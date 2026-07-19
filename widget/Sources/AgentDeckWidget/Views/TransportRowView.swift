import SwiftUI

/// Mirrors the physical transport section — Play/Stop=Allow, Loop=Allow
/// Always, Record=Deny — as colored icons that blink (same fast-blink
/// cadence as an actionable pad, Motion.fastBlinkCycle) when the focused
/// slot actually needs a decision, muted grey otherwise. "Go to window"
/// moved to a double-tap gesture directly on a pad tile (see
/// PadButtonView) rather than living here as a fourth button.
struct TransportRowView: View {
    @ObservedObject var hub: HubState

    private var focusedSlot: SlotState? {
        guard let focused = hub.snapshot.focusedSlot else { return nil }
        return hub.snapshot.slots.first { $0.slot == focused }
    }

    private var isPermission: Bool { focusedSlot?.state == "waiting_permission" }

    var body: some View {
        HStack(spacing: 4) {
            iconButton("play.fill", color: SlotColor.transportAllow) { resolve("allow") }
            iconButton("repeat", color: SlotColor.transportNeutral) { resolve("allow_always") }
            iconButton("record.circle", color: SlotColor.transportDeny) { resolve("deny") }
        }
        .frame(height: ExpandedLayout.transportRowHeight)
    }

    private func resolve(_ decision: String) {
        guard let slot = focusedSlot else { return }
        hub.resolve(slot: slot.slot, decision: decision)
    }

    private func iconButton(_ systemName: String, color: Color, action: @escaping () -> Void) -> some View {
        let enabled = isPermission
        return TimelineView(.animation) { timeline in
            let blink = enabled ? SlotVisual.blink(cycle: Motion.fastBlinkCycle, at: timeline.date) : 1.0
            Button(action: action) {
                Image(systemName: systemName)
                    .font(.system(size: 12))
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .buttonStyle(.plain)
            .background((enabled ? color : SlotColor.chrome).opacity(enabled ? 0.22 : 0.08))
            .foregroundStyle((enabled ? color : .white).opacity(enabled ? blink : 0.25))
            .clipShape(RoundedRectangle(cornerRadius: 4))
            .disabled(!enabled)
        }
    }
}
