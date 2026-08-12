"""Legacy entry point — kept for backward compatibility.

Delegates RPP generation to the ``reaper_assets`` package. Run:

    python generate_reaper_assets.py

which still produces ``generated_assets/clean_slate_reset.eel`` and
``generated_assets/auto_session_v1.rpp`` as before, but now through the
validated, canonical emitter.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from reaper_assets import catalog, generate_rpp_project, validate

EEL_SCRIPT = r"""
// @description Auto-Generated Hard Reset Utility
// @version 1.0
// @author Scott Mills (Automated)

function main()
(
    Undo_BeginBlock();
    count = CountTracks(0);
    i = 0;
    loop(count,
        tr = GetTrack(0, i);
        SetMediaTrackInfo_Value(tr, "D_VOL", 1.0); // Reset to 0dB (linear gain 1.0)
        SetMediaTrackInfo_Value(tr, "D_PAN", 0.0); // Center pan
        i += 1;
    );
    Undo_EndBlock("Hard Reset All Tracks", -1);
);

main();
""".strip()


def generate_eel_script(output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(EEL_SCRIPT + "\n")


def main():
    output_dir = "./generated_assets"
    eel_path = os.path.join(output_dir, "clean_slate_reset.eel")
    rpp_path = os.path.join(output_dir, "auto_session_v1.rpp")

    generate_eel_script(eel_path)
    print(f"[SUCCESS] EEL2 Asset Generated: {eel_path}")

    spec = catalog.get_template("mixing")
    generate_rpp_project(rpp_path, spec)
    print(f"[SUCCESS] RPP Project Generated: {rpp_path}")

    errors = validate.validate_rpp_file(rpp_path)
    if errors:
        print("[FATAL] RPP validation failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("[OK] RPP passed structural validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
