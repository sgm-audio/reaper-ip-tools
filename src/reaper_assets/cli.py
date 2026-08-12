"""Command-line interface for reaper-assets."""

import argparse
import json
import os
import sys

from . import __version__, catalog, docsgen, fx, merge, project, validate


def _cmd_generate(args):
    if args.spec:
        try:
            with open(args.spec, "r", encoding="utf-8") as f:
                spec = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[FATAL] could not read spec {args.spec!r}: {e}", file=sys.stderr)
            return 1
        default_name = os.path.splitext(os.path.basename(args.spec))[0]
    elif args.template:
        spec = catalog.get_template(args.template)
        default_name = args.template
    else:
        print("[FATAL] provide --template <name> or --spec <file>", file=sys.stderr)
        return 2

    name = args.name or default_name
    out_dir = args.out or name
    os.makedirs(out_dir, exist_ok=True)
    rpp_path = os.path.join(out_dir, f"{name}.rpp")

    text = project.generate_rpp_project(rpp_path, spec)
    docsgen.generate_docs(spec, out_dir, name=name)

    errors = validate.validate_rpp(text)
    if errors:
        print(f"[FATAL] generated RPP failed validation: {errors}", file=sys.stderr)
        return 1

    print(f"[OK] wrote {rpp_path}")
    print(f"[OK] wrote {out_dir}/session_map.md, routing_matrix.md, track_layout.csv")
    return 0


def _cmd_templates(args):
    for name in catalog.list_templates():
        print(f"{name:10s} {catalog.TEMPLATES[name]['description']}")
    return 0


def _cmd_merge(args):
    specs = [{"name": t} for t in args.track]
    merged = merge.merge_tracks_file(args.rpp, specs)
    print(f"[OK] merged {len(args.track)} track(s) into {args.rpp}")
    if args.verbose:
        print(f"[INFO] {len(merge.existing_track_names(merged))} tracks total")
    return 0


def _cmd_validate(args):
    errors = validate.validate_rpp_file(args.rpp)
    if errors:
        print("[FAIL] structural validation:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("[OK] structural validation passed")

    if args.round_trip:
        ok, msg = validate.roundtrip_check(args.rpp)
        if ok is None:
            print(f"[SKIP] {msg}")
        elif ok:
            print(f"[OK] {msg}")
        else:
            print(f"[FAIL] {msg}", file=sys.stderr)
            return 1
    return 0


def _cmd_check_plugins(args):
    spec = catalog.get_template(args.template)
    resolver = fx.PluginResolver(args.map)
    all_fx = []
    for t in spec.get("tracks", []):
        all_fx.extend(t.get("fx", []))
    unknown = resolver.missing(all_fx)
    if unknown:
        print(f"[WARN] plugins not resolvable (not stock, not in map): {unknown}")
        return 1
    print(f"[OK] all {len(all_fx)} FX references resolvable")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="reaper-assets",
        description="Emit canonical, valid REAPER .rpp session templates.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate a session template")
    g.add_argument("--template", help="named template (see 'templates')")
    g.add_argument("--spec", help="path to a JSON project spec")
    g.add_argument("-o", "--out", help="output directory")
    g.add_argument("--name", help="output base name (defaults to template/spec name)")
    g.set_defaults(func=_cmd_generate)

    t = sub.add_parser("templates", help="list available templates")
    t.set_defaults(func=_cmd_templates)

    m = sub.add_parser("merge", help="idempotently insert tracks into an existing .rpp")
    m.add_argument("rpp", help="target .rpp file")
    m.add_argument("--track", action="append", required=True, help="track name to add")
    m.add_argument("-v", "--verbose", action="store_true")
    m.set_defaults(func=_cmd_merge)

    v = sub.add_parser("validate", help="validate an .rpp file")
    v.add_argument("rpp", help="path to .rpp")
    v.add_argument(
        "--round-trip",
        action="store_true",
        help="also render in REAPER to confirm it loads",
    )
    v.set_defaults(func=_cmd_validate)

    c = sub.add_parser("check-plugins", help="verify FX references resolve")
    c.add_argument("--template", required=True, help="named template to check")
    c.add_argument("--map", help="path to reaper_plugin_map.json")
    c.set_defaults(func=_cmd_check_plugins)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
