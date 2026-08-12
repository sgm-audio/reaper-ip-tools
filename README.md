# reaper-assets

Emit **canonical, valid REAPER `.rpp` session templates** programmatically, and
package them with documentation. Chunk formats are verified against REAPER's
own output (the user's installed Project Templates) — nothing is fabricated.

## Install

```bash
uv sync --group dev        # or: pip install -e .
reaper-assets --version
```

## CLI

```bash
# List named templates
reaper-assets templates

# Generate a template (RPP + docs)
reaper-assets generate --template podcast -o ./podcast_session

# Generate from a custom JSON spec
reaper-assets generate --spec my_spec.json -o ./out

# Idempotently add tracks to an existing project
reaper-assets merge ./existing.rpp --track "GUEST 3" --track "MUSIC BED"

# Validate a project (structural + optional REAPER round-trip)
reaper-assets validate ./out/podcast.rpp --round-trip

# Verify FX references resolve to real plugin UIDs
reaper-assets check-plugins --template podcast --map reaper_plugin_map.json
```

## Python API

```python
from reaper_assets import generate_rpp_string, catalog, validate

spec = catalog.get_template("podcast")
text = generate_rpp_string(spec)
assert validate.validate_rpp(text) == []
open("podcast.rpp", "w").write(text)
```

## Templates

`podcast`, `mixing`, `mastering`, `live`, `scoring` (see `catalog.py`).

## Project layout

```
src/reaper_assets/
  builder.py    ReaperProjectBuilder, write_track/master/envelope
  project.py    generate_rpp_string / generate_rpp_project (assembly)
  fx.py         verified stock Cockos FX + PluginResolver (real UIDs)
  routing.py    AUXRECV sends + folder (ISBUS) encoding
  markers.py    MARKER / REGION emission
  catalog.py    named session templates
  docsgen.py    session_map.md / routing_matrix.md / track_layout.csv
  merge.py      idempotent track insertion
  validate.py   structural + REAPER round-trip validation
  version.py    REAPER version detection
  cli.py        command-line interface
```

Companion scripts:
- `extract_reaper_uuids.py` / `.lua` — dump plugin `name -> uid` from REAPER's ini.
- `extract_stock_fx.py` — re-extract stock FX state from Project Templates.

## Notes / limitations

- **Third-party plugin state** is not reproducible from `reaper-vstplugins64.ini`
  (identity only). `PluginResolver` prevents *fabricated* UIDs; full state
  emission is supported only for the verified stock Cockos plugins.
- **Folder depth** is single-level (`parent` / `child` / `end`). Nested folders
  are not emitted.
- **REAPER round-trip** is opt-in and requires a REAPER install; it renders the
  project headlessly and treats a clean exit as proof of successful parsing.
