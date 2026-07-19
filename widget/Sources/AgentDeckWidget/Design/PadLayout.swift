import Foundation

/// The physical MPK's pad numbering, shared by every surface that lays pads
/// out as a grid (the expanded view's PadGridView, and the compact pill's
/// dot grid) so there's exactly one place that says which slot sits where.
/// Standard Akai MPC-style numbering: pad 1 is bottom-left, ascending right
/// across the bottom row, then continuing left-to-right on the top row.
enum PadLayout {
    static let topRow = [5, 6, 7, 8]
    static let bottomRow = [1, 2, 3, 4]
}
