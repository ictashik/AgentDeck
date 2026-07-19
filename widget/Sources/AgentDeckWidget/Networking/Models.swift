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
