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
        // Two independent `.onTapGesture(count:)` modifiers on the same view
        // don't reliably disambiguate single vs. double click on macOS (they
        // do on iOS) — the double-tap handler could go unfired, live-reported
        // as "double tap to focus window is not working." `.exclusively(
        // before:)` is the documented-reliable pattern: the double-tap
        // gesture gets first refusal within the system's multi-click
        // interval, falling through to single-tap only if it doesn't
        // complete.
        .gesture(
            TapGesture(count: 2).onEnded(onDoubleTap)
                .exclusively(before: TapGesture(count: 1).onEnded(onTap))
        )
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
