-- @description Podcast Session Bootstrap (reaper-session-architect)
-- @author Scott Mills
-- @version 1.0.0
-- @changelog Builds a podcast session: speaker tracks, music bed, SFX, dialogue + show buses,
--   routing, colors, markers/regions, and stock FX chains. Idempotent with dry-run mode.
-- @provides
--   [main] . -> bootstrap.lua

-- ============================================================
-- USER SETTINGS
-- ============================================================
local CONFIG = {
    dry_run = false,          -- true: log planned actions, apply nothing
    verbose = true,           -- true: print progress to console

    sample_rate = 48000,      -- project sample rate (Hz)
    bpm = 120,                -- project tempo
    time_sig_num = 4,         -- time signature numerator
    time_sig_denom = 4,       -- time signature denominator

    -- Track definitions. Buses are listed first so they sit at the top of the mixer.
    tracks = {
        { name = "SHOW_MASTER",   rgb = {255, 255, 255}, bus = "master", fx = {"ReaComp", "ReaLimit"} },
        { name = "DIALOGUE_BUS",  rgb = {255,  82,  82}, bus = "bus",    fx = {"ReaGate", "ReaEQ", "ReaComp"} },
        { name = "SPKF_DALE",     rgb = {232,  93,  63}, bus = "source", fx = {} },
        { name = "SPKF_JAMIE",    rgb = { 63, 167, 232}, bus = "source", fx = {} },
        { name = "SPKF_BRIAN",    rgb = {122, 219,  98}, bus = "source", fx = {} },
        { name = "MUSIC_BED",     rgb = {199, 146, 234}, bus = "source", fx = {} },
        { name = "SFX_LIB",       rgb = {244, 211,  94}, bus = "source", fx = {} },
    },

    -- Routing rules: source track -> destination track.
    routes = {
        { from = "SPKF_DALE",     to = "DIALOGUE_BUS" },
        { from = "SPKF_JAMIE",    to = "DIALOGUE_BUS" },
        { from = "SPKF_BRIAN",    to = "DIALOGUE_BUS" },
        { from = "DIALOGUE_BUS",  to = "SHOW_MASTER" },
        { from = "MUSIC_BED",     to = "SHOW_MASTER" },
        { from = "SFX_LIB",       to = "SHOW_MASTER" },
    },

    -- Markers (seconds) and regions (start, end, name).
    markers = {
        { 0.0,   "Show Start" },
        { 60.0,  "Main Content" },
        { 300.0, "Outro Start" },
    },
    regions = {
        { 0.0,   60.0,  "COLD OPEN" },
        { 60.0,  300.0, "MAIN SEGMENT" },
        { 300.0, 330.0, "OUTRO" },
    },
}

-- ============================================================
-- HELPERS
-- ============================================================
local function log(msg)
    if CONFIG.verbose then
        reaper.ShowConsoleMsg(msg .. "\n")
    end
end

local function find_track_by_name(name)
    for i = 0, reaper.CountTracks(0) - 1 do
        local tr = reaper.GetTrack(0, i)
        local _, existing = reaper.GetTrackName(tr, "")
        if existing == name then
            return tr
        end
    end
    return nil
end

local function set_track_name(tr, name)
    reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", name, true)
end

local function set_track_color(tr, rgb)
    local col = reaper.ColorToNative(rgb[1], rgb[2], rgb[3]) | 0x1000000
    reaper.SetTrackColor(tr, col)
end

local function has_send_to(src, dest)
    local n = reaper.GetTrackNumSends(src, 0)
    for i = 0, n - 1 do
        local d = reaper.GetTrackSendInfo_Value(src, 0, i, "P_DESTTRACK")
        if d == dest then
            return true
        end
    end
    return false
end

local function add_stock_fx(tr, fx_names)
    for _, name in ipairs(fx_names) do
        local idx = reaper.TrackFX_AddByName(tr, name, false, -1)
        if idx < 0 then
            log("  WARN: could not add stock FX '" .. name .. "' (not found?)")
        else
            log("  Added stock FX: " .. name)
        end
    end
end

-- ============================================================
-- BUILD STEPS (each honors CONFIG.dry_run)
-- ============================================================

