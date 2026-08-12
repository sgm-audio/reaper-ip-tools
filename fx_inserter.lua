-- @description Insert FX by Name from Plugin Map
-- @author Scott Mills
-- @version 1.0.0
-- @about Prompts for a plugin name (from plugin_map.lua) and inserts it onto all selected tracks. Run plugin_map_generator.lua first to build the map.
-- @changelog Initial release
-- @link https://github.com/sgm-audio
-- @provides
--   [main] .

local SEP = package.config:sub(1, 1)

local function find_plugin(map, query)
    if not query or query == "" then
        return nil
    end
    if map[query] then
        return query, map[query]
    end
    local lower = query:lower()
    for name, info in pairs(map) do
        if name:lower():find(lower, 1, true) then
            return name, info
        end
    end
    return nil
end

local function sample_names(map)
    local names = {}
    for name in pairs(map) do
        names[#names + 1] = name
    end
    table.sort(names)
    local shown = {}
    for i = 1, math.min(#names, 8) do
        shown[#shown + 1] = names[i]
    end
    return table.concat(shown, "\n")
end

local function main()
    local resource = reaper.GetResourcePath()
    local map_path = resource .. SEP .. "plugin_map.lua"

    local f = io.open(map_path, "r")
    if not f then
        reaper.MB("Plugin map not found at:\n" .. map_path .. "\n\nRun plugin_map_generator.lua first.", "Insert FX", 0)
        return
    end
    f:close()

    local ok_map, plugin_map = pcall(dofile, map_path)
    if not ok_map or type(plugin_map) ~= "table" then
        reaper.MB("Failed to load plugin map:\n" .. tostring(plugin_map), "Insert FX", 0)
        return
    end

    local sel_count = reaper.CountSelectedTracks(0)
    if sel_count == 0 then
        reaper.MB("Select at least one track.", "Insert FX", 0)
        return
    end

    local retval_csv = ""
    local ok_input, input_csv = reaper.GetUserInputs("Insert FX by name", 1, "Plugin name", retval_csv, 0)
    if not ok_input then
        return
    end
    local query = (input_csv or ""):match("^%s*(.-)%s*$")
    if query == "" then
        return
    end

    local matched_name, info = find_plugin(plugin_map, query)
    if not matched_name then
        reaper.MB("No plugin matching \"" .. query .. "\".\n\nAvailable plugins (sample):\n" .. sample_names(plugin_map), "Insert FX", 0)
        return
    end

    local tracks = {}
    for i = 0, sel_count - 1 do
        tracks[#tracks + 1] = reaper.GetSelectedTrack(0, i)
    end

    reaper.Undo_BeginBlock()
    reaper.PreventUIRefresh(1)

    local added = 0
    for _, tr in ipairs(tracks) do
        local idx = reaper.TrackFX_AddByName(tr, matched_name, false, -1)
        if idx and idx >= 0 then
            added = added + 1
        end
    end

    reaper.PreventUIRefresh(-1)
    reaper.Undo_EndBlock("Insert FX: " .. matched_name, -1)

    if added == 0 then
        reaper.MB("Could not add \"" .. matched_name .. "\" (no tracks accepted the FX).\nType: " .. info.type .. ", file: " .. info.filename, "Insert FX", 0)
    else
        reaper.MB("Added " .. matched_name .. " to " .. added .. " track(s).", "Insert FX", 0)
    end
end

main()
