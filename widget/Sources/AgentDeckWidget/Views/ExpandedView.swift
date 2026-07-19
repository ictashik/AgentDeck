import SwiftUI

/// §2.3: the full session list. Standard macOS vibrancy is allowed here
/// (only here) — once expanded, it's openly a floating panel and the notch
/// illusion is intentionally broken.
struct ExpandedView: View {
    @ObservedObject var hub: HubState

    private var freeSlots: [Int] {
        hub.snapshot.slots.filter { $0.repo == nil }.map(\.slot)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 1) {
            if let pending = hub.snapshot.pendingClaimCwd {
                ClaimRowView(cwd: pending, freeSlots: freeSlots) { slot in
                    hub.claim(slot: slot)
                }
                Divider().opacity(0.2)
            }

            ForEach(hub.snapshot.slots) { slot in
                SlotRowView(
                    slot: slot,
                    isFocused: hub.snapshot.focusedSlot == slot.slot,
                    onResolve: { decision in hub.resolve(slot: slot.slot, decision: decision) },
                    onRaise: { hub.raiseWindow(slot: slot.slot) },
                    onFocus: { hub.focus(slot: slot.slot) },
                    onUnbind: { hub.unbind(slot: slot.slot) }
                )
            }
        }
        .padding(.vertical, 6)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.regularMaterial)
        .background(SlotColor.backgroundBottom.opacity(0.4))
    }
}
