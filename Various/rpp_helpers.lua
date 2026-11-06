-- rpp_helpers.lua — pure library for canonical REAPER .rpp chunk emission.
-- Formats verified against REAPER 7.x output (see src/reaper_assets/*.py).
-- No reaper.* calls, no side effects. dofile() to use.

local helpers = {}

-- ============================================================
-- Builder (strict, balanced-node)
-- ============================================================

local Builder = {}
Builder.__index = Builder

local function new_builder()
    return setmetatable({ lines = {}, indent = 0 }, Builder)
end
helpers.new_builder = new_builder

function Builder:add_line(content)
    self.lines[#self.lines + 1] = string.rep("  ", self.indent) .. content
end

function Builder:start_node(tag, ...)
    local parts = { tag }
    local n = select("#", ...)
    for i = 1, n do
        parts[#parts + 1] = tostring(select(i, ...))
    end
    self:add_line("<" .. table.concat(parts, " "))
    self.indent = self.indent + 1
end

function Builder:end_node()
    assert(self.indent > 0, "end_node() at root level")
    self.indent = self.indent - 1
    self:add_line(">")
end

function Builder:add_property(key, ...)
    local parts = { key }
    local n = select("#", ...)
    for i = 1, n do
        parts[#parts + 1] = tostring(select(i, ...))
    end
    self:add_line(table.concat(parts, " "))
end

function Builder:add_raw(raw)
    self:add_line(raw)
end

function Builder:build()
    assert(self.indent == 0, tostring(self.indent) .. " unclosed node(s)")
    return table.concat(self.lines, "\n") .. "\n"
end

-- ============================================================
-- Color packing: r | (g<<8) | (b<<16), plus the 0x1000000 flag.
-- ============================================================

local function color_to_native(r, g, b)
    return (r | (g << 8) | (b << 16)) | 0x1000000
end
helpers.color_to_native = color_to_native

-- ============================================================
-- Folder roles -> ISBUS argument pair (verified encoding).
--   parent       ISBUS 1 1
--   child        ISBUS 0 0
--   end (last)   ISBUS 2 -1
-- ============================================================

local FOLDER_PARENT = "parent"
local FOLDER_CHILD = "child"
local FOLDER_END = "end"

local function isbus_value(folder)
    if folder == FOLDER_PARENT then
        return 1, 1
    elseif folder == FOLDER_END then
        return 2, -1
    end
    return 0, 0
end
helpers.isbus_value = isbus_value
helpers.FOLDER_PARENT = FOLDER_PARENT
helpers.FOLDER_CHILD = FOLDER_CHILD
helpers.FOLDER_END = FOLDER_END

-- ============================================================
-- Sends: AUXRECV on the receiver, referencing the source track index.
--   AUXRECV <src_idx> 0 <mode> 0 0 0 0 0 0 -1:U <vol> -1 '<name>'
-- ============================================================

local function auxrecv_line(src_index, mode, volume, name)
    mode = mode or 0
    volume = volume or 0
    name = name or ""
    return string.format("AUXRECV %d 0 %d 0 0 0 0 0 0 -1:U %d -1 '%s'", src_index, mode, volume, name)
end
helpers.auxrecv_line = auxrecv_line

-- ============================================================
-- Markers / regions.
--   MARKER <idx> <pos> "<name>" <idnum> <color> 1 R {GUID} 0 2 [<region_end>]
-- ============================================================

local function guid()
    local hex = "0123456789ABCDEF"
    local function rand_hex(n)
        local out = {}
        for _ = 1, n do
            out[#out + 1] = hex:sub(math.random(1, 16), math.random(1, 16))
        end
        return table.concat(out)
    end
    return string.format("{%s-%s-%s-%s-%s}",
        rand_hex(8), rand_hex(4), rand_hex(4), rand_hex(4), rand_hex(12))
end

local function fmt_time(pos)
    local f = tonumber(pos)
    if f == math.floor(f) then
        return tostring(math.floor(f))
    end
    return tostring(f)
end

local function marker_line(idx, pos, name, color, idnum, region_end)
    color = color or 255
    idnum = idnum or 0
    local end_tok = ""
    if region_end ~= nil then
        end_tok = " " .. fmt_time(region_end)
    end
    return string.format('MARKER %d %s "%s" %d %d 1 R %s 0 2%s',
        idx, fmt_time(pos), name, idnum, color, guid(), end_tok)
end
helpers.marker_line = marker_line

-- ============================================================
-- Stock Cockos FX descriptors (verified state from installed templates).
-- ============================================================

local STOCK_PLUGINS = {
    ReaEQ = {
        display = "VST: ReaEQ (Cockos)",
        dll = "reaeq.dll",
        uid = 1919247729,
        hex = "56535472656571726561657100000000",
        state = {
            "cWVlcu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAAzQAAAAEAAAAAABAA",
            "IQAAAAUAAAAAAAAAAQAAAAAAAAAAAFlAAAAAAAAA8D+amZmZmZnpPwEIAAAAAQAAAAAAAAAAwHJAAAAAAAAA8D8AAAAAAAAAQAEIAAAAAQAAAAAAAAAAQI9AAAAAAAAA",
            "8D8AAAAAAAAAQAEBAAAAAQAAAAAAAAAAiLNAAAAAAAAA8D+amZmZmZnpPwEEAAAAAAAAAAAAAAAAAFlAAAAAAAAA8D8AAAAAAAAAQAEBAAAAAQAAAAAAAAAAAPA/AAAA",
            "AP0BAABcAQAAAgAAAA==",
            "AAAQAAAA",
        },
    },
    ReaComp = {
        display = "VST: ReaComp (Cockos)",
        dll = "reacomp.dll",
        uid = 1919247213,
        hex = "5653547265636D726561636F6D700000",
        state = {
            "bWNlcu9e7f4EAAAAAQAAAAAAAAACAAAAAAAAAAQAAAAAAAAACAAAAAAAAAACAAAAAQAAAAAAAAACAAAAAAAAAFwAAAAAAAAAAAAQAA==",
            "776t3g3wrd4AAJDBAABAQKabxDsK16M8AAAAAAAAAAAAAIA/AAAAAAAAAAAAAAAAnNEHMwAAgD8AAAAAzcxMPQAAAAAAAAAAAAAAAAAAgD4AAAAAAAAAAAAAAAA=",
            "AAAQAAAA",
        },
    },
    ReaGate = {
        display = "VST: ReaGate (Cockos)",
        dll = "reagate.dll",
        uid = 1919248244,
        hex = "56535472656774726561676174650000",
        state = {
            "dGdlcu9e7f4EAAAAAQAAAAAAAAACAAAAAAAAAAQAAAAAAAAACAAAAAAAAAACAAAAAQAAAAAAAAACAAAAAAAAAFwAAAAAAAAAAAAQAA==",
            "776t3g3wrd6c0QczppvEOwrXozwAAAAAAAAAAAAAgD8AAAAAAAAAAAAAAACc0QczAACAP5zRBzMAAIA/AAAAAAAAAAAAAAAALBYLPwAAAAAAAAAAAAAAAAAAAAA=",
            "AAAQAAAA",
        },
    },
    ReaLimit = {
        display = "VST: ReaLimit (Cockos)",
        dll = "realimit.dll",
        uid = 1919708532,
        hex = "565354726C6D747265616C696D697400",
        state = {
            "dG1scu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAAMAAAAAEAAAAAABAA",
            "AwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAD+fduMQw8Y/",
            "AFByb2dyYW0gMQAQAAAA",
        },
    },
}
helpers.STOCK_PLUGINS = STOCK_PLUGINS

local function write_vst_node(b, desc)
    b:start_node("VST",
        '"' .. desc.display .. '"',
        desc.dll, 0, '""', desc.uid .. "<" .. desc.hex .. ">", '""')
    for _, line in ipairs(desc.state) do
        b:add_raw(line)
    end
    b:end_node()
    b:add_property("FXID", "{" .. guid() .. "}")
    b:add_property("WAK", 0, 0)
end
helpers.write_vst_node = write_vst_node

local function write_fx_chain(b, names)
    for _, n in ipairs(names) do
        assert(STOCK_PLUGINS[n], "No stock FX descriptor for " .. tostring(n))
    end
    b:start_node("FXCHAIN")
    b:add_property("SHOW", 0)
    b:add_property("LASTSEL", 0)
    b:add_property("DOCKED", 0)
    for _, n in ipairs(names) do
        b:add_property("BYPASS", 0, 0, 0)
        write_vst_node(b, STOCK_PLUGINS[n])
    end
    b:end_node()
end
helpers.write_fx_chain = write_fx_chain

-- ============================================================
-- Track emission (canonical REAPER 7.x <TRACK {GUID}> node).
-- ============================================================

local function write_track(b, name, color, folder, receives, fx, mainsends)
    mainsends = (mainsends == nil) and 1 or mainsends
    local g = guid()

    b:start_node("TRACK", "{" .. g .. "}")
    b:add_property("NAME", '"' .. name .. '"')
    b:add_property("PEAKCOL", color and color_to_native(color[1], color[2], color[3]) or 16576)
    b:add_property("BEAT", -1)
    b:add_property("AUTOMODE", 0)
    b:add_property("PANLAWFLAGS", 3)
    b:add_property("VOLPAN", 1, 0, -1, -1, 1)
    b:add_property("MUTESOLO", 0, 0, 0)
    b:add_property("IPHASE", 0)
    b:add_property("PLAYOFFS", 0, 1)
    b:add_property("ISBUS", isbus_value(folder))
    b:add_property("BUSCOMP", 0, 0, 0, 0, 0)
    b:add_property("SHOWINMIX", 1, 0.6667, 0.5, 1, 0.5, 0, 0, 0, 0)
    b:add_property("FIXEDLANES", 9, 0, 0, 0, 0)
    b:add_property("SEL", 0)
    b:add_property("REC", 0, 0, 1, 0, 0, 0, 0, 0)
    b:add_property("VU", 2)
    b:add_property("TRACKHEIGHT", 0, 0, 0, 0, 0, 0, 0)
    b:add_property("INQ", 0, 0, 0, 0.5, 100, 0, 0, 100)
    b:add_property("NCHAN", 2)
    b:add_property("FX", fx and #fx or 0)
    b:add_property("TRACKID", "{" .. g .. "}")
    b:add_property("PERF", 0)
    if receives then
        for _, line in ipairs(receives) do
            b:add_raw(line)
        end
    end
    b:add_property("MIDIOUT", -1)
    b:add_property("MAINSEND", mainsends, 0)
    if fx and #fx > 0 then
        write_fx_chain(b, fx)
    else
        b:start_node("FXCHAIN")
        b:add_property("SHOW", 0)
        b:add_property("LASTSEL", 0)
        b:add_property("DOCKED", 0)
        b:end_node()
    end
    b:end_node() -- TRACK
end
helpers.write_track = write_track

local function write_master(b)
    b:add_property("MASTERAUTOMODE", 0)
    b:add_property("MASTERTRACKHEIGHT", 0, 0)
    b:add_property("MASTERPEAKCOL", 16576)
    b:add_property("MASTERMUTESOLO", 0)
    b:add_property("MASTERHWOUT", 0, 0, 1, 0, 0, 0, 0, -1)
    b:add_property("MASTER_NCH", 2, 2)
    b:add_property("MASTER_VOLUME", 1, 0, -1, -1, 1)
    b:add_property("MASTER_FX", 1)
    b:add_property("MASTER_SEL", 0)
end
helpers.write_master = write_master

return helpers
