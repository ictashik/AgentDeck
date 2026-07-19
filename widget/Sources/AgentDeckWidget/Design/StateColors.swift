import SwiftUI

/// Canonical color system, transcribed verbatim from the notch-widget design
/// doc §4 — this is the single source of truth shared with the physical pad
/// LEDs (daemon/protocol/pad_colors.py). Never introduce a color here that
/// doesn't also correspond to a documented state.
enum SlotColor {
    /// `waiting_input` has no entry in the design doc's §4 table (a gap the
    /// doc itself left open). Resolved here as running_tool's hue at reduced
    /// opacity — mirroring the hardware's steady-dim-amber vs
    /// steady-bright-amber pair (daemon/protocol/pad_colors.py's
    /// STATE_COLORS) — staying solid since, per CLAUDE.md, only
    /// waiting_permission/waiting_question are accept/reject-resolvable.
    static func hex(for state: String) -> String {
        switch state {
        case "idle": return "#4A515C"
        case "thinking": return "#4F8CFF"
        case "running_tool": return "#FFB020"
        case "waiting_permission": return "#FF9F0A"
        case "waiting_question": return "#BF7BFF"
        case "waiting_input": return "#FFB020"
        case "done": return "#32D74B"
        case "error": return "#FF453A"
        default: return "#4A515C"
        }
    }

    static func opacity(for state: String) -> Double {
        state == "waiting_input" ? 0.6 : 1.0
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
