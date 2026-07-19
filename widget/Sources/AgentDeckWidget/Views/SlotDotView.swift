import SwiftUI

/// The reusable state dot — used in the pill and peek. Color/blink/breathe
/// math lives in SlotVisual, shared with PadButtonView's bigger tiles.
struct SlotDotView: View {
    let slot: SlotState
    var diameter: CGFloat = 6

    var body: some View {
        TimelineView(.animation) { timeline in
            let state = SlotVisual.displayState(for: slot, at: timeline.date)
            Circle()
                .fill(SlotColor.color(for: state))
                .opacity(SlotVisual.opacity(for: state, at: timeline.date))
                .frame(width: diameter, height: diameter)
        }
    }
}
