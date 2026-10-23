import gc
import gzip
import os
import re
import struct
import zlib

TILE_SIZE = 512
EMPTY_HEIGHT = -32768
BG = (15, 18, 24, 255)

LONG = struct.Struct(">Q")
I32 = struct.Struct(">i")
U32 = struct.Struct(">I")
U16 = struct.Struct(">H")

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


class NbtReader:
    __slots__ = ("buf", "pos")

    def __init__(self, buf):
        self.buf = buf
        self.pos = 0

    def u8(self):
        v = self.buf[self.pos]
        self.pos += 1
        return v

    def i8(self):
        v = struct.unpack_from(">b", self.buf, self.pos)[0]
        self.pos += 1
        return v

    def i16(self):
        v = struct.unpack_from(">h", self.buf, self.pos)[0]
        self.pos += 2
        return v

    def i32(self):
        v = I32.unpack_from(self.buf, self.pos)[0]
        self.pos += 4
        return v

    def u16(self):
        v = U16.unpack_from(self.buf, self.pos)[0]
        self.pos += 2
        return v

    def f32(self):
        v = struct.unpack_from(">f", self.buf, self.pos)[0]
        self.pos += 4
        return v

    def f64(self):
        v = struct.unpack_from(">d", self.buf, self.pos)[0]
        self.pos += 8
        return v

    def string(self):
        n = self.u16()
        v = self.buf[self.pos:self.pos + n].decode("utf-8", "replace")
        self.pos += n
        return v

    def long_array(self):
        n = self.i32()
        view = LongArray(self.buf, self.pos, n)
        self.pos += n * 8
        return view

    def skip(self, t):
        if t == TAG_END:
            return
        if t == TAG_BYTE:
            self.pos += 1
        elif t == TAG_SHORT:
            self.pos += 2
        elif t in (TAG_INT, TAG_FLOAT):
            self.pos += 4
        elif t in (TAG_LONG, TAG_DOUBLE):
            self.pos += 8
        elif t == TAG_BYTE_ARRAY:
            n = self.i32()
            self.pos += n
        elif t == TAG_STRING:
            n = self.u16()
            self.pos += n
        elif t == TAG_LIST:
            elem = self.u8()
            n = self.i32()
            for _ in range(n):
                self.skip(elem)
        elif t == TAG_COMPOUND:
            while True:
                tt = self.u8()
                if tt == TAG_END:
                    break
                n = self.u16()
                self.pos += n
                self.skip(tt)
        elif t == TAG_INT_ARRAY:
            n = self.i32()
            self.pos += n * 4
        elif t == TAG_LONG_ARRAY:
            n = self.i32()
            self.pos += n * 8
        else:
            raise ValueError(f"未知 NBT 类型 {t}")

    def value(self, t):
        if t == TAG_END:
            return None
        if t == TAG_BYTE:
            return self.i8()
        if t == TAG_SHORT:
            return self.i16()
        if t == TAG_INT:
            return self.i32()
        if t == TAG_LONG:
            v = LONG.unpack_from(self.buf, self.pos)[0]
            self.pos += 8
            return v
        if t == TAG_FLOAT:
            return self.f32()
        if t == TAG_DOUBLE:
            return self.f64()
        if t == TAG_BYTE_ARRAY:
            n = self.i32()
            v = self.buf[self.pos:self.pos + n]
            self.pos += n
            return v
        if t == TAG_STRING:
            return self.string()
        if t == TAG_LIST:
            elem = self.u8()
            n = self.i32()
            return [self.value(elem) for _ in range(n)]
        if t == TAG_COMPOUND:
            obj = {}
            while True:
                tt = self.u8()
                if tt == TAG_END:
                    return obj
                key = self.string()
                obj[key] = self.value(tt)
        if t == TAG_INT_ARRAY:
            n = self.i32()
            v = list(struct.unpack_from(f">{n}i", self.buf, self.pos))
            self.pos += n * 4
            return v
        if t == TAG_LONG_ARRAY:
            return self.long_array()
        raise ValueError(f"未知 NBT 类型 {t}")


