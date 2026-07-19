import AppKit
import Combine
import QuartzCore
import SwiftUI

/// One custom borderless panel whose *frame* moves between the pill/peek/
/// expanded sizes (§2) rather than three separate windows. Anchored just to
/// the right of the physical notch cutout (NotchGeometry's `notch.frame` —
/// the gap between the two `auxiliaryTop*Area`s) rather than drawn on top of
/// it: on real notched hardware that gap isn't merely reserved space, it's a
/// true display cutout with no pixels under it at all, so content positioned
/// there (the pill's original placement) was never actually visible. Every
/// surface shares the same left edge (`notch.frame.maxX`) so switching
/// between them reads as one shape growing in place, not a jump.
final class OverlayPanel: NSPanel {
    static let pillHeight: CGFloat = 22
    static let pillWidth: CGFloat = 64
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
            contentRect: NSRect(origin: .zero, size: CGSize(width: OverlayPanel.pillWidth, height: OverlayPanel.pillHeight)),
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
    /// with `Motion.windowResizeCurve`'s spring-like bezier, rather than
    /// `setFrame(..., animate: false)`, which snapped instantly and made the
    /// RootView's SwiftUI crossfade play inside a window that had already
    /// jumped to its new size, producing the jump-cut/glitch this replaces.
    private func reposition(surface: SurfaceState, snapshot: HubSnapshot, animated: Bool = true) {
        let size: CGSize
        switch surface {
        case .pill:
            size = CGSize(width: Self.pillWidth, height: Self.pillHeight)
        case .peek:
            size = CGSize(width: notch.frame.width, height: Self.peekHeight)
        case .expanded:
            size = CGSize(width: ExpandedLayout.panelWidth, height: ExpandedLayout.panelHeight)
        }

        // Every surface's left edge sits flush with the notch's right edge
        // (see the class doc) — nothing is ever positioned on top of the
        // notch cutout itself, and there's no positional jump between
        // surfaces since they all grow from the same anchor.
        let originX = notch.frame.maxX

        // The resting pill lives *in* the menu bar row itself — vertically
        // centered in notch.frame's own height, same as where system menu
        // bar icons sit — not hanging below it, which read as detached from
        // the menu bar entirely. Peek/expanded are taller than the menu bar
        // row can hold, so they keep growing downward from its bottom edge,
        // the intended "island opening below the status bar" look.
        let originY: CGFloat
        switch surface {
        case .pill:
            originY = notch.frame.minY + (notch.frame.height - size.height) / 2
        case .peek, .expanded:
            originY = notch.frame.minY - size.height
        }

        let newFrame = NSRect(x: originX, y: originY, width: size.width, height: size.height)

        // §2.1/§2.3: opaque + no shadow at rest; the expanded panel is
        // allowed to look like a floating panel. Flipped before the resize
        // starts (not after) so the shadow is already correct for whichever
        // size the window is animating towards.
        hasShadow = surface == .expanded
        isOpaque = false

        if animated {
            NSAnimationContext.runAnimationGroup { context in
                context.duration = Motion.windowResizeDuration
                context.timingFunction = Motion.windowResizeCurve
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
