import SwiftUI

/// The expanded surface's mini display — a software stand-in for the MPK's
/// own (never-cracked, see daemon/protocol/screen.py) onboard screen.
/// Two lines: slot + abbreviated command (gets the flexible remaining
/// width — hover to reveal the full text in blue on line 2 if it was cut
/// off) with the repo name pinned to a fixed-width top-right slot, itself
/// truncated rather than the message, so the message always knows exactly
/// how much room it has. Falls back to a claim banner when a repo is
/// pending (takes priority — claiming is the more urgent message).
struct DisplayView: View {
    let snapshot: HubSnapshot
    let displaySlot: Int
    @State private var isHoveringCommand = false

    private var slot: SlotState? {
        snapshot.slots.first { $0.slot == displaySlot }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            topLine
            bottomLine
        }
        .font(.system(size: 10, weight: .medium, design: .monospaced))
        .foregroundStyle(.white.opacity(0.9))
        .frame(maxWidth: .infinity, alignment: .leading)
        .frame(height: ExpandedLayout.displayHeight)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(SlotColor.backgroundTop)
        .clipShape(RoundedRectangle(cornerRadius: 4))
    }

    /// Fixed width reserved for the repo name — it truncates, not the
    /// message, so the message always knows exactly how much space remains.
    private let repoNameWidth: CGFloat = 64

    @ViewBuilder
    private var topLine: some View {
        HStack(spacing: 4) {
            if let pending = snapshot.pendingClaimCwd {
                Text("+").foregroundStyle(SlotColor.chromeStrong)
                Text(basename(pending)).lineLimit(1)
            } else if let slot {
                Text("\(slot.slot)").foregroundStyle(.white.opacity(0.5))
                Text(slot.commandLabel)
                    .lineLimit(1)
                    .truncationMode(.tail)
                    .onHover { hovering in isHoveringCommand = hovering }
            } else {
                Text("—").foregroundStyle(.white.opacity(0.3))
            }

            Spacer(minLength: 4)

            // Repo name pinned top-right, fixed width — secondary info now
            // that the command/message has the primary, flexible line.
            if snapshot.pendingClaimCwd == nil, let slot {
                Text(slot.displayName)
                    .lineLimit(1)
                    .truncationMode(.tail)
                    .frame(width: repoNameWidth, alignment: .trailing)
                    .foregroundStyle(.white.opacity(0.4))
            }
        }
    }

    @ViewBuilder
    private var bottomLine: some View {
        HStack {
            if isHoveringCommand, let slot {
                Text(slot.commandLabel)
                    .foregroundStyle(Color(hex: "#4F8CFF"))
                    .lineLimit(1)
            } else if let slot {
                Text(slot.statusPhrase)
                    .foregroundStyle(.white.opacity(0.5))
                    .lineLimit(1)
            } else if snapshot.pendingClaimCwd != nil {
                Text("tap a lit pad")
                    .foregroundStyle(.white.opacity(0.5))
            }
            Spacer(minLength: 0)
        }
    }

    private func basename(_ path: String) -> String {
        path.split(separator: "/").last.map(String.init) ?? path
    }
}