class LongArray:
    __slots__ = ("buf", "off", "length")

    def __init__(self, buf, off, length):
        self.buf = buf
        self.off = off
        self.length = length

    def get(self, i):
        if i < 0 or i >= self.length:
            return 0
        return LONG.unpack_from(self.buf, self.off + i * 8)[0]


def read_nbt_root(buf):
    r = NbtReader(buf)
    if r.u8() != TAG_COMPOUND:
        raise ValueError("NBT 根标签不是 Compound")
    r.string()
    return r.value(TAG_COMPOUND)


def read_gzip_nbt(buf):
    if buf[:2] == b"\x1f\x8b":
        buf = gzip.decompress(buf)
    return read_nbt_root(buf)


def read_heightmaps(r):
    out = {}
    while True:
        t = r.u8()
        if t == TAG_END:
            return out
        key = r.string()
        if t == TAG_LONG_ARRAY:
            out[key] = r.long_array()
        else:
            r.skip(t)


def read_palette(r):
    elem = r.u8()
    n = r.i32()
    names = []
    if elem == TAG_STRING:
        for _ in range(n):
            names.append(base_name(r.string()))
        return names
    if elem == TAG_COMPOUND:
        for _ in range(n):
            name = None
            while True:
                t = r.u8()
                if t == TAG_END:
                    break
                key = r.string()
                if t == TAG_STRING:
                    v = r.string()
                    if key in ("Name", "id"):
                        name = v
                    elif name is None and ":" in v:
                        name = v
                else:
                    r.skip(t)
            names.append(base_name(name or "minecraft:air"))
        return names
    for _ in range(n):
        r.skip(elem)
    return ["minecraft:air"] * n


def read_block_states(r):
    palette = None
    data = None
    while True:
        t = r.u8()
        if t == TAG_END:
            return palette, data
        key = r.string()
        if key == "palette" and t == TAG_LIST:
            palette = read_palette(r)
        elif key == "data" and t == TAG_LONG_ARRAY:
            data = r.long_array()
        else:
            r.skip(t)


def read_sections(r):
    elem = r.u8()
    n = r.i32()
    sections = []
    if elem != TAG_COMPOUND:
        for _ in range(n):
            r.skip(elem)
        return sections
    for _ in range(n):
        y = 0
        palette = None
        data = None
        while True:
            t = r.u8()
            if t == TAG_END:
                break
            key = r.string()
            if key == "Y" and t == TAG_BYTE:
                y = r.i8()
            elif key == "block_states" and t == TAG_COMPOUND:
                palette, data = read_block_states(r)
            else:
                r.skip(t)
        sections.append((y, palette, data))
    return sections


def read_chunk(raw):
    r = NbtReader(raw)
    if r.u8() != TAG_COMPOUND:
        raise ValueError("区块根标签不是 Compound")
    r.string()
    y_pos = None
    heightmaps = {}
    sections = []
    while True:
        t = r.u8()
        if t == TAG_END:
            break
        key = r.string()
        if key == "yPos" and t == TAG_INT:
            y_pos = r.i32()
        elif key == "Heightmaps" and t == TAG_COMPOUND:
            heightmaps = read_heightmaps(r)
        elif key == "sections" and t == TAG_LIST:
            sections = read_sections(r)
        else:
            r.skip(t)
    return y_pos, heightmaps, sections


def read_chunk_activity(raw):
    """Return a chunk's InhabitedTime, or None when the field is missing."""
    r = NbtReader(raw)
    if r.u8() != TAG_COMPOUND:
        return None
    r.string()
    while True:
        t = r.u8()
        if t == TAG_END:
            return None
        key = r.string()
        if key == "InhabitedTime" and t == TAG_LONG:
            return r.value(TAG_LONG)
        if key == "Level" and t == TAG_COMPOUND:
            # 1.17 and older nest the chunk fields inside Level.
            while True:
                tt = r.u8()
                if tt == TAG_END:
                    break
                k = r.string()
                if k == "InhabitedTime" and tt == TAG_LONG:
                    return r.value(TAG_LONG)
                r.skip(tt)
            continue
        r.skip(t)


