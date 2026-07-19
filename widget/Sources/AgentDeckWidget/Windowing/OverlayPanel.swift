import AppKit
import Combine
import QuartzCore
import SwiftUI

/// One custom borderless panel whose *frame* moves between the pill/peek/
/// expanded sizes (§2) rather than three separate windows. Positioned via
/// NotchGeometry so the pill reads as a continuation of the physical notch
/// in its resting state.
final class OverlayPanel: NSPanel {
    static let pillHeight: CGFloat = 22
    static let peekHeight: CGFloat = 44
    // Expanded size is fixed now (display + 4x2 pad grid + transport row,
    // not a variable-length session list) — see Design/ExpandedLayout.swift,
    // shared with the SwiftUI views themselves so the window always matches
    // its content exactly with no fittingSize query needed.

    private let hub: HubState
    private var notch: NotchRect
    private var cancellables: Set<AnyCancellable> = []
    private var outsideClickMonitor: Any?

    init(hub: HubState, screen: NSScreen) {
        self.hub = hub
        self.notch = NotchGeometry.current(for: screen)

        super.init(
            contentRect: NSRect(origin: .zero, size: CGSize(width: notch.frame.width, height: OverlayPanel.pillHeight)),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )

        isOpaque = false
        backgroundColor = .clear
        hasShadow = false
        level = .statusBar
        collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle, .fullScreenAuxiliary]
        ignoresMouseEvents = false
        isMovableByWindowBackground = false
        isReleasedWhenClosed = false

        let hosting = NSHostingView(rootView: RootView(hub: hub))
        hosting.frame = NSRect(origin: .zero, size: frame.size)
        hosting.autoresizingMask = [.width, .height]
        contentView = hosting

        NotificationCenter.default.addObserver(
            self, selector: #selector(screenParametersChanged),
            name: NSApplication.didChangeScreenParametersNotification, object: nil
        )

        Publishers.CombineLatest(hub.$surface, hub.$snapshot)
            .receive(on: RunLoop.main)
            .sink { [weak self] surface, snapshot in
                self?.reposition(surface: surface, snapshot: snapshot)
            }
            .store(in: &cancellables)

        reposition(surface: .pill, snapshot: hub.snapshot, animated: false)
    }

    @objc private func screenParametersChanged() {
        guard let screen = NSScreen.main else { return }
        notch = NotchGeometry.current(for: screen)
        // A screen/resolution change repositions the notch itself — snap,
        // don't animate; this isn't a pill/peek/expanded state transition.
        reposition(surface: hub.surface, snapshot: hub.snapshot, animated: false)
    }

    /// Resizes/repositions the panel to match the given surface. Animated by
    /// default: pop/collapse between pill, peek, and expanded uses the
    /// window's own `animator()` proxy (Apple's documented mechanism for
    /// smoothly animating an NSWindow's frame — see
    /// developer.apple.com/documentation/appkit/nswindow/1419519-setframe)
    /// rather than `setFrame(..., animate: false)`, which snapped instantly
    /// and made the RootView's SwiftUI crossfade (Motion.peekTransition)
    /// play inside a window that had already jumped to its new size,
    /// producing the jump-cut/glitch this replaces. Same duration and an
    /// equivalent easing curve as that SwiftUI animation, so the frame
    /// resize and the content crossfade read as one motion, not two out of
    /// sync ones.
    private func reposition(surface: SurfaceState, snapshot: HubSnapshot, animated: Bool = true) {
        let size: CGSize
        switch surface {
        case .pill:
            size = CGSize(width: max(notch.frame.width, 120), height: Self.pillHeight)
        case .peek:
            size = CGSize(width: max(notch.frame.width, 160), height: Self.peekHeight)
        case .expanded:
            size = CGSize(width: ExpandedLayout.panelWidth, height: ExpandedLayout.panelHeight)
        }

        let originX = (surface == .expanded)
            ? notch.frame.midX - size.width / 2
            : notch.frame.minX
        let originY = notch.frame.minY - size.height

        let newFrame = NSRect(x: originX, y: originY, width: size.width, height: size.height)

        // §2.1/§2.3: opaque + no shadow while fused to the notch; the
        // expanded panel is allowed to look like a floating panel. Flipped
        // before the resize starts (not after) so the shadow is already
        // correct for whichever size the window is animating towards.
        hasShadow = surface == .expanded
        isOpaque = false

        if animated {
            NSAnimationContext.runAnimationGroup { context in
                context.duration = Motion.peekTransition
                context.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
                self.animator().setFrame(newFrame, display: true)
            }
        } else {
            setFrame(newFrame, display: true, animate: false)
        }

        updateOutsideClickMonitor(active: surface == .expanded)
    }

    private func updateOutsideClickMonitor(active: Bool) {
        if active {
            guard outsideClickMonitor == nil else { return }
            outsideClickMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown]) { [weak self] _ in
                self?.hub.collapse()
            }
        } else if let monitor = outsideClickMonitor {
            NSEvent.removeMonitor(monitor)
            outsideClickMonitor = nil
        }
    }
}
