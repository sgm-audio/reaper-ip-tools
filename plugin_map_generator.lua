-- @description Generate Plugin Map Lua Module
-- @author Scott Mills
-- @version 1.0.0
-- @about Reads reaper-vstplugins64.ini and reaper-clap-win64.ini from the REAPER resource path and writes plugin_map.lua (name -> {uid, filename, type}) for dofile() consumption by other ReaScripts
-- @changelog Initial release
-- @link https://github.com/sgm-audio
-- @provides
--   [main] .

local CONFIG = {
    output_name = "plugin_map.lua",
    verbose = true,
}

local SEP = package.config:sub(1, 1)

local function trim(s)
    return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function detect_type(filename)
    local lower = filename:lower()
    if lower:find("%.vst3$") then
        return "VST3"
    elseif lower:find("%.clap$") then
        return "CLAP"
    end
    return "VST"
end

local function lua_quote(s)
    s = s:gsub("\\", "\\\\")
    s = s:gsub('"', '\\"')
    return '"' .. s .. '"'
end

local function parse_vst_ini(ini_path, plugins)
    local f, err = io.open(ini_path, "r")
    if not f then
        if CONFIG.verbose then
            reaper.ShowConsoleMsg("Could not open " .. ini_path .. ": " .. tostring(err) .. "\n")
        end
        return
    end
    for line in f:lines() do
        line = line:gsub("[\r\n]+$", "")
        local trimmed = trim(line)
        if trimmed ~= "" and not trimmed:match("^%[") then
            local filename, data = line:match("^([^=]+)=(.*)$")
            if filename and data then
                local uid = data:match("^([^,]+)")
                local name = data:match("^[^,]+,[^,]+,(.*)$")
                if uid and name then
                    plugins[trim(name)] = {
                        uid = trim(uid),
                        filename = trim(filename),
                        type = detect_type(filename),
                    }
                end
            end
        end
    end
    f:close()
end

local function parse_clap_ini(ini_path, plugins)
    local f, err = io.open(ini_path, "r")
    if not f then
        if CONFIG.verbose then
            reaper.ShowConsoleMsg("Could not open " .. ini_path .. ": " .. tostring(err) .. "\n")
        end
        return
    end
    local section, section_uid = nil, nil
    for line in f:lines() do
        line = line:gsub("[\r\n]+$", "")
        local trimmed = trim(line)
        if trimmed ~= "" then
            local sec = trimmed:match("^%[([^%]]+)%]$")
            if sec then
                section = sec
                section_uid = nil
            elseif section then
                local key, value = line:match("^([^=]+)=(.*)$")
                if key then
                    key, value = trim(key), trim(value)
                    if key == "_" then
                        section_uid = value
                    elseif value:match("^0|") then
                        local name = value:match("^0|(.*)$")
                        if name and not plugins[name] then
                            plugins[name] = {
                                uid = section_uid or "",
                                filename = section,
                                type = "CLAP",
                            }
                        end
                    end
                end
            end
        end
    end
    f:close()
end

local function write_module(plugins, out_path)
    local names = {}
    for name in pairs(plugins) do
        names[#names + 1] = name
    end
    table.sort(names)

    local parts = { "return {" }
    for _, name in ipairs(names) do
        local p = plugins[name]
        parts[#parts + 1] = string.format(
            "    [%s] = { uid = %s, filename = %s, type = %s },",
            lua_quote(name), lua_quote(p.uid), lua_quote(p.filename), lua_quote(p.type))
    end
    parts[#parts + 1] = "}"

    local f, err = io.open(out_path, "w")
    if not f then
        reaper.MB("Could not write " .. out_path .. "\n" .. tostring(err), "Plugin Map", 0)
        return false
    end
    f:write(table.concat(parts, "\n") .. "\n")
    f:close()
    return true, #names
end

local function main()
    local resource = reaper.GetResourcePath()
    if not resource or resource == "" then
        reaper.MB("Could not determine the REAPER resource path.", "Plugin Map", 0)
        return
    end

    local plugins = {}
    parse_vst_ini(resource .. SEP .. "reaper-vstplugins64.ini", plugins)
    parse_clap_ini(resource .. SEP .. "reaper-clap-win64.ini", plugins)

    if next(plugins) == nil then
        reaper.MB("No plugins found. Is the REAPER resource path correct?", "Plugin Map", 0)
        return
    end

    local out_path = resource .. SEP .. CONFIG.output_name
    local ok, count = write_module(plugins, out_path)
    if ok then
        reaper.MB("Wrote plugin map (" .. count .. " plugins) to:\n" .. out_path, "Plugin Map", 0)
    end
end

main()