def read_region_chunk(data, idx):
    p = idx * 4
    off = (data[p] << 16) | (data[p + 1] << 8) | data[p + 2]
    sectors = data[p + 3]
    if not off or not sectors:
        return None
    pos = off * 4096
    if pos + 5 > len(data):
        return None
    length = U32.unpack_from(data, pos)[0]
    if length <= 1:
        return None
    comp = data[pos + 4]
    end = min(len(data), pos + 4 + length)
    payload = data[pos + 5:end]
    try:
        if comp == 1:
            return gzip.decompress(payload)
        if comp == 2:
            return zlib.decompress(payload)
        if comp == 3:
            return payload
    except Exception:
        return None
    return None


def height_bits(length):
    for bits in range(9, 17):
        per = 64 // bits
        if (256 + per - 1) // per == length:
            return bits
    return 9


def make_height_reader(hm):
    if hm is None or hm.length == 0:
        return None
    bits = height_bits(hm.length)
    per = 64 // bits
    mask = (1 << bits) - 1

    def get(index):
        return (hm.get(index // per) >> ((index % per) * bits)) & mask

    return get


def prepare_section(palette, data, y):
    names = palette if palette else ["minecraft:air"]
    bits = max(4, (max(1, len(names)) - 1).bit_length())
    per = 64 // bits
    invisible = all(is_air(n) or base_name(n) == "bedrock" for n in names)
    return (y, names, data, bits, per, invisible)


def block_at(sec, x, local_y, z):
    _, names, data, bits, per, _ = sec
    if data is None:
        return names[0] if names else "minecraft:air"
    idx = local_y * 256 + z * 16 + x
    li = idx // per
    off = (idx % per) * bits
    pi = (data.get(li) >> off) & ((1 << bits) - 1)
    return names[pi] if pi < len(names) else "minecraft:air"


def find_top_below(sections, x, z, start_y, min_y, skip_bedrock):
    y = start_y
    while y >= min_y:
        sy = y // 16
        sec = sections.get(sy)
        if sec is None or sec[5]:
            y = sy * 16 - 1
            continue
        name = block_at(sec, x, y - sy * 16, z)
        if not is_air(name) and not (skip_bedrock and base_name(name) == "bedrock"):
            return y, name
        y -= 1
    return None


def base_name(name):
    if not name:
        return ""
    s = name.split("[", 1)[0]
    if s.startswith("minecraft:"):
        s = s[10:]
    return s


def is_air(name):
    b = base_name(name)
    return b == "air" or b == "cave_air" or b == "void_air"


DYE = {
    "white": (233, 236, 236), "orange": (240, 118, 19), "magenta": (189, 68, 179),
    "light_blue": (58, 175, 217), "yellow": (248, 198, 39), "lime": (112, 185, 25),
    "pink": (237, 141, 172), "gray": (62, 68, 71), "light_gray": (142, 142, 134),
    "cyan": (21, 137, 145), "purple": (121, 42, 172), "blue": (53, 57, 157),
    "brown": (114, 71, 40), "green": (84, 109, 27), "red": (161, 39, 34),
    "black": (20, 21, 25),
}

CONCRETE = {
    "white": (207, 213, 214), "orange": (224, 97, 0), "magenta": (169, 48, 159),
    "light_blue": (36, 137, 199), "yellow": (241, 175, 21), "lime": (94, 168, 24),
    "pink": (214, 101, 143), "gray": (55, 58, 62), "light_gray": (125, 125, 115),
    "cyan": (21, 119, 136), "purple": (100, 32, 156), "blue": (45, 47, 143),
    "brown": (96, 60, 32), "green": (73, 91, 36), "red": (142, 33, 33),
    "black": (8, 10, 15),
}

WOOD = {
    "oak": (162, 130, 78), "spruce": (114, 84, 48), "birch": (196, 179, 123),
    "jungle": (160, 115, 80), "acacia": (168, 90, 50), "dark_oak": (66, 43, 20),
    "mangrove": (117, 54, 48), "cherry": (226, 178, 172), "bamboo": (193, 173, 80),
    "crimson": (101, 48, 70), "warped": (43, 104, 99), "pale_oak": (222, 216, 200),
}

LEAVES = {
    "oak_leaves": (55, 110, 40), "spruce_leaves": (45, 80, 48), "birch_leaves": (105, 140, 65),
    "jungle_leaves": (45, 110, 35), "acacia_leaves": (95, 130, 50), "dark_oak_leaves": (40, 85, 32),
    "mangrove_leaves": (55, 105, 60), "cherry_leaves": (225, 160, 190), "azalea_leaves": (75, 125, 55),
    "flowering_azalea_leaves": (100, 140, 65), "pale_oak_leaves": (165, 175, 140),
}

EXACT = {
    "water": (50, 100, 175), "bubble_column": (70, 140, 205), "lava": (230, 90, 20),
    "magma_block": (150, 60, 20), "grass_block": (106, 156, 62), "short_grass": (100, 150, 60),
    "grass": (100, 150, 60), "tall_grass": (100, 150, 60), "fern": (95, 145, 58),
    "large_fern": (95, 145, 58), "dead_bush": (140, 110, 55), "vine": (70, 110, 50),
    "moss_block": (80, 120, 50), "moss_carpet": (80, 120, 50), "pale_moss_block": (140, 150, 120),
    "pale_hanging_moss": (150, 160, 130), "hanging_roots": (120, 100, 80),
    "big_dripleaf": (90, 140, 60), "small_dripleaf": (100, 150, 70), "lily_pad": (60, 120, 50),
    "dirt": (122, 88, 60), "coarse_dirt": (113, 80, 54), "rooted_dirt": (124, 91, 63),
    "podzol": (96, 68, 34), "mycelium": (125, 115, 120), "mud": (73, 62, 50),
    "muddy_mangrove_roots": (70, 60, 48), "dirt_path": (148, 121, 65), "farmland": (110, 78, 48),
    "sand": (219, 207, 163), "suspicious_sand": (212, 200, 158), "red_sand": (180, 97, 31),
    "suspicious_gravel": (140, 130, 125), "sandstone": (216, 203, 155),
    "red_sandstone": (178, 96, 35), "smooth_sandstone": (220, 210, 165),
    "cut_sandstone": (214, 201, 152), "chiseled_sandstone": (210, 197, 148),
    "gravel": (130, 124, 120), "stone": (125, 125, 125), "cobblestone": (110, 110, 110),
    "mossy_cobblestone": (92, 108, 78), "smooth_stone": (150, 150, 150),
    "stone_bricks": (120, 120, 120), "mossy_stone_bricks": (95, 110, 80),
    "cracked_stone_bricks": (105, 105, 105), "chiseled_stone_bricks": (115, 115, 115),
    "andesite": (136, 136, 136), "polished_andesite": (130, 130, 130),
    "diorite": (188, 188, 188), "polished_diorite": (182, 182, 182),
    "granite": (149, 103, 85), "polished_granite": (145, 100, 83),
    "deepslate": (85, 85, 90), "cobbled_deepslate": (77, 77, 82),
    "polished_deepslate": (90, 90, 95), "deepslate_bricks": (80, 80, 85),
    "deepslate_tiles": (76, 76, 81), "chiseled_deepslate": (82, 82, 87),
    "tuff": (108, 109, 102), "polished_tuff": (112, 113, 106), "chiseled_tuff": (105, 106, 99),
    "calcite": (224, 224, 220), "dripstone_block": (134, 107, 92), "bedrock": (55, 55, 55),
    "obsidian": (24, 20, 36), "crying_obsidian": (44, 22, 80), "netherrack": (111, 54, 52),
    "nether_bricks": (44, 22, 26), "red_nether_bricks": (70, 7, 10), "blackstone": (42, 37, 41),
    "polished_blackstone": (48, 42, 46), "gilded_blackstone": (60, 48, 35),
    "basalt": (73, 72, 77), "smooth_basalt": (65, 64, 68), "soul_sand": (81, 62, 50),
    "soul_soil": (75, 57, 46), "crimson_nylium": (115, 30, 36), "warped_nylium": (43, 104, 99),
    "nether_wart_block": (150, 20, 20), "warped_wart_block": (20, 120, 110),
    "shroomlight": (240, 150, 70), "end_stone": (219, 222, 158),
    "end_stone_bricks": (210, 213, 150), "purpur_block": (169, 125, 169),
    "purpur_pillar": (160, 115, 160), "chorus_plant": (93, 58, 93),
    "chorus_flower": (120, 80, 120), "snow_block": (240, 250, 250), "snow": (245, 250, 250),
    "powder_snow": (235, 245, 250), "ice": (145, 183, 235), "packed_ice": (141, 180, 250),
    "blue_ice": (116, 167, 253), "frosted_ice": (170, 200, 240), "glass": (185, 210, 220),
    "glass_pane": (185, 210, 220), "tinted_glass": (70, 65, 80), "glowstone": (255, 220, 130),
    "sea_lantern": (220, 240, 235), "redstone_lamp": (160, 100, 55), "jack_o_lantern": (220, 150, 50),
    "lantern": (230, 180, 90), "soul_lantern": (100, 190, 200), "torch": (255, 200, 80),
    "soul_torch": (90, 200, 210), "campfire": (190, 120, 50), "soul_campfire": (80, 160, 170),
    "iron_block": (220, 220, 220), "gold_block": (247, 213, 74), "diamond_block": (98, 219, 214),
    "emerald_block": (43, 190, 100), "redstone_block": (175, 24, 5), "lapis_block": (30, 67, 140),
    "coal_block": (30, 30, 30), "quartz_block": (235, 229, 222), "smooth_quartz": (237, 231, 224),
    "amethyst_block": (133, 97, 191), "copper_block": (192, 107, 79),
    "exposed_copper": (161, 125, 103), "weathered_copper": (108, 153, 110),
    "oxidized_copper": (82, 162, 132), "cut_copper": (190, 106, 78),
    "netherite_block": (56, 50, 52), "lodestone": (100, 100, 110), "beacon": (120, 220, 220),
    "conduit": (150, 180, 160), "respawn_anchor": (90, 50, 120), "bell": (200, 170, 60),
    "crafting_table": (150, 110, 70), "bookshelf": (160, 140, 100),
    "enchanting_table": (120, 60, 120), "anvil": (70, 70, 75), "chipped_anvil": (70, 70, 75),
    "damaged_anvil": (70, 70, 75), "chest": (150, 110, 50), "trapped_chest": (150, 110, 50),
    "ender_chest": (45, 70, 80), "barrel": (130, 95, 55), "furnace": (110, 110, 110),
    "blast_furnace": (90, 90, 95), "smoker": (100, 95, 90), "dispenser": (100, 100, 100),
    "dropper": (100, 100, 100), "hopper": (70, 70, 75), "observer": (90, 90, 95),
    "piston": (150, 130, 100), "sticky_piston": (120, 150, 100), "piston_head": (160, 140, 105),
    "note_block": (130, 95, 70), "jukebox": (130, 95, 70), "target": (225, 215, 190),
    "lever": (120, 110, 90), "rail": (140, 140, 140), "powered_rail": (160, 130, 90),
    "detector_rail": (140, 120, 100), "activator_rail": (150, 100, 80),
    "redstone_wire": (170, 30, 30), "redstone_torch": (180, 40, 40),
    "repeater": (150, 140, 130), "comparator": (150, 140, 130),
    "daylight_detector": (120, 110, 90), "wheat": (190, 170, 80), "carrots": (90, 130, 50),
    "potatoes": (110, 150, 60), "beetroots": (120, 60, 60), "melon": (120, 160, 50),
    "pumpkin": (200, 130, 30), "carved_pumpkin": (210, 140, 35), "hay_block": (190, 160, 50),
    "sugar_cane": (140, 180, 90), "cactus": (70, 130, 50), "bamboo": (160, 180, 80),
    "nether_wart": (130, 30, 35), "cocoa": (130, 80, 40), "sweet_berry_bush": (80, 120, 50),
    "kelp": (50, 130, 80), "kelp_plant": (50, 130, 80), "seagrass": (60, 140, 80),
    "tall_seagrass": (60, 140, 80), "sponge": (190, 180, 100), "wet_sponge": (160, 170, 80),
    "honey_block": (230, 170, 50), "slime_block": (110, 190, 100), "sculk": (25, 45, 50),
    "sculk_catalyst": (30, 55, 60), "sculk_sensor": (20, 60, 65), "sculk_vein": (30, 60, 65),
}

MINERALS = {
    "coal": (45, 45, 45), "iron": (190, 160, 130), "copper": (200, 120, 80),
    "gold": (240, 200, 70), "redstone": (180, 30, 30), "lapis": (40, 80, 160),
    "diamond": (100, 220, 215), "emerald": (50, 200, 110), "quartz": (230, 225, 215),
    "ancient_debris": (90, 60, 55),
}

COLOR_CACHE = {}


def mix(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def scale(c, f):
    return (
        max(0, min(255, int(c[0] * f))),
        max(0, min(255, int(c[1] * f))),
        max(0, min(255, int(c[2] * f))),
    )


def hash_color(s):
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    hue = (h % 360) / 360.0
    sat = 0.28 + ((h >> 9) % 20) / 100.0
    light = 0.36 + ((h >> 17) % 16) / 100.0
    return hsl_to_rgb(hue, sat, light)


def hsl_to_rgb(h, s, l):
    def f(n):
        k = (n + h * 12) % 12
        a = s * min(l, 1 - l)
        return int((l - a * max(-1, min(k - 3, 9 - k, 1))) * 255)
    return f(0), f(8), f(4)


def dye_of(base, suffix):
    return DYE.get(base[:-len(suffix)])


PLANK_RE = re.compile(r"_planks$|_mosaic$")
LOG_RE = re.compile(r"_log$|_wood$|_hyphae$|_stem$")
ORE_RE = re.compile(r"_ore$")
STAIR_RE = re.compile(r"_(stairs|slab|wall)$")
FURNITURE_RE = re.compile(r"_(button|pressure_plate|trapdoor|fence_gate|fence|door|wall_hanging_sign|hanging_sign|wall_sign|sign)$")


def compute_color(full_name):
    base = base_name(full_name)
    if not base or base in ("air", "cave_air", "void_air"):
        return None
    if base in EXACT:
        return EXACT[base]
    if base in LEAVES:
        return LEAVES[base]

    if PLANK_RE.search(base):
        for key, c in WOOD.items():
            if base.startswith(key + "_"):
                return c
        return 150, 115, 70

    if LOG_RE.search(base):
        stripped = base.startswith("stripped_")
        b = base[9:] if stripped else base
        for key, c in WOOD.items():
            if b.startswith(key + "_"):
                return scale(c, 1.06 if stripped else 0.78)
        return 120, 90, 55

    if base.endswith("_leaves"):
        return 65, 110, 50
    if base.endswith("_sapling") or base.endswith("_propagule"):
        return 90, 140, 60

    if base.endswith("_concrete_powder"):
        c = dye_of(base, "_concrete_powder")
        if c:
            return mix(c, (255, 255, 255), 0.18)
    if base.endswith("_concrete"):
        key = base[:-9]
        if key in CONCRETE:
            return CONCRETE[key]
        c = dye_of(base, "_concrete")
        if c:
            return c
    if base.endswith("_terracotta"):
        c = dye_of(base, "_terracotta")
        if c:
            return mix(c, (150, 95, 68), 0.55)
        if base == "terracotta":
            return 150, 95, 68
    if base.endswith("_glazed_terracotta"):
        c = dye_of(base, "_glazed_terracotta")
        if c:
            return mix(c, (255, 255, 255), 0.15)
    if base.endswith("_stained_glass_pane"):
        c = dye_of(base, "_stained_glass_pane")
        if c:
            return mix(c, (220, 235, 240), 0.35)
    if base.endswith("_stained_glass"):
        c = dye_of(base, "_stained_glass")
        if c:
            return mix(c, (220, 235, 240), 0.35)
    if base.endswith(("_wool", "_carpet", "_bed", "_banner", "_shulker_box", "_candle")):
        for suffix in ("_wool", "_carpet", "_bed", "_banner", "_shulker_box", "_candle"):
            if base.endswith(suffix):
                c = DYE.get(base[:-len(suffix)])
                if c:
                    return scale(c, 0.72) if suffix == "_shulker_box" else c
                break

    if ORE_RE.search(base) or base == "ancient_debris":
        deep = base.startswith("deepslate_")
        stripped = base[10:] if deep else base
        stripped = stripped[:-4] if stripped.endswith("_ore") else stripped
        mineral = MINERALS.get(stripped)
        stone_base = (82, 82, 88) if deep else (125, 125, 125)
        return mix(stone_base, mineral, 0.45) if mineral else stone_base

    if base.startswith("raw_") and base.endswith("_block"):
        m = MINERALS.get(base[4:-6])
        return mix(m, (120, 100, 80), 0.35) if m else (150, 120, 90)

    if FURNITURE_RE.search(base):
        b = FURNITURE_RE.sub("", base)
        for key, c in WOOD.items():
            if b.startswith(key + "_") or b == key:
                return scale(c, 0.95)
        if b in EXACT:
            return EXACT[b]
        return 130, 105, 75

    if STAIR_RE.search(base):
        b = STAIR_RE.sub("", base)
        if b in EXACT:
            return EXACT[b]
        if b in LEAVES:
            return LEAVES[b]
        for key, c in WOOD.items():
            if b.startswith(key + "_"):
                return c
        if b.endswith("_concrete"):
            c = CONCRETE.get(b[:-9])
            if c:
                return c
        if b.endswith("_bricks") and b in EXACT:
            return EXACT[b]

    if base.startswith("potted_"):
        return compute_color(base[7:]) or (130, 100, 70)
    if base in ("flower_pot", "decorated_pot"):
        return 140, 95, 70
    if base.endswith("_coral_block") or base.endswith("_coral"):
        if base.startswith("dead_"):
            return 120, 115, 105
        if base.startswith("tube_"):
            return 50, 90, 200
        if base.startswith("brain_"):
            return 200, 90, 150
        if base.startswith("bubble_"):
            return 160, 40, 170
        if base.startswith("fire_"):
            return 190, 50, 50
        if base.startswith("horn_"):
            return 200, 180, 60
        return 180, 100, 150

    return hash_color(base)


def color_of(full_name):
    c = COLOR_CACHE.get(full_name)
    if c is None:
        c = compute_color(full_name)
        COLOR_CACHE[full_name] = c or (0, 0, 0)
    return c if c != (0, 0, 0) else None


def water_color(depth):
    return mix((82, 145, 205), (24, 58, 125), max(0.0, min(1.0, depth / 45.0)))


def render_tile(region_path, is_nether=False, size=TILE_SIZE):
    step = TILE_SIZE // size
    data = open(region_path, "rb").read()
    pixels = bytearray(bytes(BG) * (size * size))
    heights = [EMPTY_HEIGHT] * (size * size)
    cache = COLOR_CACHE

    for cz in range(32):
        for cx in range(32):
            raw = read_region_chunk(data, cz * 32 + cx)
            if raw is None:
                continue
            try:
                y_pos, heightmaps, raw_sections = read_chunk(raw)
            except Exception:
                continue
            sections = {}
            for sy, palette, sdata in raw_sections:
                sections[sy] = prepare_section(palette, sdata, sy)
            if not sections:
                continue
            min_y = y_pos * 16 if y_pos is not None else min(sections) * 16
            hget = make_height_reader(heightmaps.get("WORLD_SURFACE") or heightmaps.get("MOTION_BLOCKING"))
            fget = make_height_reader(heightmaps.get("OCEAN_FLOOR"))
            if hget is None:
                continue

            for z in range(0, 16, step):
                for x in range(0, 16, step):
                    hm_index = z * 16 + x
                    h = hget(hm_index)
                    if h <= 0:
                        continue
                    surface_y = h + min_y - 1
                    top = None
                    if is_nether:
                        if surface_y > 127:
                            sy = surface_y // 16
                            sec = sections.get(sy)
                            name = block_at(sec, x, surface_y - sy * 16, z) if sec else "minecraft:air"
                            if not is_air(name):
                                top = (surface_y, name)
                        if top is None:
                            top = find_top_below(sections, x, z, min(surface_y, 126), min_y, True)
                    else:
                        sy = surface_y // 16
                        sec = sections.get(sy)
                        name = block_at(sec, x, surface_y - sy * 16, z) if sec else "minecraft:air"
                        if not is_air(name):
                            top = (surface_y, name)
                        else:
                            top = find_top_below(sections, x, z, surface_y - 1, min_y, False)
                    if top is None:
                        continue
                    top_y, top_name = top
                    c = cache.get(top_name)
                    if c is None:
                        c = compute_color(top_name)
                        cache[top_name] = c if c else (0, 0, 0)
                    if not c:
                        continue
                    bn = base_name(top_name)
                    if bn == "water" or bn == "bubble_column":
                        depth = 8
                        if fget is not None:
                            fh = fget(hm_index)
                            if fh > 0:
                                depth = max(0, surface_y - (fh + min_y - 1))
                        c = water_color(depth)

                    px = (cx * 16 + x) // step
                    pz = (cz * 16 + z) // step
                    p = pz * size + px
                    o = p * 4
                    pixels[o] = c[0]
                    pixels[o + 1] = c[1]
                    pixels[o + 2] = c[2]
                    heights[p] = top_y

    for pz in range(size):
        base = pz * size
        for px in range(size):
            p = base + px
            h = heights[p]
            if h == EMPTY_HEIGHT:
                continue
            s = 0
            n = 0
            if px > 0:
                w = heights[p - 1]
                if w != EMPTY_HEIGHT and abs(h - w) < 48:
                    s += h - w
                    n += 1
            if pz > 0:
                nn = heights[p - size]
                if nn != EMPTY_HEIGHT and abs(h - nn) < 48:
                    s += h - nn
                    n += 1
            f = 1.0
            if n:
                f -= max(-0.22, min(0.22, (s / n) * 0.02))
            f *= 1 + max(-0.06, min(0.06, (h - 64) / 900.0))
            if f == 1.0:
                continue
            o = p * 4
            pixels[o] = max(0, min(255, int(pixels[o] * f)))
            pixels[o + 1] = max(0, min(255, int(pixels[o + 1] * f)))
            pixels[o + 2] = max(0, min(255, int(pixels[o + 2] * f)))

    return bytes(pixels)


def render_tile_gz(region_path, is_nether=False, size=TILE_SIZE):
    if size not in (256, 512):
        size = TILE_SIZE
    gc.disable()
    try:
        pixels = render_tile(region_path, is_nether, size)
    finally:
        gc.enable()
    return gzip.compress(pixels, compresslevel=3)
