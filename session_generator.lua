-- @description Generate Full Session Template (RPP)
-- @author Scott Mills
-- @version 1.0.0
-- @about Builds a session RPP with a drum folder, instrument children, a reverb bus, sends, track colors and markers, using verified REAPER 7.x chunk formats
-- @changelog Initial release
-- @link https://github.com/sgm-audio
-- @provides
--   [main] .

local CONFIG = {
    output_dir_name = "generated_assets",
    rpp_name = "auto_session_v2.rpp",
    note_name = "APPLY_FX_HERE.md",
}

local SEP = package.config:sub(1, 1)

local function script_directory()
    local path = reaper.get_script_path()
    if not path or path == "" then
        return reaper.GetResourcePath()
    end
    if path:match("%.[%w]+$") then
        local dir = path:match("^(.*)[/\\]")
        if dir and dir ~= "" then
            return dir
        end
    end
    return path
end

local function load_helpers()
    local dir = script_directory()
    local path = dir .. SEP .. "rpp_helpers.lua"
    local ok, H = pcall(dofile, path)
    if not ok or type(H) ~= "table" then
        reaper.MB("Failed to load rpp_helpers.lua:\n" .. tostring(H), "Session Template", 0)
        return nil
    end
    return H
end

local function build_rpp(H)
    local b = H.new_builder()

    b:start_node("REAPER_PROJECT", "0.1", '"7.0"', os.time())
    H.write_master(b)

    b:add_property("SAMPLERATE", 48000, 0, 0)
    b:add_property("TEMPO", 120, 4, 4)

    -- Tracks are emitted in mixer order. For sends, AUXRECV references the
    -- *source* track by 0-based index in this ordering.
    -- Order: [0] Drums(folder) [1] Kick [2] Snare [3] Overhead L
    --        [4] Overhead R [5] Bass [6] Gtr L [7] Gtr R
    --        [8] Synths [9] Reverb Bus

    local RED = { 255, 82, 82 }
    local RUST = { 232, 93, 63 }
    local ORANGE = { 255, 136, 0 }
    local YELLOW = { 244, 211, 94 }
    local BLUE = { 63, 167, 232 }
    local GREEN = { 122, 219, 98 }
    local PURPLE = { 199, 146, 234 }
    local WHITE = { 255, 255, 255 }

    -- Drums folder + children. Last child (Overhead R) closes the folder.
    H.write_track(b, "DRUM BUS", RUST, H.FOLDER_PARENT, nil, nil, 0)
    H.write_track(b, "Kick", RED, H.FOLDER_CHILD)
    -- Snare sends to Reverb Bus (index 9) as well as its folder parent.
    H.write_track(b, "Snare", ORANGE, H.FOLDER_CHILD, { H.auxrecv_line(9, 0, 0, "Snare->Reverb") })
    H.write_track(b, "Overhead L", YELLOW, H.FOLDER_CHILD)
    H.write_track(b, "Overhead R", YELLOW, H.FOLDER_END)

    H.write_track(b, "Bass (DI)", BLUE)
    H.write_track(b, "Gtr L", GREEN)
    H.write_track(b, "Gtr R", GREEN)
    H.write_track(b, "Synths", PURPLE)

    H.write_track(b, "Reverb Bus", WHITE, nil, nil, nil, 0)

    -- Markers: Intro, Verse, Chorus, Outro.
    b:add_raw(H.marker_line(1, 0.0, "Intro", 255, 0))
    b:add_raw(H.marker_line(2, 8.0, "Verse", 255, 0))
    b:add_raw(H.marker_line(3, 16.0, "Chorus", 255, 0))
    b:add_raw(H.marker_line(4, 24.0, "Outro", 255, 0))

    b:end_node() -- REAPER_PROJECT

    return b:build()
end

local function write_file(path, content)
    local f, err = io.open(path, "w")
    if not f then
        return nil, err
    end
    f:write(content)
    f:close()
    return true
end

local function main()
    local H = load_helpers()
    if not H then
        return
    end

    local dir = script_directory()
    local output_dir = dir .. SEP .. CONFIG.output_dir_name
    -- RecursiveCreateDirectory returns positive on success, 0 on failure.
    local mkdir_result = reaper.RecursiveCreateDirectory(output_dir, 0)
    if not mkdir_result or mkdir_result <= 0 then
        reaper.MB("Could not create output directory:\n" .. output_dir, "Session Template", 0)
        return
    end

    local rpp_path = output_dir .. SEP .. CONFIG.rpp_name
    local note_path = output_dir .. SEP .. CONFIG.note_name

    local ok, err = write_file(rpp_path, build_rpp(H))
    if not ok then
        reaper.MB("Failed to write RPP:\n" .. rpp_path .. "\n" .. tostring(err), "Session Template", 0)
        return
    end

    local note = [[# Session Template — Applying FX

This RPP is generated with routing, folders, colors and markers only.
FX are applied at runtime (no fabricated binary presets) — run:

  * fx_inserter.lua  (inserts a named plugin from plugin_map.lua onto selected tracks)
  * or add stock Cockos FX via the track FX chain UI.

To use stock chains programmatically, see src/reaper_assets/fx.py
(verified ReaEQ / ReaComp / ReaGate / ReaLimit descriptors).
]]
    local nok, nerr = write_file(note_path, note)
    if not nok then
        reaper.MB("Failed to write note:\n" .. note_path .. "\n" .. tostring(nerr), "Session Template", 0)
        return
    end

    reaper.MB("Generated session template:\n" .. rpp_path .. "\n" .. note_path, "Session Template", 0)
end

main()
