CHAT WITH PYMOL — INSTALLATION

Requirements
• macOS 10.15 or newer
• PyMOL installed (normally /Applications/PyMOL.app)
• An OpenAI API key

Install
1. Drag “Chat with PyMOL” into the Applications folder.
2. Open “Chat with PyMOL”. It will find and launch PyMOL.
3. Paste your OpenAI API key when asked. The key is stored in your macOS
   login Keychain, not inside the application or a PyMOL session.
4. The chat panel opens at the bottom of PyMOL. Type a request or click the
   microphone once and speak.

Official releases are Developer ID signed and notarized by Apple. Open the
app normally and allow microphone access when prompted. If macOS cannot
verify an older copy, download the current release; do not disable Gatekeeper.
Local development builds are not notarized automatically.

Current installation guide:
https://github.com/RomeroLab/pymol-chat/blob/main/docs/INSTALL.md

To change or remove the saved key, choose “⋯ → API Key Settings…” in the
chat panel. A green dot next to the menu indicates that a key is active.

The launcher contains no API key and requires no Terminal commands or Python
package installation. API usage is billed to the account associated with the
configured key.

Spoken replies use Marin, an AI-generated OpenAI voice, with additional API
usage. Use “⋯ → Spoken Replies” to mute or enable them.
The application sends prompts, scene metadata, and molecular command results
to OpenAI, plus microphone recordings for transcription and reply text for
speech. It does not upload structure files or viewport screenshots.
