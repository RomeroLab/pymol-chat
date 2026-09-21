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

If macOS blocks this build, Control-click the application, choose
Open, and confirm once. A public release should be Developer ID signed and
notarized so this step is unnecessary.

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
