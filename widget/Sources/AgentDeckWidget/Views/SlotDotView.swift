import SwiftUI

/// The reusable state dot — color, blink/breathe motion, and the done->idle
/// fade rule all live here so every surface (pill/peek/expanded) renders a
/// given slot identically (§1: "hardware/software color parity... the same
/// exact color for slot 3 in the notch" — and the same shape everywhere in
/// software too).
struct SlotDotView: View {
    let slot: SlotState
    var diameter: CGFloat = 6

    var body: some View {
        TimelineView(.animation) { timeline in
            let effectiveState = displayState(at: timeline.date)
            Circle()
                .fill(SlotColor.color(for: effectiveState))
                .opacity(opacity(for: effectiveState, at: timeline.date))
                .frame(width: diameter, height: diameter)
        }
    }

    /// `done` renders as `idle` once past the fade threshold (§4) — a pure
    /// rendering substitution, the underlying JSON state is untouched.
    private func displayState(at date: Date) -> String {
        if slot.state == "done" {
            let age = date.timeIntervalSince1970 - slot.updatedAt
            if age > Motion.doneToIdleFadeAfter { return "idle" }
        }
        return slot.state
    }

    private func opacity(for state: String, at date: Date) -> Double {
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
    private func blink(cycle: Double, at date: Date) -> Double {
        let phase = date.timeIntervalSince1970.truncatingRemainder(dividingBy: cycle) / cycle
        return phase < 0.5 ? 1.0 : 0.15
    }

    /// Smooth oscillation for the optional thinking-breathe (§5: "low
    /// amplitude enough that it reads as a heartbeat, not a blink").
    private func breathe(at date: Date) -> Double {
        let phase = date.timeIntervalSince1970.truncatingRemainder(dividingBy: Motion.breatheCycle) / Motion.breatheCycle
        let wave = (sin(phase * 2 * .pi) + 1) / 2  // 0...1
        return Motion.breatheRange.lowerBound + wave * (Motion.breatheRange.upperBound - Motion.breatheRange.lowerBound)
    }
}
