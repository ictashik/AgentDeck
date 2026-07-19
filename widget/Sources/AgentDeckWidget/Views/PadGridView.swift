import SwiftUI

/// The 4×2 pad grid mirroring the physical MPK's own layout — pads numbered
/// 1-4 on the bottom row, 5-8 on the top row (standard Akai MPC-style
/// numbering), left to right, so tapping "pad 3" here means the same thing
/// as pad 3 on the hardware.
struct PadGridView: View {
    @ObservedObject var hub: HubState
    @Binding var hoveredSlot: Int?

    var body: some View {
        VStack(spacing: ExpandedLayout.padGap) {
            row(PadLayout.topRow)
            row(PadLayout.bottomRow)
        }
    }

    private func row(_ slotNumbers: [Int]) -> some View {
        HStack(spacing: ExpandedLayout.padGap) {
            ForEach(slotNumbers, id: \.self) { number in
                if let slot = hub.snapshot.slots.first(where: { $0.slot == number }) {
                    PadButtonView(
                        slot: slot,
                        isFocused: hub.snapshot.focusedSlot == number,
                        isClaimable: hub.snapshot.pendingClaimCwd != nil && slot.repo == nil,
                        onTap: { tapped(slot) },
                        onDoubleTap: { doubleTapped(slot) },
                        onHover: { hovering in hoveredSlot = hovering ? number : nil },
                        onUnbind: { hub.unbind(slot: number) }
                    )
                }
            }
        }
    }

    private func tapped(_ slot: SlotState) {
        if hub.snapshot.pendingClaimCwd != nil && slot.repo == nil {
            hub.claim(slot: slot.slot)
        } else if slot.repo != nil {
            hub.focus(slot: slot.slot)
        }
    }

    /// Double-clicking any active (bound) pad raises its window — the
    /// widget's equivalent of Shift+pad on the hardware.
    private func doubleTapped(_ slot: SlotState) {
        guard slot.repo != nil else { return }
        hub.focus(slot: slot.slot)
        hub.raiseWindow(slot: slot.slot)
    }
}
