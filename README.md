# Chat with PyMOL

Chat with PyMOL adds a compact natural-language assistant directly to the PyMOL interface. It can inspect the active session and perform PyMOL operations from typed or spoken requests while keeping the molecular viewer as the main workspace.

Watch Chat with PyMOL explore chymotrypsin using voice commands and spoken responses (sound on).

https://github.com/user-attachments/assets/53dca1be-80e7-41cd-b999-4371dd69a3c7

## Install on macOS

The packaged application is the easiest installation method. It supports Apple Silicon and Intel Macs and does not require Terminal commands or Python package installation.

1. Install PyMOL and place `PyMOL.app` in your **Applications** folder.
2. Download `Chat-with-PyMOL-macOS.dmg` from the [latest release](https://github.com/RomeroLab/pymol-chat/releases/latest).
3. Open the downloaded DMG.
4. Drag **Chat with PyMOL** onto the **Applications** shortcut.
5. Open **Chat with PyMOL** from Applications. The launcher will find PyMOL and open the assistant automatically.
6. Paste an OpenAI API key when prompted. Use the link in that window to create or manage keys.
7. On the first voice request, allow microphone access for **PyMOL Chat Voice**.

The API key is stored in the macOS login Keychain. It is never embedded in the application or saved in PyMOL session files. A green dot beside the options menu means a key is active.

> The current macOS installer is Developer ID-signed by Philip Romero and notarized by Apple. Open it normally; macOS may show a standard first-launch confirmation and request microphone access. If you downloaded an older installer, download the current release again.

For detailed installation help and troubleshooting, see [docs/INSTALL.md](docs/INSTALL.md).

## Use

Open a structure using PyMOL's normal controls, then type a request and press Return. For example:

- `Show the protein as a cartoon and color each chain differently.`
- `Select residues within 4 angstroms of the ligand.`
- `Download 2HHB and show the heme groups as sticks.`
- `Make a clean publication-style view.`

Click the microphone once to speak. Recording stops automatically after a short pause. The **⋯** menu contains API key settings and an optional command log.

Keys saved through **⋯ → API Key Settings** are stored in macOS Keychain and take priority over `OPENAI_API_KEY` or a development `.env` file, including after restarting PyMOL. Environment configuration is used only when no saved key is readable. The replacement field stays blank for privacy; a green status dot indicates that a key is loaded, not that it has been validated by OpenAI.

### Spoken replies

Replies can be read aloud with **Marin**, an AI-generated OpenAI voice using `gpt-4o-mini-tts`. Reply text is sent to OpenAI for speech generation, with additional API usage charges. Audio streams directly to the speakers without saving a recording, with a 300 ms startup buffer for smoother playback. Turn **⋯ → Spoken Replies** off to mute them. Starting another request or the microphone also stops playback. Your mute preference is remembered. Speech errors leave the written reply available in chat.

The assistant uses PyMOL commands to frame structures, without capturing screenshots. Active selection markers are cleared after commands; named selections remain available. Larger tasks may need a follow-up request.

## Requirements

- macOS 10.15 or newer
- A Qt-based PyMOL 2.x installation
- An OpenAI API key with API billing enabled
- Internet access for OpenAI requests and optional PDB downloads

The packaged release is for macOS. Windows and Linux installers are not currently provided or tested. PyMOL is installed separately and is not bundled with this application.

## Privacy and security

- The application does not upload local structure files or capture/send viewport screenshots.
- Prompt text, compact scene metadata, generated commands, and command results are sent to OpenAI. Results may include molecular information such as residue identities, coordinates, distances, or sequences queried from a local structure. Do not use confidential structures unless this disclosure is permitted.
- Voice recordings are sent to OpenAI for transcription; reply text is sent for Marin speech generation when spoken replies are enabled.
- Temporary recordings and structures downloaded through `cmd.fetch` are stored under `~/.pymol-chat` by default. Older versions may have left viewport captures there.
- Generated Python is checked before execution to restrict common shell, filesystem, networking, and unsafe PyMOL command paths. These checks are not an operating-system sandbox. Review important changes and save your PyMOL session before destructive requests.
- Public structure retrieval through `cmd.fetch` is allowed and redirected to the private application directory.

## Development

See [the development guide](docs/DEVELOPMENT.md) for source setup, configuration, tests, and builds. The [release checklist](MANUAL_TESTS.md) covers hands-on validation.

## Support

Report bugs through [GitHub Issues](https://github.com/RomeroLab/pymol-chat/issues). Include your macOS and PyMOL versions, the steps to reproduce the problem, and any relevant error message. Do not include API keys or confidential molecular data.

## License

Chat with PyMOL is released under the [MIT License](LICENSE).
