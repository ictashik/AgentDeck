import Foundation

/// Reads the anti-spoofing token daemon/auth.py creates at
/// ~/.agentdeck/token, sent back as X-Agentdeck-Token on mutating calls.
/// Read fresh on every call rather than cached at launch, so a regenerated
/// token file doesn't require restarting the widget.
enum AuthToken {
    static var current: String? {
        let path = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".agentdeck/token")
        return try? String(contentsOf: path, encoding: .utf8)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
