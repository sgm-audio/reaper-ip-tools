-- @description Generate REAPER Session Assets (RPP + EEL)
-- @author Scott Mills
-- @version 1.0.0
-- @about Builds a valid auto_session_v1.rpp and clean_slate_reset.eel into a generated_assets folder using a strict, balanced-node builder
-- @changelog Initial release
-- @link https://github.com/sgm-audio
-- @provides
--   [main] .

local CONFIG = {
    output_dir_name = "generated_assets",
    rpp_name = "auto_session_v1.rpp",
    eel_name = "clean_slate_reset.eel",
    track_names = { "Kick", "Snare", "Bass (DI)", "Gtr L", "Gtr R", "Synths" },
}

local SEP = package.config:sub(1, 1)

local ProjectBuilder = {}
ProjectBuilder.__index = ProjectBuilder

local function new_builder()
    return setmetatable({ lines = {}, indent = 0 }, ProjectBuilder)
end

function ProjectBuilder:add_line(content)
    self.lines[#self.lines + 1] = string.rep("  ", self.indent) .. content
end

function ProjectBuilder:start_node(tag, ...)
    local params = {}
    local n = select("#", ...)
    for i = 1, n do
        params[i] = tostring(select(i, ...))
    end
    local header = "<" .. tag
    if n > 0 then
        header = header .. " " .. table.concat(params, " ")
    end
    self:add_line(header)
    self.indent = self.indent + 1
end

function ProjectBuilder:end_node()
    if self.indent == 0 then
        error("Syntax Error: Attempted to close a node at root level.")
    end
    self.indent = self.indent - 1
    self:add_line(">")
end

function ProjectBuilder:add_property(key, value)
    if type(value) == "string" and value:find(" ", 1, true) and not value:find('^"') then
        value = '"' .. value .. '"'
    end
    self:add_line(key .. " " .. tostring(value))
end

function ProjectBuilder:add_raw(raw)
    self:add_line(raw)
end

function ProjectBuilder:build()
    if self.indent ~= 0 then
        error("Syntax Error: Unbalanced nodes. Open levels: " .. self.indent)
    end
    return table.concat(self.lines, "\n")
end

local function build_rpp_content()
    local rpp = new_builder()

    rpp:start_node("REAPER_PROJECT", "0.1", '"7.0"', os.time())

    rpp:add_property("SAMPLERATE", "48000 0 0")
    rpp:add_property("TEMPO", "120 4 4")

    rpp:start_node("TRACK")
    rpp:add_property("NAME", '"Master"')
    rpp:add_property("VOLPAN", "1.0 0.0 -1.0 -1.0 1.0")
    rpp:end_node()

    for _, name in ipairs(CONFIG.track_names) do
        rpp:start_node("TRACK")
        rpp:add_property("NAME", '"' .. name .. '"')
        rpp:add_property("PEAKCOL", 16576)
        rpp:add_property("BEAT", -1)
        rpp:add_property("VOLPAN", "1.0 0.0 -1.0 -1.0 1.0")

        rpp:start_node("FXCHAIN")
        rpp:add_property("SHOW", 0)
        rpp:add_property("LASTSEL", 0)
        rpp:add_property("DOCKED", 0)
        rpp:end_node()

        rpp:end_node()
    end

    rpp:end_node()

    return rpp:build()
end

local function build_eel_content()
    local eel = [[// @description Auto-Generated Hard Reset Utility
// @version 1.0
// @author Scott Mills (Automated)

function main()
(
    Undo_BeginBlock();
    count = CountTracks(0);
    i = 0;
    loop(count,
        tr = GetTrack(0, i);
        SetMediaTrackInfo_Value(tr, "D_VOL", 1.0); // Reset to 0dB (Linear gain 1.0)
        SetMediaTrackInfo_Value(tr, "D_PAN", 0.0); // Center pan
        i += 1;
    );
    Undo_EndBlock("Hard Reset All Tracks", -1);
);

main();
]]
    return eel
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

local function script_directory()
    local path = reaper.get_script_path()
    if not path or path == "" then
        return reaper.GetResourcePath()
    end
    -- get_script_path() may return the full path to the .lua file rather than
    -- its directory, so strip a trailing filename component if one is present.
    if path:match("%.[%w]+$") then
        local dir = path:match("^(.*)[/\\]")
        if dir and dir ~= "" then
            return dir
        end
    end
    return path
end

local function main()
    local script_dir = script_directory()
    if not script_dir or script_dir == "" then
        reaper.MB("Could not determine the script path.", "Session Assets", 0)
        return
    end

    local output_dir = script_dir .. SEP .. CONFIG.output_dir_name
    -- RecursiveCreateDirectory returns a positive value on success, 0 on failure
    local mkdir_result = reaper.RecursiveCreateDirectory(output_dir, 0)
    if not mkdir_result or mkdir_result <= 0 then
        reaper.MB("Could not create output directory:\n" .. output_dir, "Session Assets", 0)
        return
    end

    local rpp_path = output_dir .. SEP .. CONFIG.rpp_name
    local eel_path = output_dir .. SEP .. CONFIG.eel_name

    local rpp_ok, rpp_err = write_file(rpp_path, build_rpp_content() .. "\n")
    if not rpp_ok then
        reaper.MB("Failed to write RPP project:\n" .. rpp_path .. "\n" .. tostring(rpp_err), "Session Assets", 0)
        return
    end

    local eel_ok, eel_err = write_file(eel_path, build_eel_content())
    if not eel_ok then
        reaper.MB("Failed to write EEL script:\n" .. eel_path .. "\n" .. tostring(eel_err), "Session Assets", 0)
        return
    end

    reaper.MB("Generated session assets:\n" .. rpp_path .. "\n" .. eel_path, "Session Assets", 0)
end

main()
