# Release manual tests

Run the app, load a structure that contains a ligand, and try the following in order.

1. **Typed manipulation:** “Show the ligand as sticks and color it yellow.” Confirm the live viewport changes.
2. **Multi-turn reference:** “Now select and show residues within 5 angstroms of it.” Confirm the model uses the ligand from the prior turn and leaves a named selection.
3. **Voice:** Click the microphone once and say “Color chain A cyan.” Stop speaking; confirm recording ends automatically after about one second, the transcript is sent, and the scene changes. Confirm the stop square still ends recording manually.
4. **Error recovery:** Ask “First try `cmd.not_a_real_method()` and then recover by coloring chain A green.” Choose **⋯ → Show Command Log** and confirm the API error is returned to the model and a valid follow-up call succeeds.
5. **No visual inspection:** Ask to frame a selected site. Confirm the command log uses `orient`, with no screenshot capture or repeated cosmetic adjustments. Even an explicit request for visual inspection must not capture/send an image.
6. **Files:** Drag a `.pdb`, `.cif`, `.mmcif`, or `.pse` onto the chat panel. Confirm it loads into the current session and is immediately available in the next prompt.
7. **Public fetch:** Ask “Download human hemoglobin.” Confirm the agent resolves a suitable public PDB accession, calls `cmd.fetch`, and loads it into the live scene.

## Packaged release checks

- Build from a clean source copy containing no ignored helper executable, `.env`, or build directory. Verify both native executables include arm64 and x86_64, and verify the app signature and DMG integrity.
- Copy the app out of the mounted DMG to a fresh test location and launch it. Confirm the packaged chat dock loads without the development checkout on its import path.
- Save a key once, quit the test PyMOL instance, and relaunch. Confirm the saved key is loaded without re-entry. Do not erase an existing key or microphone permission just to simulate a new user; test first-run permissions on a separate macOS account/device.
- Confirm microphone permission, automatic silence cutoff, transcription, and manual stop using actual speech. Confirm denial gives useful instructions. Existing permission on a developer machine does not establish first-install behavior.
- Confirm Marin speaks a reply, can be interrupted and muted, and the mute preference survives relaunch. Test with headphones if needed.
- Confirm the command log contains commands, results, and errors but no timing diagnostics. Confirm simple visual requests still complete promptly, medium reasoning remains configured, and named selections survive automatic deselection.
- Run the automated network-failure recovery tests; do not disconnect the user's whole machine. Confirm results from successful and partially failed operations survive a failed follow-up request.
- Before publishing, inspect the packaged files for keys and private data and verify README/install instructions match this version. Never include `.env` or recordings.
