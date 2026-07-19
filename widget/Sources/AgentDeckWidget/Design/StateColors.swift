import SwiftUI

/// Canonical color system. Started as a verbatim transcription of the
/// notch-widget design doc §4, but §4's `idle`/`waiting_permission`/
/// `waiting_question` hexes (slate gray, orange, violet) assumed colors the
/// real hardware turned out not to support: daemon/protocol/pad_colors.py's
/// module docstring found GREY indistinguishable from OFF on this unit, and
/// no confirmed ORANGE/VIOLET velocity exists at all — so the daemon's
/// STATE_COLORS silently substitutes WHITE for idle and reuses the *same*
/// AMBER/BLUE as running_tool/thinking for waiting_permission/
/// waiting_question (distinguished only by blink motion, not hue). This
/// table now mirrors those substitutions instead of the pre-hardware design
/// doc, restoring "hardware/software color parity" (§1) — screen and pads
/// showing different colors for the same state was a live-reported bug.
/// design.md itself is left as-is per its own note: it's the historical
/// record, not edited to match.
enum SlotColor {
    /// `waiting_input` has no entry in the design doc's §4 table (a gap the
    /// doc itself left open). Resolved here as running_tool's hue at reduced
    /// opacity — mirroring the hardware's steady-dim-amber vs
    /// steady-bright-amber pair (daemon/protocol/pad_colors.py's
    /// STATE_COLORS) — staying solid since, per CLAUDE.md, only
    /// waiting_permission/waiting_question are accept/reject-resolvable.
    static func hex(for state: String) -> String {
        switch state {
        case "idle": return "#FFFFFF"
        case "thinking": return "#4F8CFF"
        case "running_tool": return "#FFB020"
        case "waiting_permission": return "#FFB020"
        case "waiting_question": return "#4F8CFF"
        case "waiting_input": return "#FFB020"
        case "done": return "#32D74B"
        case "error": return "#FF453A"
        default: return "#FFFFFF"
        }
    }

    static func opacity(for state: String) -> Double {
        (state == "waiting_input" || state == "idle") ? 0.6 : 1.0
    }

    static func color(for state: String) -> Color {
        Color(hex: hex(for: state)).opacity(opacity(for: state))
    }

    /// §4: "Background: near-black, #050506 to #0A0A0B".
    static let backgroundTop = Color(hex: "#0A0A0B")
    static let backgroundBottom = Color(hex: "#050506")

    /// §4: "Chrome / non-semantic accents ... never reuse a state color for
    /// structure."
    static let chrome = Color.white.opacity(0.35)
    static let chromeStrong = Color.white.opacity(0.6)

    /// Transport button colors (TransportRowView) — a distinct vocabulary
    /// from the §4 state table, mirroring the conventional
    /// play/loop/record affordance rather than session state, so reusing
    /// green/red here doesn't collide with §4's "no state shares a hue"
    /// rule (these aren't state colors at all).
    static let transportAllow = Color(hex: "#32D74B")
    static let transportDeny = Color(hex: "#FF453A")
    static let transportNeutral = Color.white.opacity(0.75)
}

extension Color {
    /// Minimal `#RRGGBB` / `#RGB` hex parser — no external dependency needed
    /// for the small fixed palette above.
    init(hex: String) {
        var s = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if s.hasPrefix("#") { s.removeFirst() }

        var value: UInt64 = 0
        Scanner(string: s).scanHexInt64(&value)

        let r, g, b: UInt64
        switch s.count {
        case 3:
            r = (value >> 8) & 0xF
            g = (value >> 4) & 0xF
            b = value & 0xF
            self.init(
                red: Double(r * 17) / 255,
                green: Double(g * 17) / 255,
                blue: Double(b * 17) / 255
            )
        default:
            r = (value >> 16) & 0xFF
            g = (value >> 8) & 0xFF
            b = value & 0xFF
            self.init(
                red: Double(r) / 255,
                green: Double(g) / 255,
                blue: Double(b) / 255
            )
        }
    }
}
