import SwiftUI

/// §2.3: one dense line per session (dot + slot number + repo + detail),
/// monospace so columns align. Only actionable rows break onto a second
/// line, for the inline decision affordance — §6's one explicit exception
/// to "one line per session."
struct SlotRowView: View {
    let slot: SlotState
    let isFocused: Bool
    let onResolve: (String) -> Void
    let onRaise: () -> Void
    let onFocus: () -> Void
    let onUnbind: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 6) {
                SlotDotView(slot: slot, diameter: 6)
                Text("\(slot.slot)")
                    .frame(width: 12, alignment: .trailing)
                Text(slot.displayName)
                    .lineLimit(1)
                Spacer(minLength: 4)
                Text(slot.detail ?? slot.state)
                    .lineLimit(1)
                    .foregroundStyle(.white.opacity(0.55))
                    .frame(maxWidth: 140, alignment: .trailing)
            }
            .font(.system(size: 11, design: .monospaced))
            .foregroundStyle(.white.opacity(0.9))
            .padding(.vertical, 3)
            .padding(.horizontal, 8)
            .background(
                RoundedRectangle(cornerRadius: 3)
                    .fill(isFocused ? SlotColor.chrome.opacity(0.12) : .clear)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 3)
                    .strokeBorder(isFocused ? SlotColor.chromeStrong : .clear, lineWidth: 1)
            )
            .contentShape(Rectangle())
            .onTapGesture { onFocus() }
            .contextMenu {
                Button("Raise window", action: onRaise)
                if slot.repo != nil {
                    Button("Unbind", role: .destructive, action: onUnbind)
                }
            }

            if slot.state == "waiting_permission" {
                HStack(spacing: 6) {
                    actionButton("Allow") { onResolve("allow") }
                    actionButton("Allow Always") { onResolve("allow_always") }
                    actionButton("Deny") { onResolve("deny") }
                }
                .padding(.leading, 24)
                .padding(.bottom, 2)
            } else if slot.state == "waiting_question" {
                HStack(spacing: 6) {
                    actionButton("Go to window", action: onRaise)
                }
                .padding(.leading, 24)
                .padding(.bottom, 2)
            }
        }
    }

    private func actionButton(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 10, design: .monospaced))
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
        }
        .buttonStyle(.plain)
        .background(SlotColor.chrome.opacity(0.15))
        .clipShape(RoundedRectangle(cornerRadius: 3))
    }
}
