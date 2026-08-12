import json
import os
import platform


def get_reaper_resource_path():
    """
    Attempts to auto-detect the REAPER resource path on Windows/Mac.
    """
    system = platform.system()
    if system == "Windows":
        # Standard portable or installed path
        path = os.path.join(os.environ["APPDATA"], "REAPER")
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
    return input("Enter full path to REAPER resource folder: ").strip()


def parse_reaper_ini(ini_path):
    """
    Parses reaper-vstplugins64.ini.
    Format is roughly: filename=UID,ProjectID,Name
    """
    plugins = {}

    if not os.path.exists(ini_path):
        print(f"[ERROR] Could not find {ini_path}")
        return {}

    print(f"Scanning: {ini_path}...")

    with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("["):
                continue

            # Split only on the first equals sign to separate Filename from Data
            if "=" not in line:
                continue

            filename, data = line.split("=", 1)

            # Data is CSV: UID, UnknownInt, "Name (Developer)"
            # Note: The name might contain commas, so we be careful.
            parts = data.split(",")

            if len(parts) < 3:
                continue

            # VST3 UIDs are usually long hex strings. VST2 are shorter checksums.
            uid = parts[0]
            # The name is the last part(s). Re-join just in case name has commas.
            name = ",".join(parts[2:])

            # Clean up the name (remove quotes if present)
            name = name.strip()

            # Detect Type based on extension
            p_type = "VST"
            if filename.lower().endswith(".vst3"):
                p_type = "VST3"
            elif filename.lower().endswith(".clap"):
                p_type = "CLAP"

            # Store in dictionary: Key = Name (e.g., "Archetype Gojira (Neural DSP)")
            # Value = {UID, Filename, Type}
            plugins[name] = {"uid": uid, "filename": filename, "type": p_type}

    return plugins


def main():
    resource_path = get_reaper_resource_path()
    ini_path = os.path.join(resource_path, "reaper-vstplugins64.ini")

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
