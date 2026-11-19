import json
import os
import platform

VST_INI_CANDIDATES = (
    "reaper-vstplugins64.ini",
    "reaper-vstplugins_x86_64.ini",
    "reaper-vstplugins_arm64.ini",
    "reaper-vstplugins-arm64.ini",
    "reaper-vstplugins_aarch64.ini",
    "reaper-vstplugins.ini",
)


def get_reaper_resource_path():
    """
    Attempts to auto-detect the REAPER resource path on Windows/Mac/Linux.
    """
    system = platform.system()
    if system == "Windows":
        # Standard portable or installed path (APPDATA may be unset in some
        # environments -- fall back through to the user prompt rather than
        # raising KeyError).
        appdata = os.environ.get("APPDATA")
        if appdata:
            path = os.path.join(appdata, "REAPER")
            if os.path.exists(path):
                return path
    elif system == "Darwin":  # Mac
        path = os.path.expanduser("~/Library/Application Support/REAPER")
        if os.path.exists(path):
            return path
    elif system == "Linux":
        path = os.path.expanduser("~/.config/REAPER")
        if os.path.exists(path):
            return path

    # Fallback: Ask user if not found
    print("Could not auto-detect REAPER folder.")
    try:
        return input("Enter full path to REAPER resource folder: ").strip()
    except EOFError:
        return ""


def find_vst_ini(resource_path):
    """Return the first existing platform-specific REAPER VST plugin cache ini."""
    if not resource_path:
        return None
    for filename in VST_INI_CANDIDATES:
        candidate = os.path.join(resource_path, filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def parse_reaper_ini(ini_path):
    """
    Parses REAPER's ``reaper-vstplugins*.ini`` cache file.
    Real REAPER format: ``filename=mtime_size_hash,plugin_uid,Display Name``
    """
    plugins = {}

    if not ini_path or not os.path.exists(ini_path):
        print(f"[ERROR] Could not find {ini_path}")
        return {}

    print(f"Scanning: {ini_path}...")

    with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(("[", ";", "#")):
                continue

            # Split only on the first equals sign to separate Filename from Data
            if "=" not in line:
                continue

            filename, data = line.split("=", 1)
            filename = filename.strip()
            if not filename:
                continue

            # Data is CSV: mtime_size_hash, plugin_uid, Display Name
            # Note: The name might contain commas, so rejoin from parts[2:].
            parts = data.split(",")

            if len(parts) < 3:
                continue

            uid = parts[1].strip()
            name = ",".join(parts[2:]).strip().strip('"').strip()
            for suffix in ("!!!VST3i", "!!!VSTi"):
                if name.endswith(suffix):
                    name = name[: -len(suffix)].strip()

            if not uid or not name:
                continue

            # Detect Type based on extension (ignoring <...> sub-plugin suffixes)
            base_filename = filename.split("<", 1)[0].strip().lower()
            p_type = "VST"
            if base_filename.endswith(".vst3"):
                p_type = "VST3"
            elif base_filename.endswith(".clap"):
                p_type = "CLAP"

            plugins[name] = {"uid": uid, "filename": filename, "type": p_type}

    return plugins


def main():
    resource_path = get_reaper_resource_path()
    ini_path = find_vst_ini(resource_path)
    if not ini_path:
        print(
            f"[ERROR] Could not find any REAPER VST cache ini in {resource_path!r}"
        )
        return

    plugins = parse_reaper_ini(ini_path)

    if not plugins:
        print("No plugins found. Is the path correct?")
        return

    output_file = "reaper_plugin_map.json"

    # Save to JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(plugins, f, indent=4)

    print(f"\n[SUCCESS] Extracted {len(plugins)} plugins.")
    print(f"Map saved to: {os.path.abspath(output_file)}")
    print("Use this JSON to lookup 'uid' by Plugin Name in your RPP generator.")


if __name__ == "__main__":
    main()
