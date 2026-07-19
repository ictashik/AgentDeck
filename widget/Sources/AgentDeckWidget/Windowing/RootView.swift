import AppKit
import SwiftUI

/// The single SwiftUI root hosted by OverlayPanel — switches its *content*
/// between pill/peek/expanded per §2, while OverlayPanel itself resizes the
/// window frame to match (one window, not three, per the notch-fused
/// illusion in its resting state).
struct RootView: View {
    @ObservedObject var hub: HubState
    @State private var launchAtLogin = LoginItem.isEnabled

    var body: some View {
        Group {
            switch hub.surface {
            case .pill:
                PillView(snapshot: hub.snapshot)
                    .onTapGesture { hub.expand() }
                    .onHover { hovering in
                        if hovering { hub.startHoverPeek() } else { hub.stopHoverPeek() }
                    }
            case .peek(let slot):
                PeekView(snapshot: hub.snapshot, slot: slot)
                    .onTapGesture { hub.expand() }
                    .onHover { hovering in
                        if !hovering { hub.stopHoverPeek() }
                    }
            case .expanded:
                ExpandedView(hub: hub)
            }
        }
        .animation(.easeInOut(duration: Motion.peekTransition), value: hub.surface)
        .contextMenu {
            Toggle("Launch at Login", isOn: $launchAtLogin)
                .onChange(of: launchAtLogin) { _, newValue in LoginItem.setEnabled(newValue) }
            Divider()
            Button("Quit AgentDeck") { NSApp.terminate(nil) }
        }
    }
}
