import SwiftUI

/// §2.2: the pill grows downward to show one line — which slot, a short
/// phrase. Nothing more. This is the notification replacement.
struct PeekView: View {
    let snapshot: HubSnapshot
    let slot: Int

    private var peeked: SlotState? {
        snapshot.slots.first { $0.slot == slot }
    }

    var body: some View {
        VStack(spacing: 4) {
            HStack(spacing: 5) {
                ForEach(snapshot.slots) { s in
                    SlotDotView(slot: s)
                }
            }
            .padding(.top, 6)

            if let peeked {
                Text("\(peeked.slot)  \(peeked.displayName)  \(statusPhrase(for: peeked))")
                    .font(.system(size: 10, weight: .medium, design: .monospaced))
                    .foregroundStyle(.white.opacity(0.85))
                    .lineLimit(1)
                    .padding(.bottom, 6)
            }
        }
        .padding(.horizontal, 10)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(SlotColor.backgroundBottom)
    }

    /// A 2-4 word status phrase (§2.2), preferring the hook-supplied detail
    /// when there is one.
    private func statusPhrase(for slot: SlotState) -> String {
        switch slot.state {
        case "waiting_permission":
            return slot.detail.map { "allow \($0)?" } ?? "needs permission"
        case "waiting_question":
            return slot.detail ?? "has a question"
        default:
            return slot.state
        }
    }
}
