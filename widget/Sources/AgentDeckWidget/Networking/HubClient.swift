import Foundation

/// Talks to the Python daemon's FastAPI hub (127.0.0.1:8765) — the SSE
/// stream for live state, and the five mutating POST actions the widget
/// needs (daemon/http_api.py). All stored state is immutable (`let`), so
/// this is safe to hand across actor boundaries.
final class HubClient: Sendable {
    private let baseURL = URL(string: "http://127.0.0.1:8765")!
    private let session: URLSession
    private let streamSession: URLSession

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10
        session = URLSession(configuration: config)

        // Separate session for GET /events: timeoutIntervalForRequest governs
        // the gap between successive bytes, not total connection duration —
        // /events only emits on an actual state change, so an idle gap far
        // longer than a normal request timeout is completely expected here,
        // not a hang. A short timeout (as used for the mutating POSTs above)
        // was killing the stream every time nothing changed for a while.
        let streamConfig = URLSessionConfiguration.default
        streamConfig.timeoutIntervalForRequest = .infinity
        streamConfig.timeoutIntervalForResource = .infinity
        streamSession = URLSession(configuration: streamConfig)
    }

    /// Connects to GET /events and calls `onSnapshot` on the main actor for
    /// every frame. Reconnects with a fixed backoff if the stream ends
    /// (daemon restart, network blip) — runs until the surrounding Task is
    /// cancelled.
    func streamEvents(onSnapshot: @escaping @MainActor (HubSnapshot) -> Void) async {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        while !Task.isCancelled {
            do {
                let url = baseURL.appendingPathComponent("events")
                let (bytes, response) = try await streamSession.bytes(from: url)
                guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                    throw URLError(.badServerResponse)
                }
                // Every frame daemon/http_api.py's /events sends is exactly
                // one `data: <single-line JSON>\n\n` — json.dumps never
                // embeds a raw newline, so each frame is fully decodable the
                // moment its one `data:` line arrives. (Deliberately not
                // waiting for the blank line that terminates an SSE frame
                // per spec: URLSession's AsyncBytes.lines doesn't reliably
                // surface it as its own empty element, which silently
                // starved this of ever decoding anything — confirmed live.)
                for try await line in bytes.lines {
                    if Task.isCancelled { return }
                    guard line.hasPrefix("data:") else { continue }
                    let payload = line.dropFirst(5).trimmingCharacters(in: .whitespaces)
                    guard let jsonData = payload.data(using: .utf8) else { continue }
                    if let snapshot = try? decoder.decode(HubSnapshot.self, from: jsonData) {
                        await MainActor.run { onSnapshot(snapshot) }
                    }
                }
            } catch {
                print("HubClient: stream error \(error)")
            }

            if Task.isCancelled { return }
            try? await Task.sleep(nanoseconds: 1_000_000_000)  // 1s reconnect backoff
        }
    }

    // MARK: - Mutating actions

    func resolve(slot: Int, decision: String) async throws {
        try await post("resolve", body: ["slot": slot, "decision": decision])
    }

    @discardableResult
    func claim(slot: Int) async throws -> String? {
        struct Response: Decodable { let ok: Bool; let cwd: String? }
        let data = try await postForData("claim", body: ["slot": slot])
        return try JSONDecoder().decode(Response.self, from: data).cwd
    }

    func unbind(slot: Int) async throws {
        try await post("unbind", body: ["slot": slot])
    }

    func raiseWindow(slot: Int) async throws {
        try await post("raise", body: ["slot": slot])
    }

    func focus(slot: Int) async throws {
        try await post("focus", body: ["slot": slot])
    }

    // MARK: - Plumbing

    private func post(_ path: String, body: [String: Any]) async throws {
        _ = try await postForData(path, body: body)
    }

    private func postForData(_ path: String, body: [String: Any]) async throws -> Data {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = AuthToken.current {
            request.setValue(token, forHTTPHeaderField: "X-Agentdeck-Token")
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return data
    }
}
