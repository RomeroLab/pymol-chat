# Development guide

## Run from source

Use macOS with a Qt-based PyMOL 2.x installation. The application uses PyMOL's Python and Qt; no additional Python packages are required. Building the native microphone helper requires Apple's Xcode Command Line Tools.

```bash
git clone https://github.com/RomeroLab/pymol-chat.git
cd pymol-chat
chmod +x run.sh voice_helper/build.sh build_dmg.sh
./run.sh
```

Set `PYMOL_APP` if PyMOL is not at `/Applications/PyMOL.app`.

Enter an API key through **⋯ → API Key Settings…**, export `OPENAI_API_KEY`, or copy `.env.example` to `.env`. A saved Keychain key takes priority over environment configuration. Never commit a real key; `.env` is ignored by Git.

## Configuration

The default model is `gpt-5.6-sol`, with medium reasoning. Development overrides include `OPENAI_MODEL`, `OPENAI_REASONING_EFFORT`, and `OPENAI_TRANSCRIBE_MODEL` (default `gpt-4o-mini-transcribe`). Spoken replies use Marin through `gpt-4o-mini-tts`, with a 300 ms playback buffer.

## Execution behavior

The model receives one local tool for PyMOL/Python execution. Requests permit at most three command rounds, then a tools-disabled final response. The assistant uses `orient(selection)` for framing and does not capture screenshots.

Simple visual operations can use a prepared confirmation after successful execution, avoiding an extra model round. This requires one tool call, a nonempty-selection assertion, supported direct visual commands, and no diagnostic output. Measurements, interpretation, errors, and complex operations use the normal review loop.

Completed and partially failed execution results are retained in memory if a subsequent network request fails. This recovery does not survive quitting PyMOL or guarantee that an action will never be repeated. Generated-code checks are not an operating-system sandbox.

## Tests

```bash
QT_QPA_PLATFORM=offscreen /Applications/PyMOL.app/Contents/bin/python -B \
  -m unittest discover -s tests -v
```

Also complete the [manual release checklist](../MANUAL_TESTS.md), especially microphone permissions and spoken requests on a separate macOS account or device.

## Build

```bash
./build_dmg.sh
```

This builds universal arm64/x86_64 executables and writes `outputs/Chat-with-PyMOL-macOS.dmg`. The default build is ad-hoc signed for development, **not notarized for distribution**.

For distribution, set `PYMOL_CHAT_SIGNING_IDENTITY` to a valid full Developer ID Application identity in your Keychain. Set `PYMOL_CHAT_DMG_OUTPUT` to a new output path to preserve an existing release. The script signs nested code before the outer app, with hardened runtime and microphone entitlements. Apple notarization, stapling, and Gatekeeper verification are separate release steps; the script does not perform them. Any change to the distributed app or DMG requires a new signed/notarized artifact.

## Source layout

- `pymol_chat/` — Qt interface, model execution, API client, Keychain, and audio
- `voice_helper/` — native silence-detecting microphone helper
- `packaging/` — launcher, app metadata, entitlements, and installer Read Me
- `tests/` — automated regression tests
- `launch_plugin.py` and `run.sh` — development entry points
- `build_dmg.sh` — macOS distribution build

Build outputs, recordings, local structures, and credentials do not belong in the repository.
