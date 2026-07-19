import SwiftUI

/// One pad tile in the expanded view's 4×2 grid — the widget-side twin of a
/// physical pad: same color/blink language (SlotVisual), same position.
/// Unbound pads render mostly-empty; a claimable one (pending repo, no
/// binding) gets a pulsing outline instead of a fill, inviting a click —
/// there's no state color to show for something that isn't a session yet.
struct PadButtonView: View {
    let slot: SlotState
    let isFocused: Bool
    let isClaimable: Bool
    let onTap: () -> Void
    let onDoubleTap: () -> Void
    let onHover: (Bool) -> Void
    let onUnbind: () -> Void

    var body: some View {
        TimelineView(.animation) { timeline in
            RoundedRectangle(cornerRadius: 6)
                .fill(fill(at: timeline.date))
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .strokeBorder(border(at: timeline.date), lineWidth: borderWidth)
                )
        }
        .frame(width: ExpandedLayout.padSize, height: ExpandedLayout.padSize)
        .overlay(alignment: .topLeading) {
            Text("\(slot.slot)")
                .font(.system(size: 8, design: .monospaced))
                .foregroundStyle(.white.opacity(0.3))
                .padding(4)
        }
        .contentShape(RoundedRectangle(cornerRadius: 6))
        // SwiftUI disambiguates single vs. double tap automatically when
        // both are attached to the same view (a short delay on the single
        // tap to see if a second one follows) — no manual timing needed.
        .onTapGesture(count: 2, perform: onDoubleTap)
        .onTapGesture(count: 1, perform: onTap)
        .onHover(perform: onHover)
        .contextMenu {
            if slot.repo != nil {
                Button("Unbind", role: .destructive, action: onUnbind)
            }
        }
    }

    private var borderWidth: CGFloat { (isFocused || isClaimable) ? 1.5 : 0 }

    private func fill(at date: Date) -> Color {
        guard slot.repo != nil else {
            // Unbound: the hardware's "off" look (daemon/protocol/pad_colors.py's
            // message_for_empty), not idle-gray — nothing is bound here yet.
            return SlotColor.backgroundTop.opacity(0.6)
        }
        let state = SlotVisual.displayState(for: slot, at: date)
        return SlotColor.color(for: state).opacity(SlotVisual.opacity(for: state, at: date))
    }

    private func border(at date: Date) -> Color {
        if isClaimable {
            return SlotColor.chromeStrong.opacity(SlotVisual.breathe(at: date, cycle: 1.4, range: 0.3...0.9))
        }
        return isFocused ? SlotColor.chromeStrong : .clear
    }
}
