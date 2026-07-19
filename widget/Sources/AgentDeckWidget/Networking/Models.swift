import Foundation

/// One session slot, mirroring daemon/http_api.py's `_slot_payload`.
struct SlotState: Codable, Identifiable, Equatable {
    var id: Int { slot }
    let slot: Int
    let agent: String?
    let state: String
    let detail: String?
    let cwd: String?
    let updatedAt: Double
    let label: String?
    let repo: String?

    var isActionable: Bool {
        state == "waiting_permission" || state == "waiting_question"
    }

    /// The name shown in the widget: the friendly slot binding label if
    /// bound, else the cwd's basename, else a plain "slot N" fallback.
    var displayName: String {
        if let label, !label.isEmpty { return label }
        if let cwd, let last = cwd.split(separator: "/").last { return String(last) }
        return "slot \(slot)"
    }

    /// A 2-4 word status phrase (§2.2), preferring the hook-supplied detail
    /// when there is one. Shared by the peek and the mini display.
    var statusPhrase: String {
        switch state {
        case "waiting_permission":
            return detail.map { "allow \($0)?" } ?? "needs permission"
        case "waiting_question":
            return detail ?? "has a question"
        default:
            return detail ?? state
        }
    }

    /// Abbreviated tool-prefixed command label for the mini display, e.g.
    /// "bash:rm -rf build/" or "AKQ:overwrite this file?" — there's no
    /// separate tool_name field in this payload, so the state itself
    /// stands in for which tool is implied.
    var commandLabel: String {
        switch state {
        case "waiting_permission":
            return "bash:" + (detail ?? "?")
        case "waiting_question":
            return "AKQ:" + (detail ?? "?")
        default:
            return detail ?? state
        }
    }
}

/// Whole-store snapshot, mirroring daemon/http_api.py's `_snapshot` — the
/// shape both GET /state and GET /events return.
struct HubSnapshot: Codable, Equatable {
    let focusedSlot: Int?
    let midiConnected: Bool
    let pendingClaimCwd: String?
    let slots: [SlotState]

    static let empty = HubSnapshot(focusedSlot: nil, midiConnected: false, pendingClaimCwd: nil, slots: [])
}
