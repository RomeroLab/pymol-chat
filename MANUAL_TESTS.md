# MVP manual tests

Run the app, load a structure that contains a ligand, and try the following in order.

1. **Typed manipulation:** “Show the ligand as sticks and color it yellow.” Confirm the live viewport changes.
2. **Multi-turn reference:** “Now select and show residues within 5 angstroms of it.” Confirm the model uses the ligand from the prior turn and leaves a named selection.
3. **Voice:** Click the microphone once and say “Color chain A cyan.” Stop speaking; confirm recording ends automatically after about one second, the transcript is sent, and the scene changes. Confirm the stop square still ends recording manually.
4. **Error recovery:** Ask “First try `cmd.not_a_real_method()` and then recover by coloring chain A green.” Choose **⋯ → Show Command Log** and confirm the API error is returned to the model and a valid follow-up call succeeds.
5. **Vision:** Ask “Make this a clean publication view, inspect the viewport, and correct the framing if needed.” In the debug log, confirm a viewport capture occurs only when requested.
6. **Files:** Drag a `.pdb`, `.cif`, `.mmcif`, or `.pse` onto the chat panel. Confirm it loads into the current session and is immediately available in the next prompt.
7. **Public fetch:** Ask “Download human hemoglobin.” Confirm the agent resolves a suitable public PDB accession, calls `cmd.fetch`, and loads it into the live scene.
