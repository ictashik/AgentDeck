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
                Text("\(peeked.slot)  \(peeked.displayName)  \(peeked.statusPhrase)")
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
}
