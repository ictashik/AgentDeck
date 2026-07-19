import Foundation

enum SurfaceState: Equatable {
    case pill
    case peek(slot: Int)
    case expanded
}

/// Owns the live connection to the daemon and the widget's current surface
/// state (§2: pill / peek / expanded). Purely data-driven — animation ticks
/// (blink/breathe/done-fade) live in the views themselves via TimelineView,
/// not here.
@MainActor
final class HubState: ObservableObject {
    @Published private(set) var snapshot: HubSnapshot = .empty
    @Published private(set) var surface: SurfaceState = .pill

    private let client = HubClient()
    private var streamTask: Task<Void, Never>?
    private var autoCollapseTask: Task<Void, Never>?
    private var hoverCycleTask: Task<Void, Never>?

    func start() {
        guard streamTask == nil else { return }
        streamTask = Task { [weak self] in
            await self?.client.streamEvents { snapshot in
                self?.apply(snapshot)
            }
        }
    }

    private func apply(_ newSnapshot: HubSnapshot) {
        // §2.2: "Only actionable-state transitions trigger an automatic
        // peek." Diff by (slot, state) — a slot newly entering
        // waiting_permission/waiting_question that wasn't already in that
        // state triggers a peek.
        let previousActionable = Set(snapshot.slots.filter(\.isActionable).map(\.slot))
        let newlyActionable = newSnapshot.slots.first { $0.isActionable && !previousActionable.contains($0.slot) }

        snapshot = newSnapshot

        if let slot = newlyActionable, surface == .pill {
            showPeek(slot: slot.slot, autoCollapse: true)
        }
    }

    // MARK: - Surface transitions

    /// Hover entered the pill: manually peek, cycling through every
    /// currently-actionable slot on a fixed interval (design decision: when
    /// several slots are actionable at once, cycle rather than show one or
    /// stack all).
    func startHoverPeek() {
        guard surface != .expanded else { return }
        hoverCycleTask?.cancel()
        autoCollapseTask?.cancel()

        let actionable = snapshot.slots.filter(\.isActionable)
        guard !actionable.isEmpty else { return }

        hoverCycleTask = Task { [weak self] in
            var index = 0
            while !Task.isCancelled {
                guard let self else { return }
                let slots = self.snapshot.slots.filter(\.isActionable)
                if slots.isEmpty {
                    self.surface = .pill
                    return
                }
                self.surface = .peek(slot: slots[index % slots.count].slot)
                index += 1
                try? await Task.sleep(nanoseconds: UInt64(Motion.peekCycleInterval * 1_000_000_000))
            }
        }
    }

    func stopHoverPeek() {
        hoverCycleTask?.cancel()
        hoverCycleTask = nil
        if case .peek = surface {
            surface = .pill
        }
    }

    private func showPeek(slot: Int, autoCollapse: Bool) {
        surface = .peek(slot: slot)
        guard autoCollapse else { return }
        autoCollapseTask?.cancel()
        autoCollapseTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(Motion.peekAutoCollapseAfter * 1_000_000_000))
            guard let self, !Task.isCancelled else { return }
            if case .peek = self.surface {
                self.surface = .pill
            }
        }
    }

    func expand() {
        hoverCycleTask?.cancel()
        autoCollapseTask?.cancel()
        surface = .expanded
    }

    func collapse() {
        hoverCycleTask?.cancel()
        autoCollapseTask?.cancel()
        surface = .pill
    }

    // MARK: - Actions (best-effort — a personal localhost tool, errors are
    // swallowed rather than surfaced, matching hooks/post_event.sh's own
    // "never block on the hub" philosophy).

    func resolve(slot: Int, decision: String) {
        Task { try? await client.resolve(slot: slot, decision: decision) }
    }

    func claim(slot: Int) {
        Task { try? await client.claim(slot: slot) }
    }

    func unbind(slot: Int) {
        Task { try? await client.unbind(slot: slot) }
        collapse()
    }

    func raiseWindow(slot: Int) {
        Task { try? await client.raiseWindow(slot: slot) }
    }

    func focus(slot: Int) {
        Task { try? await client.focus(slot: slot) }
    }
}
