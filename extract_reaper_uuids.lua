-- @description Extract REAPER Plugin UUID Map to JSON
-- @author Scott Mills
-- @version 1.0.0
-- @about Reads reaper-vstplugins64.ini and reaper-clap-win64.ini from the REAPER resource path and writes a JSON map of plugin name -> {uid, filename, type}
-- @changelog Initial release
-- @link https://github.com/sgm-audio
-- @provides
--   [main] .

local CONFIG = {
    output_name = "reaper_plugin_map.json",
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

local function json_escape(s)
    s = s:gsub("\\", "\\\\")
    s = s:gsub('"', '\\"')
    s = s:gsub("\n", "\\n")
    s = s:gsub("\r", "\\r")
    s = s:gsub("\t", "\\t")
    s = s:gsub("\b", "\\b")
    s = s:gsub("\f", "\\f")
    -- Escape any remaining control characters (< 0x20) as \u00XX
    s = s:gsub("[\1-\31]", function(c) return string.format("\\u%04x", c:byte()) end)
    return s
end

local function json_encode(value, indent)
    indent = indent or 0
    local pad = string.rep("  ", indent)
    local child_pad = string.rep("  ", indent + 1)
    local t = type(value)
    if t == "string" then
        return '"' .. json_escape(value) .. '"'
    elseif t == "number" then
        if value ~= value then
            return "null"
        end
        return tostring(value)
    elseif t == "boolean" then
        return tostring(value)
    elseif t == "table" then
        if #value > 0 then
            local parts = {}
            for i = 1, #value do
                parts[i] = child_pad .. json_encode(value[i], indent + 1)
            end
            return "[\n" .. table.concat(parts, ",\n") .. "\n" .. pad .. "]"
        end
        local parts, n = {}, 0
        for k, v in pairs(value) do
            n = n + 1
            parts[n] = child_pad .. '"' .. json_escape(tostring(k)) .. '": ' .. json_encode(v, indent + 1)
        end
        if n == 0 then
            return "{}"
        end
        return "{\n" .. table.concat(parts, ",\n") .. "\n" .. pad .. "}"
    end
    return "null"
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

local function write_map(plugins, out_path)
    local names = {}
    for name in pairs(plugins) do
        names[#names + 1] = name
    end
    table.sort(names)

    local parts = {}
    for i, name in ipairs(names) do
        local p = plugins[name]
        parts[i] = '  "' .. json_escape(name) .. '": {\n'
            .. '    "uid": ' .. json_encode(p.uid) .. ',\n'
            .. '    "filename": ' .. json_encode(p.filename) .. ',\n'
            .. '    "type": ' .. json_encode(p.type) .. "\n  }"
    end
    local json = "{\n" .. table.concat(parts, ",\n") .. "\n}\n"

    local f, err = io.open(out_path, "w")
    if not f then
        reaper.MB("Could not write " .. out_path .. "\n" .. tostring(err), "Plugin Map", 0)
        return false
    end
    f:write(json)
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
    local ok, count = write_map(plugins, out_path)
    if ok then
        reaper.MB("Extracted " .. count .. " plugins.\nMap saved to:\n" .. out_path, "Plugin Map", 0)
    end
end

main()