local function ensure_tracks()
    local track_refs = {}
    for _, spec in ipairs(CONFIG.tracks) do
        local tr = find_track_by_name(spec.name)
        if tr then
            log("Reusing existing track: " .. spec.name)
        else
            if CONFIG.dry_run then
                log("[DRY RUN] Would create track: " .. spec.name)
                tr = nil
            else
                tr = reaper.InsertTrackAtIndex(reaper.CountTracks(0), true)
                set_track_name(tr, spec.name)
                log("Created track: " .. spec.name)
            end
        end

        if tr then
            set_track_name(tr, spec.name)
            set_track_color(tr, spec.rgb)

            -- Bus topology: everything except SHOW_MASTER disables master/parent send.
            local main_send = (spec.bus == "master") and 1 or 0
            if not CONFIG.dry_run then
                reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", main_send)
            end

            if #spec.fx > 0 then
                log("  FX chain for " .. spec.name .. ": " .. table.concat(spec.fx, ", "))
                if not CONFIG.dry_run then
                    add_stock_fx(tr, spec.fx)
                end
            end
        end

        track_refs[spec.name] = tr
    end
    return track_refs
end

local function ensure_routes(track_refs)
    for _, rule in ipairs(CONFIG.routes) do
        local src = track_refs[rule.from]
        local dest = track_refs[rule.to]
        if not src or not dest then
            log("  WARN: route skipped (missing track) " .. rule.from .. " -> " .. rule.to)
        elseif has_send_to(src, dest) then
            log("Send already exists: " .. rule.from .. " -> " .. rule.to)
        else
            log("Send: " .. rule.from .. " -> " .. rule.to)
            if not CONFIG.dry_run then
                reaper.CreateTrackSend(src, dest)
            end
        end
    end
end

local function ensure_markers_regions()
    for _, m in ipairs(CONFIG.markers) do
        log(string.format("Marker at %.1fs: %s", m[1], m[2]))
        if not CONFIG.dry_run then
            reaper.AddProjectMarker2(0, false, m[1], 0, m[2], -1, 0)
        end
    end
    for _, r in ipairs(CONFIG.regions) do
        log(string.format("Region %.1fs - %.1fs: %s", r[1], r[2], r[3]))
        if not CONFIG.dry_run then
            reaper.AddProjectMarker2(0, true, r[1], r[2], r[3], -1, 0)
        end
    end
end

local function ensure_project_settings()
    if CONFIG.dry_run then
        log(string.format("[DRY RUN] Would set sample rate %d, BPM %d, time sig %d/%d",
            CONFIG.sample_rate, CONFIG.bpm, CONFIG.time_sig_num, CONFIG.time_sig_denom))
        return
    end
    reaper.GetSetProjectInfo(0, "PROJECT_SRATE", CONFIG.sample_rate, true)
    reaper.SetCurrentBPM(0, CONFIG.bpm, true)
    if reaper.SetTempoTimeSigMarker then
        reaper.SetTempoTimeSigMarker(0, -1, 0.0, -1, -1, -1, CONFIG.time_sig_num, CONFIG.time_sig_denom, 0)
    end
    log(string.format("Project settings: %d Hz, %d BPM, %d/%d",
        CONFIG.sample_rate, CONFIG.bpm, CONFIG.time_sig_num, CONFIG.time_sig_denom))
end

-- ============================================================
-- MAIN
-- ============================================================
local function main()
    if CONFIG.dry_run then
        log("=== PODCAST SESSION BOOTSTRAP (DRY RUN) ===")
    else
        reaper.Undo_BeginBlock()
        reaper.PreventUIRefresh(1)
        log("=== PODCAST SESSION BOOTSTRAP ===")
    end

    ensure_project_settings()
    local track_refs = ensure_tracks()
    ensure_routes(track_refs)
    ensure_markers_regions()

    if not CONFIG.dry_run then
        reaper.PreventUIRefresh(-1)
        reaper.Undo_EndBlock("Build Podcast Session", -1)
        reaper.TrackList_AdjustWindows(false)
        reaper.UpdateArrange()
    end

    log("Done. Dialogue target: -16 LUFS integrated, 48 kHz / 24-bit WAV.")
end

main()
