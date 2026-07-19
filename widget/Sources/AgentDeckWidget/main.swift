import AppKit

// Plain imperative bootstrap rather than the SwiftUI `App` protocol — this
// app has no `Scene` it actually wants (no WindowGroup, no MenuBarExtra);
// the one custom NSPanel is fully AppKit-managed (see OverlayPanel.swift).
let delegate = AppDelegate()
let app = NSApplication.shared
app.delegate = delegate
app.setActivationPolicy(.accessory)  // no Dock icon, no app-switcher entry
app.run()
