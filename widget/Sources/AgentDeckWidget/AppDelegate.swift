import AppKit

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private let hub = HubState()
    private var panel: OverlayPanel?

    func applicationDidFinishLaunching(_ notification: Notification) {
        guard let screen = NSScreen.main else { return }
        panel = OverlayPanel(hub: hub, screen: screen)
        panel?.orderFrontRegardless()
        hub.start()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }
}
