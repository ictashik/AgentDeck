import SwiftUI

/// Lets a pending (unbound) repo be claimed to a free slot purely by click —
/// the widget-side equivalent of pressing a blinking pad, so a new session
/// is usable with zero hardware attached (§3: "complete, standalone interface").
struct ClaimRowView: View {
    let cwd: String
    let freeSlots: [Int]
    let onClaim: (Int) -> Void

    private var basename: String {
        cwd.split(separator: "/").last.map(String.init) ?? cwd
    }

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .strokeBorder(SlotColor.chromeStrong, lineWidth: 1)
                .frame(width: 6, height: 6)
            Text(basename)
                .lineLimit(1)
            Spacer(minLength: 4)
            ForEach(freeSlots, id: \.self) { slot in
                Button {
                    onClaim(slot)
                } label: {
                    Text("\(slot)")
                        .font(.system(size: 10, design: .monospaced))
                        .frame(width: 16, height: 16)
                }
                .buttonStyle(.plain)
                .background(SlotColor.chrome.opacity(0.15))
                .clipShape(RoundedRectangle(cornerRadius: 3))
            }
        }
        .font(.system(size: 11, design: .monospaced))
        .foregroundStyle(.white.opacity(0.9))
        .padding(.vertical, 3)
        .padding(.horizontal, 8)
    }
}
