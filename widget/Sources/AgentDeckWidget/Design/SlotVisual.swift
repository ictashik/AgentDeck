import SwiftUI

/// Shared color/blink/breathe/done-fade math — used by both `SlotDotView`
/// (the small pill/peek dots) and `PadButtonView` (the bigger expanded-view
/// pad tiles), so a given slot renders identically at any size (§1:
/// "hardware/software color parity").
enum SlotVisual {
    /// §4 originally called for `done` to fade to an `idle` look client-side
    /// after a few seconds, but that has no hardware equivalent — the pad
    /// LED just reflects whatever `state` currently is (daemon/midi_io.py's
    /// `_refresh_pad_colors`), and the daemon never auto-transitions `done`
    /// back to `idle` on its own (only the next real hook event changes
    /// it). A session sitting `done` for a while showed solid green on the
    /// MPK but faded to grey on screen — a live-reported parity bug — so
    /// this is deliberately a pass-through now, matching hardware exactly.
    static func displayState(for slot: SlotState, at date: Date) -> String {
        slot.state
    }

    static func opacity(for state: String, at date: Date) -> Double {
        let base = SlotColor.opacity(for: state)
        switch state {
        case "waiting_permission":
            return base * blink(cycle: Motion.fastBlinkCycle, at: date)
        case "waiting_question":
            return base * blink(cycle: Motion.slowBlinkCycle, at: date)
        case "thinking":
            return base * breathe(at: date)
        default:
            return base
        }
    }

    /// Discrete on/off blink (not a fade) — §5's "urgent, binary, resolve-now
    /// cadence" reads as a hard on/off, not a smooth pulse.
    static func blink(cycle: Double, at date: Date) -> Double {
        let phase = date.timeIntervalSince1970.truncatingRemainder(dividingBy: cycle) / cycle
        return phase < 0.5 ? 1.0 : 0.15
    }

    /// Smooth oscillation for the optional thinking-breathe (§5: "low
    /// amplitude enough that it reads as a heartbeat, not a blink") — also
    /// reused for the claimable-pad pulse in the expanded view.
    static func breathe(at date: Date, cycle: Double = Motion.breatheCycle, range: ClosedRange<Double> = Motion.breatheRange) -> Double {
        let phase = date.timeIntervalSince1970.truncatingRemainder(dividingBy: cycle) / cycle
        let wave = (sin(phase * 2 * .pi) + 1) / 2  // 0...1
        return range.lowerBound + wave * (range.upperBound - range.lowerBound)
    }
}
