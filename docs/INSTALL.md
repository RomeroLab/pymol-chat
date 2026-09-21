# Installation guide

This guide installs Chat with PyMOL on macOS without using Terminal.

## 1. Install PyMOL

Chat with PyMOL runs inside an existing PyMOL installation. Install a Qt-based PyMOL 2.x release first, then confirm that `PyMOL.app` is in the macOS **Applications** folder and opens normally.

## 2. Download Chat with PyMOL

1. Visit the [latest GitHub release](https://github.com/RomeroLab/pymol-chat/releases/latest).
2. Under **Assets**, click `Chat-with-PyMOL-macOS.dmg`.
3. Wait for the download to finish, then open the DMG from the browser's downloads list or the Finder **Downloads** folder.

## 3. Install the application

Drag **Chat with PyMOL** onto the **Applications** shortcut shown in the DMG window. After it finishes copying, eject the disk image.

Open **Applications** in Finder and double-click **Chat with PyMOL**. The launcher starts PyMOL and adds the chat panel along the bottom of the PyMOL window.

If PyMOL is installed somewhere other than `/Applications/PyMOL.app`, the launcher will ask you to locate it. Select the correct `PyMOL.app` and click **Open**.

### If macOS blocks the application

The current build is ad-hoc signed rather than Apple-notarized. If macOS says it cannot verify the developer:

1. Open the Finder **Applications** folder.
2. Control-click **Chat with PyMOL**.
3. Choose **Open** from the shortcut menu.
4. Click **Open** in the confirmation window.

This exception is normally required only once.

## 4. Configure an OpenAI API key

The first launch displays an **OpenAI API Key** window.

1. Follow **Create or manage an API key** if you do not already have one.
2. Copy the key from the OpenAI dashboard.
3. Paste it into the application and click **Save**.

The application stores the key in your macOS login Keychain. For security, an active key is never displayed again. When a key is already configured, the window reports **API key active** and leaves the text field empty; that field is only for entering a replacement.

A green dot beside **⋯** indicates that a key is active. To replace or remove a Keychain key later, open **⋯ → API Key Settings…**.

The dot means a key is loaded, not that OpenAI has validated it. A saved Keychain key takes priority over development environment or `.env` keys. Updating the application does not erase the saved key.

API keys authenticate billed OpenAI API usage. Review usage and billing in the OpenAI Platform account associated with the configured key.

## 5. Enable voice input

Click the circular microphone control once. The first time, macOS asks whether **PyMOL Chat Voice** may access the microphone. Choose **Allow**.

Speak normally and pause when finished. Recording stops automatically after about one second of silence. You can click the square stop control to end it manually.

If microphone access was previously denied:

1. Open **System Settings**.
2. Choose **Privacy & Security → Microphone**.
3. Enable **PyMOL Chat Voice**.
4. Restart Chat with PyMOL.

## 6. Spoken replies

Replies can be read aloud using Marin, an AI-generated OpenAI voice. This sends reply text to OpenAI and incurs additional API usage. Use **⋯ → Spoken Replies** to mute or enable speech. Starting a new request also stops speech. If Qt audio support is unavailable, written chat remains usable.

## Updating the application

Download the newer DMG, quit PyMOL, and replace the existing **Chat with PyMOL** application in Applications. The API key remains in Keychain, so it does not normally need to be entered again.

## Uninstalling

Quit PyMOL and move **Chat with PyMOL** from Applications to the Trash. To remove the stored API key first, choose **⋯ → API Key Settings… → Remove Key**.

Temporary application data is stored in `~/.pymol-chat`. Removing that folder is optional and does not affect PyMOL itself.

## Troubleshooting

### The panel does not appear

In PyMOL, choose **Plugin → Chat with PyMOL**. If that menu item is absent, quit both applications and launch PyMOL through **Chat with PyMOL** again.

### The green key dot is missing

Open **⋯ → API Key Settings…** and add a valid OpenAI API key. Confirm that the API account has billing enabled and available usage.

### A request returns a connection error

Confirm that the Mac has internet access and that its network allows connections to `api.openai.com`. Then retry the request.

### Voice input does not stop automatically

Speak close enough to the selected system microphone, then leave a clear pause. Silent recordings time out after eight seconds, and all recordings stop after 30 seconds.

### Inspecting executed commands

Choose **⋯ → Show Command Log** to view generated PyMOL commands, results, and errors without timing diagnostics. Visual inspection is disabled; the app uses PyMOL commands for framing instead of screenshot/revision loops.

### A key is loaded but requests fail

If OpenAI reports an expired or invalid key, replace it through **⋯ → API Key Settings…**. If the saved key cannot be read after restarting, check macOS Keychain access; the application may fall back to development configuration. Do not share keys or screenshots containing keys when reporting a problem.

### A request stops before all work is finished

Each request permits three command rounds, then a final summary of completed and unfinished work. Ask a follow-up to continue a larger task. If a connection error occurs after the scene changes, ask what completed before repeating a destructive operation; execution results are retained for the next turn in the same session.
