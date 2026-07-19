import SwiftUI

/// Shared color/blink/breathe/done-fade math — used by both `SlotDotView`
/// (the small pill/peek dots) and `PadButtonView` (the bigger expanded-view
/// pad tiles), so a given slot renders identically at any size (§1:
/// "hardware/software color parity").
enum SlotVisual {
    /// `done` renders as `idle` once past the fade threshold (§4) — a pure
    /// rendering substitution, the underlying JSON state is untouched.
    static func displayState(for slot: SlotState, at date: Date) -> String {
        if slot.state == "done" {
            let age = date.timeIntervalSince1970 - slot.updatedAt
            if age > Motion.doneToIdleFadeAfter { return "idle" }
        }
        return slot.state
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
