import SwiftUI

/// §2.1: the default, always-present compact pill. Fully opaque, fused to
/// the notch's black — nothing here but 8 dots and a small, deliberately
/// muted connection glyph kept apart from them.
struct PillView: View {
    let snapshot: HubSnapshot

    var body: some View {
        VStack(spacing: 2) {
            HStack(spacing: 5) {
                ForEach(snapshot.slots) { slot in
                    SlotDotView(slot: slot)
                }
            }
            // §3: "a small, deliberately minor connection indicator ...
            // positioned apart from the 8 session dots — don't let it
            // compete with them for attention." Muted white/gray only,
            // never a state color.
            Circle()
                .fill(SlotColor.chrome)
                .opacity(snapshot.midiConnected ? 1.0 : 0.0)
                .frame(width: 3, height: 3)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(SlotColor.backgroundBottom)
    }
}
