import QuartzCore

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
    /// bouncy or playful." Drives RootView's SwiftUI content crossfade
    /// (opacity only, so it stays quick/non-bouncy per that rule even though
    /// the frame resize below now has a spring feel — a fade doesn't clash
    /// with a springy size/position change the way another motion would).
    static let peekTransition: Double = 0.175

    /// OverlayPanel's window-frame resize between pill/peek/expanded. A bit
    /// longer than `peekTransition` and paired with `windowResizeCurve`
    /// (see there) to read as an Apple-style spring settle rather than a
    /// linear/mechanical resize.
    static let windowResizeDuration: Double = 0.32

    /// `NSAnimationContext` only accepts a `CAMediaTimingFunction` (a cubic
    /// bezier), not true spring physics — there's no damping/velocity knob
    /// for an NSWindow frame the way `UIView`/SwiftUI springs have. This
    /// control-point pair (0.32, 0.72, 0, 1) is the standard "spring-like
    /// ease-out" bezier approximation used across Apple's own UIKit/SwiftUI
    /// spring curves: a fast initial move that decelerates hard into the
    /// landing, without literal overshoot (which risked visible clipping on
    /// a resizing NSHostingView).
    @MainActor static let windowResizeCurve = CAMediaTimingFunction(controlPoints: 0.32, 0.72, 0, 1)

    /// How long an automatic peek stays up before collapsing back to the
    /// pill (the underlying dot keeps blinking regardless).
    static let peekAutoCollapseAfter: Double = 4.0

    /// How long the hover-triggered peek shows each actionable slot before
    /// cycling to the next one, when several slots are actionable at once.
    static let peekCycleInterval: Double = 2.5
}
