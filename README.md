# Chat with PyMOL

Chat with PyMOL adds a compact natural-language assistant directly to the PyMOL interface. It can inspect the active session and perform PyMOL operations from typed or spoken requests while keeping the molecular viewer as the main workspace.

![Chat with PyMOL controlling a human hemoglobin structure](docs/images/chat-with-pymol.png)

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

> This development build is ad-hoc signed. If macOS blocks the first launch, Control-click **Chat with PyMOL**, select **Open**, and confirm. A future Developer ID-signed and notarized release will not require this workaround.

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

The previous release, v1.0.0, remains available on the GitHub releases page.

Simple visual changes can now use a prepared confirmation immediately after successful execution, skipping the follow-up model request. This shortcut requires one tool call, a nonempty-selection assertion, supported direct visual commands, and no diagnostic output. Measurements, interpretation, errors, and more complex operations still use the normal review loop. Tool results and the confirmation are retained for the next conversation turn.

Visual inspection is disabled: the chat agent does not capture or send viewport screenshots. It is instructed to use `orient(selection)` for orientation and framing, preserve the camera when reframing is unnecessary, batch related changes, and stop after successful completion rather than refine appearance in repeated rounds. Requests allow at most three command rounds (including structural queries and repairs), followed by a tools-disabled final response describing results and any unfinished work. Longer tasks may need a follow-up request. Active selection markers are cleared after every executed batch; named selections remain available.

Sol uses medium reasoning effort by default. Set `OPENAI_REASONING_EFFORT=low` to try faster responses, with a potential tradeoff in complex-task quality. The command log shows executed commands, results, and errors without timing diagnostics. The direct-confirmation shortcut and streaming Marin playback remain enabled.

## Requirements

- macOS 10.15 or newer
- A Qt-based PyMOL 2.x installation
- An OpenAI API key with API billing enabled
- Internet access for OpenAI requests and optional PDB downloads

The default model is `gpt-5.6-sol`. Set `OPENAI_MODEL` to override it in development installations. Voice requests use `gpt-4o-mini-transcribe` by default.

## Privacy and security

- The application does not upload local structure files or capture/send viewport screenshots.
- Prompt text, compact scene metadata, generated commands, and command results are sent to OpenAI. Results may include molecular information such as residue identities, coordinates, distances, or sequences queried from a local structure. Do not use confidential structures unless this disclosure is permitted.
- Voice recordings are sent to OpenAI for transcription; reply text is sent for Marin speech generation when spoken replies are enabled.
- Temporary recordings and structures downloaded through `cmd.fetch` are stored under `~/.pymol-chat` by default. Older versions may have left viewport captures there.
- Generated Python is checked before execution to restrict common shell, filesystem, networking, and unsafe PyMOL command paths. These checks are not an operating-system sandbox. Review important changes and save your PyMOL session before destructive requests.
- Public structure retrieval through `cmd.fetch` is allowed and redirected to the private application directory.

## Development

Clone the repository and launch the development version:

```bash
chmod +x run.sh
./run.sh
```

Either enter an API key through **⋯ → API Key Settings…**, export `OPENAI_API_KEY`, or copy `.env.example` to `.env` and configure it locally. The `.env` file is ignored by Git.

Run the automated tests with PyMOL's Python:

```bash
QT_QPA_PLATFORM=minimal /Applications/PyMOL.app/Contents/bin/python \
  -m unittest discover -s tests -v
```

Build the universal macOS application and DMG:

```bash
./build_dmg.sh
```

The resulting installer is written to `outputs/Chat-with-PyMOL-macOS.dmg`.

## Project structure

- `pymol_chat/ui.py` — native Qt dock and background task handling
- `pymol_chat/agent.py` — Responses API tool loop
- `pymol_chat/executor.py` — live PyMOL execution and safety checks
- `pymol_chat/audio.py` — one-click voice capture and transcription
- `pymol_chat/api_client.py` — dependency-free OpenAI HTTPS client
- `pymol_chat/keychain.py` — macOS Keychain integration
- `voice_helper/` — native silence-detecting microphone helper
- `packaging/` — universal macOS launcher sources
- `build_dmg.sh` — reproducible DMG build script

The model receives one local tool: direct PyMOL/Python execution. Failed commands are returned for correction within the three-command-round budget, followed by a tools-disabled final response. Completed execution results are retained in memory if a subsequent network request fails, so the next turn receives that history. This recovery does not persist across quitting PyMOL and does not guarantee that the model will never repeat an action.

## License

Chat with PyMOL is released under the [MIT License](LICENSE).
