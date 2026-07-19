import Foundation

/// Fixed sizing for the expanded surface's display + pad-grid layout (§2.3,
/// reinterpreted per a follow-up prompt as a mini display + 4×2 pad grid
/// mirroring the physical MPK, not a session list). Shared between the
/// SwiftUI views themselves and OverlayPanel's window-frame sizing, so the
/// window is always sized exactly to its content — no fittingSize queries
/// needed.
enum ExpandedLayout {
    static let padSize: CGFloat = 46
    static let padGap: CGFloat = 8
    static let gridColumns = 4
    static let gridRows = 2

    static let displayHeight: CGFloat = 42
    static let transportRowHeight: CGFloat = 26
    static let sectionGap: CGFloat = 8
    static let outerPadding: CGFloat = 10

    static var gridWidth: CGFloat {
        CGFloat(gridColumns) * padSize + CGFloat(gridColumns - 1) * padGap
    }

    static var gridHeight: CGFloat {
        CGFloat(gridRows) * padSize + CGFloat(gridRows - 1) * padGap
    }

    static var panelWidth: CGFloat {
        gridWidth + outerPadding * 2
    }

    static var panelHeight: CGFloat {
        displayHeight + sectionGap + gridHeight + sectionGap + transportRowHeight + outerPadding * 2
    }
}
