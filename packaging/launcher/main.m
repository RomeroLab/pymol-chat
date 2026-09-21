#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>

static void ShowError(NSString *message) {
    [NSApp activateIgnoringOtherApps:YES];
    NSAlert *alert = [[NSAlert alloc] init];
    alert.messageText = @"Chat with PyMOL";
    alert.informativeText = message;
    alert.alertStyle = NSAlertStyleCritical;
    [alert runModal];
}

static NSString *PyMOLExecutable(void) {
    NSFileManager *files = NSFileManager.defaultManager;
    NSMutableArray<NSString *> *candidates = [NSMutableArray array];
    NSString *saved = [NSUserDefaults.standardUserDefaults stringForKey:@"PyMOLApplication"];
    if (saved.length) [candidates addObject:saved];
    [candidates addObject:@"/Applications/PyMOL.app"];
    [candidates addObject:[NSHomeDirectory() stringByAppendingPathComponent:@"Applications/PyMOL.app"]];
    for (NSString *app in candidates) {
        NSString *executable = [app stringByAppendingPathComponent:@"Contents/bin/pymol"];
        if ([files isExecutableFileAtPath:executable]) return executable;
    }

    [NSApp activateIgnoringOtherApps:YES];
    NSOpenPanel *panel = [NSOpenPanel openPanel];
    panel.title = @"Choose PyMOL.app";
    panel.message = @"PyMOL must already be installed. Select the PyMOL application.";
    panel.canChooseFiles = YES;
    panel.canChooseDirectories = NO;
    panel.allowsMultipleSelection = NO;
    if ([panel runModal] != NSModalResponseOK) return nil;
    NSString *app = panel.URL.path;
    NSString *executable = [app stringByAppendingPathComponent:@"Contents/bin/pymol"];
    if (![files isExecutableFileAtPath:executable]) return nil;
    [NSUserDefaults.standardUserDefaults setObject:app forKey:@"PyMOLApplication"];
    return executable;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];

        NSString *pymol = PyMOLExecutable();
        if (!pymol) {
            ShowError(@"PyMOL could not be found. Install PyMOL, then open this launcher again.");
            return EXIT_FAILURE;
        }

        NSString *resources = NSBundle.mainBundle.resourcePath;
        NSString *loader = [resources stringByAppendingPathComponent:@"launch_plugin.py"];
        NSMutableDictionary *environment = [NSProcessInfo.processInfo.environment mutableCopy];
        NSString *oldPythonPath = environment[@"PYTHONPATH"];
        environment[@"PYTHONPATH"] = oldPythonPath.length
            ? [NSString stringWithFormat:@"%@:%@", resources, oldPythonPath]
            : resources;
        environment[@"PYMOL_CHAT_PORTABLE"] = @"1";
        // Keep Python caches outside the signed application bundle by not
        // writing bytecode. Mutating bundle resources invalidates its seal.
        environment[@"PYTHONDONTWRITEBYTECODE"] = @"1";

        NSTask *task = [[NSTask alloc] init];
        task.executableURL = [NSURL fileURLWithPath:pymol];
        task.arguments = @[@"-r", loader];
        task.environment = environment;
        task.currentDirectoryURL = [NSURL fileURLWithPath:NSHomeDirectory()];
        NSError *error = nil;
        if (![task launchAndReturnError:&error]) {
            ShowError([NSString stringWithFormat:@"PyMOL could not be started:\n%@", error.localizedDescription]);
            return EXIT_FAILURE;
        }
        [task waitUntilExit];
        return task.terminationStatus;
    }
}
