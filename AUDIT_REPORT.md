# QA / Audit Report — reaper-ip-tools

Branch: `arena/ef503613-reaper-ip-tools` (from `d94f85a`)
Date: 2026-11-12
Scope: Python package `reaper_assets`, companion scripts, and generated REAPER-targeted output.

## 1. Headline finding

**There are no ReaScripts (Lua/EEL `.lua`/`.eel` files checked into the repo,
and no `index.xml` ReaPack feed).** Commit `d94f85a` ("chore(reapack): pull
release - remove index.xml and scripts so feed 404s") removed them, and the
README previously documented six Lua scripts plus `podcast_template/bootstrap.lua`
that no longer exist. The README has been updated to state this explicitly.

What remains that targets REAPER:
- `src/reaper_assets/` — emits canonical `.rpp` session data (tracks, folders,
  sends, markers/regions, stock FX chains).
- `generate_reaper_assets.py` — emits `generated_assets/clean_slate_reset.eel`,
  an EEL2 script, plus an `.rpp` via the package.
- `podcast_template/template.RPP` — a stub project (notes only) that awaits
  the missing `bootstrap.lua`.

Verification below covers everything that *is* present, checked against the
official REAPER documentation and against real REAPER-saved project files.

## 2. Verification sources

- Official ReaScript API reference (REAPER v7.85):
  https://www.reaper.fm/sdk/reascript/reascripthelp.html — fetched live;
  function list confirms EEL2/Lua/Python signatures.
- Ground-truth REAPER 7.x project files in `tests/fixtures/`
  (`voice_over.rpp` = REAPER 7.57/win64, `broadcast_ready.rpp` = 7.69/linux,
  `NewProject.rpp` = 7.38/win64), plus public GitHub mirrors of `.rpp` files
  (ddf/evaluator, efairbanks/tb-303-plugin, cpmpercussion/Studio1-Demo).
- No REAPER executable is available in this environment, so the opt-in
  `validate --round-trip` check (which renders headlessly in REAPER) is
  skipped gracefully everywhere; structural validation substitutes for it.

## 3. Lint

Tooling installed into a throwaway venv (not committed): `ruff 0.17.5`,
`pytest` (via PyPI).

- `ruff check .` — clean (0 findings).
- `ruff format --check .` — clean.
- `python -m py_compile` on all Python modules — clean.
- PEP 668 environment: tests ran in `/home/user/.venv-qa` with the package
  installed editable (`pip install -e .`).

## 4. Tests

`pytest` — **50 passed** (45 pre-existing + 5 added):

| File | Tests |
| --- | --- |
| test_builder.py | 6 |
| test_cli.py | 4 |
| test_docsgen.py | 3 |
| test_fx.py | 10 |
| test_markers.py | 4 |
| test_merge.py | 7 |
| test_project.py | 6 |
| test_routing.py | 3 |
| test_validate.py | 5 |
| test_extract_uuids.py | 2 (new) |

Coverage: builder grammar, stock FX descriptors & UIDs, FXCHAIN emission,
routing (AUXRECV, ISBUS folder encoding), markers/regions, catalog templates,
docs generation, idempotent merge, structural validation, CLI commands, and
ini parsing for `extract_reaper_uuids.py`.

## 5. Conformance vs the official REAPER RPP format / ReaScript API

### 5.1 RPP generator (`builder.py`, `project.py`, `fx.py`, `routing.py`, `markers.py`)

Checked line-by-line against `tests/fixtures/*.rpp` (REAPER's own output).
All conformant:

| Element | Generator | REAPER ground truth | Status |
| --- | --- | --- | --- |
| Project header | `<REAPER_PROJECT 0.1 "X.YY/win64" <ts>` | matches fixtures | OK |
| Master block | `MASTERAUTOMODE … MASTER_SEL` (no master FXCHAIN) | matches `voice_over.rpp` | OK |
| Envelopes | `MASTERPLAYSPEEDENV`, `TEMPOENVEX` with `EGUID`/`ACT`/`VIS`/`DEFSHAPE` | matches fixtures | OK |
| Settings | `TIMEMODE 1 5 -1 30 0 0 -1`, `GRID 3199 …`, `RENDER_RANGE 1 0 0 18 1000`, `SMPTESYNC …` | matches fixtures | OK |
| Track field order | NAME, PEAKCOL, BEAT, AUTOMODE, PANLAWFLAGS, VOLPAN … MAINSEND, [FXCHAIN] | matches fixtures | OK |
| Track GUID | `<TRACK {GUID} … TRACKID {GUID}` identical | matches fixtures | OK |
| Folder encoding | parent `ISBUS 1 1`, child `ISBUB 0 0`, end `ISBUS 2 -1` | matches `broadcast_ready.rpp` | OK |
| Sends | `AUXRECV <src> 0 <mode> 0 0 0 0 0 0 -1:U <vol> -1 ''` on receiver | matches fixtures | OK |
| VST node | `<VST "VST: … (Cockos)" dll 0 "" uid<hex> ""` + base64 state | matches fixtures verbatim | OK |
| Stock plugin UIDs | ReaEQ 1919247729, ReaComp 1919247213, ReaGate 1919248244, ReaLimit 1919708532 | match fixture UIDs exactly | OK |
| FXID / WAK | emitted at FXCHAIN level immediately after each `>` VST closer | matches fixtures verbatim | OK |
| MARKER / REGION | `MARKER <idx> <pos> "<name>" <id> <color> 1 R {GUID} 0 2 [end]` | matches fixtures verbatim | OK |
| Marker indexing | single increasing counter across markers + regions | matches REAPER convention | OK |

One deliberate conformance fix: `project.py` wrote `<METRONOME 6 0>`; every
ground-truth project writes `<METRONOME 6 2>`. Changed to `6 2` (node open
line intentionally has no trailing `>` on the same line, matching REAPER's
own writer style).

Noted cosmetic differences vs REAPER-saved files (REAPER fills these in on
save; they do not affect loadability): no `FLOAT`/`FLOATPOS` window-position
line after VST nodes; `VU 2` instead of session-specific meter values;
`MASTERPEAKCOL 16576` default.

### 5.2 EEL2 asset (`generate_reaper_assets.py` → `clean_slate_reset.eel`)

API calls verified against the official EEL2 function list:

| Call | Official EEL2 API | Verdict |
| --- | --- | --- |
| `Undo_BeginBlock()` | `void Undo_BeginBlock()` | OK |
| `CountTracks(0)` | in API function list | OK |
| `GetTrack(0, i)` | `MediaTrack GetTrack(ReaProject proj, int trackidx)` | OK |
| `SetMediaTrackInfo_Value(tr, "D_VOL", 1.0)` | `bool SetMediaTrackInfo_Value(MediaTrack tr, "parmname", newvalue)` | OK |
| `Undo_EndBlock("…", -1)` | `void Undo_EndBlock(string desc, int flags)` | OK |
| `loop(count, …)` | EEL2 built-in | OK |

Syntax follows EEL2 convention (`function main() ( … );` parenthesized
function body, as used by JSFX/EEL2). Could not be executed (no REAPER), so
this is an API-level verification only.

### 5.3 `validate.py`

Structural checks (header, terminal `>`, balanced node depth, no quoted
numerics) pass on all fixtures and on all generated output. Round-trip
rendering in REAPER is opt-in and returns `[SKIP]` when `reaper.exe` is
absent.

## 6. Bugs fixed in this audit

1. `src/reaper_assets/project.py` — `METRONOME 6 0` → `METRONOME 6 2`
   to match REAPER ground truth.
2. `extract_reaper_uuids.py` — `os.environ["APPDATA"]` raised `KeyError`
   when APPDATA unset; now falls back gracefully. Plugin names are now
   stripped of surrounding quotes (the comment promised it; the code
   didn't).
3. `extract_stock_fx.py` — removed unused `_STATE_START` regex; the state
   collector now skips `FLOAT`/`FLOATPOS`/`FXID`/`WAK`/`BYPASS` lines
   inside `<VST>` nodes, keeping extracted state blobs shaped like the
   hardcoded `STOCK_PLUGINS` descriptors.

Audit-reopened item that turned out **not** to be a bug: `write_vst_node`
emits `FXID`/`WAK` after the `>` that closes each `<VST>` node (at
FXCHAIN level). That initially looked like a nesting error, but it matches
REAPER's own output exactly (see `voice_over.rpp`), so no change was made.

## 7. Known gaps (not fixed)

- **Missing ReaScripts.** The Lua scripts named in the old README
  (`extract_reaper_uuids.lua`, `plugin_map_generator.lua`, `fx_inserter.lua`,
  `generate_reaper_assets.lua`, `session_generator.lua`, `rpp_helpers.lua`,
  `podcast_template/bootstrap.lua`) and `index.xml` are absent. To ship a
  working ReaPack feed they would need to be restored and each function call
  re-verified against the official EEL2/Lua API list at
  reaper.fm/sdk/reascript/reascripthelp.html.
- **No REAPER round-trip.** `validate --round-trip` cannot run without a
  REAPER install; structural validation is the substitute.
- **EEL2 script not runtime-tested.** `clean_slate_reset.eel` is API-verified
  only.
- **Third-party plugin state.** `PluginResolver` resolves identity (UID,
  filename, type) from `reaper-vstplugins64.ini`/`reaper-clap-win64.ini` but
  cannot reproduce third-party plugin state — only the four stock Cockos
  plugins emit verified state. Documented limitation; not a regression.
- `extract_reaper_uuids.py` only scans `reaper-vstplugins64.ini`; CLAP ini
  parsing is not implemented (documented as future work in `fx.py`).

## 8. Recommendations

1. Decide whether to restore the removed Lua ReaScripts and `index.xml`, or
   keep the README as-is (now corrected) and drop ReaPack claims.
2. Add a REAPER round-trip smoke test to CI on Windows/macOS where REAPER is
   installed (`validate --round-trip`).
3. Execute `clean_slate_reset.eel` in REAPER once to confirm runtime
   behavior (undo block, track volume/pan reset).
4. Consider running `extract_stock_fx.py` against the local Project Templates
   on a machine with REAPER installed to refresh `STOCK_PLUGINS` when REAPER
   versions change.
