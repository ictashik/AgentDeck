import SwiftUI

/// §2.1: the default, always-present compact pill. Fully opaque, fused to
/// the notch's black. Dots are laid out as a 4×2 grid mirroring the
/// physical MPK's own pad numbering (PadLayout) rather than one flat row of
/// 8, so the pill reads as a tiny mirror of the hardware grid, not just a
/// status strip — sized tight enough (smaller dots/gaps than the expanded
/// grid) that the pill's overall footprint doesn't grow versus the single
/// row this replaced.
struct PillView: View {
    let snapshot: HubSnapshot

    private let dotDiameter: CGFloat = 5
    private let dotGap: CGFloat = 4
    private let rowGap: CGFloat = 3

    var body: some View {
        HStack(spacing: 6) {
            VStack(spacing: rowGap) {
                row(PadLayout.topRow)
                row(PadLayout.bottomRow)
            }
            // §3: "a small, deliberately minor connection indicator ...
            // positioned apart from the 8 session dots — don't let it
            // compete with them for attention." Muted white/gray only,
            // never a state color. Sits beside the grid, not below it, so
            // adding a second row of dots doesn't add a third line of height.
            Circle()
                .fill(SlotColor.chrome)
                .opacity(snapshot.midiConnected ? 1.0 : 0.0)
                .frame(width: 3, height: 3)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(SlotColor.backgroundBottom)
    }

    private func row(_ slotNumbers: [Int]) -> some View {
        HStack(spacing: dotGap) {
            ForEach(slotNumbers, id: \.self) { number in
                if let slot = snapshot.slots.first(where: { $0.slot == number }) {
                    SlotDotView(slot: slot, diameter: dotDiameter)
                }
            }
        }
    }
}
