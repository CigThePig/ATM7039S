# Observation summaries

Parsed `tools/runtime_capture.py` outputs, one `OBS-NNN.json` per record in [observations.json](../observations.json). Raw captures stay outside the repository unless the device owner has reviewed them. [OBS-001](../../reports/v3-first-hardware-capture.md) records the first owner-operated V3 capture, including procedural limitations. Raw captures remain private.

Summaries from capture script version 3 carry `format_version` 2 and a `capture.state` of `authenticated-complete`, `authenticated-partial` or `quarantined`. Only an authenticated summary from a live device (no `fixture_root`, no `path_override`) can back an observation record; `research.py validate` enforces this.
