import AppKit

struct NotchRect {
    let frame: CGRect
    let hasNotch: Bool
}

/// Derives the physical notch's on-screen bounding box so the compact pill
/// can be sized/positioned to match it exactly (§2.1: "Query the actual
/// notch bounding box at runtime rather than hardcoding"). Falls back to a
/// plain top-center placement (no "fused" illusion) on displays without a
/// notch — external monitors, older MacBooks.
enum NotchGeometry {
    static func current(for screen: NSScreen) -> NotchRect {
        guard let left = screen.auxiliaryTopLeftArea, let right = screen.auxiliaryTopRightArea else {
            let width: CGFloat = 220
            let height: CGFloat = 32
            let frame = CGRect(
                x: screen.frame.midX - width / 2,
                y: screen.frame.maxY - height,
                width: width,
                height: height
            )
            return NotchRect(frame: frame, hasNotch: false)
        }

        // The physical notch is the gap between the left/right auxiliary
        // menu-bar areas — this is exactly what those two properties exist
        // to describe (the usable menu-bar strips flanking a camera housing).
        let notchFrame = CGRect(
            x: left.maxX,
            y: screen.frame.maxY - left.height,
            width: right.minX - left.maxX,
            height: left.height
        )
        return NotchRect(frame: notchFrame, hasNotch: true)
    }
}
