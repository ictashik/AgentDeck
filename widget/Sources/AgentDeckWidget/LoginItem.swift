import ServiceManagement

/// "Launch at Login" toggle — modern SMAppService API, no second launchd
/// plist needed alongside the daemon's (tools/install_launchd.py).
enum LoginItem {
    static var isEnabled: Bool {
        SMAppService.mainApp.status == .enabled
    }

    static func setEnabled(_ enabled: Bool) {
        do {
            if enabled {
                try SMAppService.mainApp.register()
            } else {
                try SMAppService.mainApp.unregister()
            }
        } catch {
            // Best-effort, personal tool — nothing actionable to surface here.
        }
    }
}
