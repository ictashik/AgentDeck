import SwiftUI

/// §2.3, reinterpreted per a follow-up prompt: a mini display + 4×2 pad
/// grid mirroring the physical MPK's own layout, instead of a session list.
/// Standard macOS vibrancy is allowed here (only here) — once expanded,
/// it's openly a floating panel and the notch illusion is intentionally
/// broken.
struct ExpandedView: View {
    @ObservedObject var hub: HubState
    @State private var hoveredSlot: Int?

    private var displaySlot: Int {
        hoveredSlot ?? hub.snapshot.focusedSlot ?? 1
    }

    var body: some View {
        VStack(spacing: ExpandedLayout.sectionGap) {
            DisplayView(snapshot: hub.snapshot, displaySlot: displaySlot)
            PadGridView(hub: hub, hoveredSlot: $hoveredSlot)
            TransportRowView(hub: hub)
        }
        .padding(ExpandedLayout.outerPadding)
        .frame(width: ExpandedLayout.panelWidth, height: ExpandedLayout.panelHeight)
        .background(.regularMaterial)
        .background(SlotColor.backgroundBottom.opacity(0.4))
    }
}
