import Foundation

/// Motion language constants, transcribed from the design doc §5. Motion is
/// spent only on the two actionable states plus the optional thinking
/// breathe — everything else is fully static, per §5's explicit rule.
enum Motion {
    /// waiting_permission: "~500ms full cycle. Urgent, binary, resolve-now cadence."
    static let fastBlinkCycle: Double = 0.5

    /// waiting_question: "~1400ms full cycle... roughly 3x slower than the
    /// fast blink — the difference must read as categorically different."
    static let slowBlinkCycle: Double = 1.4

    /// thinking (optional): "a subtle opacity oscillation, ~60%-100%, slow
    /// (~2.4s cycle)."
    static let breatheCycle: Double = 2.4
    static let breatheRange: ClosedRange<Double> = 0.6...1.0

    /// "Peek transition: quick, mechanical expand/collapse (~150-200ms), not
    /// bouncy or playful."
    static let peekTransition: Double = 0.175

    /// How long an automatic peek stays up before collapsing back to the
    /// pill (the underlying dot keeps blinking regardless).
    static let peekAutoCollapseAfter: Double = 4.0

    /// How long the hover-triggered peek shows each actionable slot before
    /// cycling to the next one, when several slots are actionable at once.
    static let peekCycleInterval: Double = 2.5
}
