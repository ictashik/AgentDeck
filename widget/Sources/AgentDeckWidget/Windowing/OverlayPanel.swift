import AppKit
import Combine
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

        reposition(surface: .pill, snapshot: hub.snapshot)
    }

    @objc private func screenParametersChanged() {
        guard let screen = NSScreen.main else { return }
        notch = NotchGeometry.current(for: screen)
        reposition(surface: hub.surface, snapshot: hub.snapshot)
    }

    private func reposition(surface: SurfaceState, snapshot: HubSnapshot) {
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
        setFrame(newFrame, display: true, animate: false)

        // §2.1/§2.3: opaque + no shadow while fused to the notch; the
        // expanded panel is allowed to look like a floating panel.
        hasShadow = surface == .expanded
        isOpaque = false

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
