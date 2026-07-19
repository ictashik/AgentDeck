// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "AgentDeckWidget",
    platforms: [.macOS(.v14)],  // NSScreen.auxiliaryTopLeftArea/RightArea require macOS 12+; onChange(of:initial:) requires 14+
    targets: [
        .executableTarget(
            name: "AgentDeckWidget",
            path: "Sources/AgentDeckWidget"
        )
    ]
)
