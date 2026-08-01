# TODO port wall code

from typing import Callable, Sequence
import sys
import io
from base64 import b64encode
from dataclasses import dataclass, field
from enum import Enum, unique, auto

from PIL import Image

import image_manipulation
import data
from data import (
    AnimData, RenderedSection, ImageType, LayoutBehaviour, FrameInfo, LutInfo, Metadata, LayoutOffsets,
    SHEET_SCALE, FONT_SIZE
)

import blocks_meta

BLOCK_IMAGE_FOLDER_PATH = 'terraria_walls'
RENDERED_SECTION_PATH = 'rendered_wall_sections'

TILE_SPACE = SHEET_SCALE * 18

TILE_BORDER_PIXELS = SHEET_SCALE * 4
TILE_SIZE = SHEET_SCALE * 8

type XIndex = int
type YIndex = int
type Lut = Sequence[Sequence[tuple[XIndex, YIndex]]]


@unique
class WallPattern(Enum):
    """How the blocks in a frame are organised"""
    DEFAULT = auto() # Used by most blocks such as dirt
    CHECKER = auto() # Used for 2 frame non animated blocks
    SLAB = auto()    # Used for slabs and some plating
    LAYER = auto()


@unique
class AnimationType(Enum):
    NONE = auto()
    # Change frame every x miliseconds
    BASIC = auto()
    # Rainbow moss and bricks, generate a hue shifted gif
    RAINBOW = auto()
    # Starry blocks
    STARRY = auto()
    # LAVA_CLOUD = auto()
    # RAINBOW_CLOUD = auto()

@dataclass(kw_only=True) # dataclass inheritance is weird without kw_only
class WallAnimData(AnimData):
    type: AnimationType = AnimationType.NONE
    bounce: bool = False  # Duplicate sequence at the end but in reverse order
    repeat_last: int = 0  # Number of times to duplicate last frame

@unique
class Category(Enum):
    NATURAL = auto()
    WOOD = auto()
    STONE = auto()
    STONE2 = auto()
    STONE3 = auto()
    MISC_BRICK = auto()
    SAND = auto()
    TRADITIONAL = auto()
    MISC = auto()
    GLASS = auto()
    METAL = auto()
    GEMSPARK = auto()
    WALLPAPER = auto()
    ANCIENT = auto()
    DUNGEON = auto()
    NEW = auto()

@dataclass
class Wall:
    tile_number: int
    name: str
    # category: Category
    pattern: WallPattern = WallPattern.DEFAULT
    anim: WallAnimData = field(default_factory=lambda: WallAnimData())

    def section_size(self) -> int:
        """Number of pixels that make up a final square"""
        match self.pattern:
            case _:
                return 3

    def section_final_size(self) -> tuple[int, int]:
        match self.pattern:
            case _:
                return (4 * TILE_SIZE, 4 * TILE_SIZE)
    
    def sanitised_name(self) -> str:
        """Name with invalid path characters removed"""
        return self.name.replace("\n", "")

BLOCK_DICTIONARY: dict[Category, Sequence[Wall]] = {
    Category.NATURAL: (
        # Wall(2, 'Dirt Wall\n(Natural)'),
        Wall(16,  'Dirt Wall'),
        Wall(59,  'Rocky Dirt Wall'),
        Wall(170, 'Cave Dirt Wall'),
        Wall(171, 'Rough Dirt Wall'),
        Wall(196, 'Layered Dirt Wall'),
        Wall(197, 'Crumbling Dirt Wall'),
        Wall(198, 'Cracked Dirt Wall'),
        Wall(199, 'Wavy Dirt Wall'),
        Wall(15,  'Mud Wall'),
        Wall(205, 'Leafy Jungle Wall'),
        Wall(207, 'Jungle Vine Wall'),
        Wall(63,  'Grass Wall'),
        Wall(64,  'Jungle Wall'),
        Wall(65,  'Flower Wall'),
        Wall(69,  'Corrupt Grass Wall'),
        Wall(81,  'Crimson Grass Wall'),
        Wall(70,  'Hallowed Grass Wall'),
        Wall(40,  'Snow Wall'),
        Wall(71,  'Ice Wall'),
        Wall(74,  'Mushroom Wall'),
        Wall(80,  'Mushroom Wall\n(Natural)'),
        Wall(208, 'Ember Wall'),
        Wall(209, 'Cinder Wall'),
        Wall(210, 'Magma Wall'),
        Wall(211, 'Smouldering Stone Wall'),
        Wall(79,  'Obisidian Wall'),
    ),
    Category.WOOD: (
        Wall(4,   'Wood Wall'),
        Wall(42,  'Rich Mahogany Wall'),
        Wall(149, 'Boreal Wood Wall'),
        Wall(312, 'Bamboo Wall'),
        Wall(313, 'Large Bamboo Wall'),
        Wall(151, 'Palm Wood Wall'),
        Wall(316, 'Ash Wood Wall'),
        Wall(41,  'Ebonwood Wall'),
        Wall(85,  'Shadewood Wall'),
        Wall(43,  'Pearlwood Wall'),
        Wall(115, 'Spooky Wood Wall'),
        Wall(27,  'Planked Wall'),
        Wall(72,  'Cactus Wall'),
        Wall(106, 'Wooden Fence'),
        Wall(139, 'Rich Mahogany Fence'),
        Wall(150, 'Boreal Wood Fence'),
        Wall(315, 'Bamboo Fence'),
        Wall(152, 'Palm Wood Fence'),
        Wall(317, 'Ash Wood Fence'),
        Wall(138, 'Ebonwood Fence'),
        Wall(141, 'Shadewood Fence'),
        Wall(140, 'Pearlwood Fence'),
        Wall(78,  'Living Wood Wall'),
        Wall(60,  'Living Leaf Wall'),
        Wall(358, 'Pine Wood Wall', pattern=WallPattern.CHECKER),
        Wall(353, 'Pine Tree Wall'),
        Wall(351, 'Feywood Wall'),
    ),
    Category.STONE2: (
        Wall(54, 'Green Mossy Wall'),
        Wall(55, 'Brown Mossy Wall'),
        Wall(56, 'Red Mossy Wall'),
        Wall(57, 'Blue Mossy Wall'),
        Wall(58, 'Purple Mossy Wall'),
    ),
    Category.STONE3: (
        Wall(48,  'Amethyst Stone Wall'),
        Wall(49,  'Topaz Stone Wall'),
        Wall(53,  'Diamond Stone Wall'),
        Wall(314, 'Amber Stone Wall'),
        Wall(50,  'Sapphire Stone Wall'),
        Wall(51,  'Emerald Stone Wall'),
        Wall(52,  'Ruby Stone Wall'),
    ),
    Category.STONE: (
        Wall(1, 'Stone Wall'),
        Wall(61, 'Old Stone Wall'),
        Wall(185, 'Craggy Stone Wall', pattern=WallPattern.SLAB),
        Wall(204, 'Lichen Stone Wall'),
        Wall(206, 'Ivy Stone Wall'),
        Wall(212, 'Worn Stone Wall'),
        Wall(213, 'Stalactite Stone Wall'),
        Wall(214, 'Mottled Stone Wall'),
        Wall(215, 'Fractured Stone Wall'),
        Wall(319, 'Reef Wall'),
        Wall(178, 'Marble Wall'),
        Wall(179, 'Smooth Marble Wall', pattern=WallPattern.SLAB),
        Wall(180, 'Granite Wall'),
        Wall(181, 'Smooth Granite Wall'),
        Wall(3, 'Ebonstone Wall'),
        # Wall(246, 'Ebonstone Wall', 'category': 'ignore'},
        Wall(188, 'Corrupt Growth Wall'),
        Wall(189, 'Corrupt Mass Wall'),
        Wall(191, 'Corrupt Tendril Wall'),
        Wall(190, 'Corrupt Pustule Wall'),
        Wall(83, 'Crimstone Wall'),
        Wall(192, 'Crimson Crust Wall'),
        Wall(193, 'Crimson Scab Wall'),
        Wall(194, 'Crimson Teeth Wall'),
        Wall(195, 'Crimson Blister Wall'),
        Wall(233, 'Lesion Block Wall'),
        Wall(236, 'Spider Nest Wall'),
        Wall(28, 'Pearlstone Wall'),
        Wall(201, 'Hallowed Cavern Wall'),
        Wall(200, 'Hallowed Prism Wall'),
        Wall(202, 'Hallowed Shard Wall'),
        Wall(203, 'Hallowed Crystalline Wall'),
        Wall(186, 'Crystal Block Wall'),
        Wall(321, 'Aetherium Wall'),
        Wall(322, 'Aetherium Brick Wall'),
    ),
    Category.MISC_BRICK: (
        Wall(147, 'Stone Slab Wall', pattern=WallPattern.SLAB),
        Wall(6, 'Red Brick Wall'),
        Wall(5, 'Gray Brick Wall'),
        Wall(31, 'Snow Brick Wall'),
        Wall(84, 'Ice Brick Wall'),
        Wall(44, 'Rainbow Brick Wall', anim=WallAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=60)),
        Wall(34, 'Sandstone Brick Wall'),
        Wall(35, 'Ebonstone Brick Wall'),
        Wall(234, 'Crimstone Brick Wall'),
        Wall(24, 'Mudstone Brick Wall'),
        Wall(82, 'Disc Wall'),
        Wall(348, 'Fall Star Wall'),
        Wall(360, 'Crescent Wall'),
        Wall(14, 'Obsidian Brick Wall'),
        Wall(23, 'Iridescent Brick Wall'),
        Wall(13, 'Hellstone Brick Wall'),
        Wall(22, 'Pearlstone Brick Wall'),
        Wall(87, 'Lihzahrd Brick Wall'),
        Wall(341, 'Lava Moss Brick Wall'),
        Wall(342, 'Argon Moss Brick Wall'),
        Wall(343, 'Krypton Moss Brick Wall'),
        Wall(344, 'Xenon Moss Brick Wall'),
        Wall(345, 'Neon Moss Brick Wall'),
        Wall(346, 'Helium Moss Brick Wall', anim = WallAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=60)),
    ),
    Category.SAND: (
        Wall(187, 'Sandstone Wall'),
        Wall(235, 'Smooth Sandstone Wall'),
        Wall(216, 'Hardened Sand Wall'),
        Wall(223, 'Desert Fossil Wall'),
        Wall(220, 'Ebonsandstone Wall'),
        Wall(217, 'Hardened Ebonsand Wall'),
        Wall(221, 'Crimsandstone Wall'),
        Wall(218, 'Hardened Crimsand Wall'),
        Wall(222, 'Pearlsandstone Wall'),
        Wall(219, 'Hardened Pearlsand Wall'),
    ),
    Category.TRADITIONAL: (
        Wall(39, 'Gray Stucco Wall'),
        Wall(36, 'Red Stucco Wall'),
        Wall(37, 'Yellow Stucco Wall'),
        Wall(38, 'Green Stucco Wall'),
        Wall(142, 'White Dynasty Wall'),
        Wall(143, 'Blue Dynasty Wall'),
    ),
    Category.MISC: (
        Wall(29, 'Candy Cane Wall'),
        Wall(30, 'Green Candy Cane Wall'),
        Wall(62, 'Spider Wall'),
        Wall(66, 'Grass Wall'),
        Wall(67, 'Jungle Wall'),
        Wall(68, 'Flower Wall'),
        Wall(73, 'Cloud Wall'),
        Wall(75, 'Bone Block Wall'),
        Wall(76, 'Slime Block Wall'),
        Wall(77, 'Flesh Block Wall'),
        Wall(86, 'Hive Wall'),
        Wall(113, 'Pumpkin Wall'),
        Wall(114, 'Hay Wall'),
        Wall(225, 'Cog Wall', anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=2, frame_duration=100)),
        Wall(228, 'Silly Pink Balloon Wall'),
        Wall(229, 'Silly Purple Balloon Wall'),
        Wall(230, 'Silly Green Balloon Wall'),
        Wall(318, 'Echo Wall'),
        Wall(320, 'Poo Wall'),
        Wall(363, 'Office Wall', pattern=WallPattern.CHECKER),
        Wall(366, 'Boulder Wall', pattern=WallPattern.CHECKER),
        Wall(359, 'Harpy Wall', pattern=WallPattern.CHECKER),
        Wall(362, 'Spike Wall', pattern=WallPattern.CHECKER),
        Wall(354, 'Easter Wall', pattern=WallPattern.LAYER),
        Wall(357, 'Jellyfish Wall', anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=100,
        )),
        Wall(365, 'Aquarium Wall', anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=130,
        )),
        Wall(355, 'Gothic Brick Wall', pattern=WallPattern.CHECKER),
        Wall(364, 'Forbidden Wall'),
        Wall(361, 'Librarian Wall'),
        Wall(356, 'Flinx Fur Wall'),
    ),
    Category.GLASS: (
        Wall(21,  'Glass Wall'),
        Wall(88,  'Purple Stained Glass'),
        Wall(92,  'Red Stained Glass'),
        Wall(241, 'Orange Stained Glass'),
        Wall(89,  'Yellow Stained Glass'),
        Wall(91,  'Green Stained Glass'),
        Wall(90,  'Blue Stained Glass'),
        Wall(93,  'Multicolored Stained\nGlass'),
        Wall(136, 'Waterfall Wall', anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Wall(137, 'Lavafall Wall', anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=200)),
        Wall(172, 'Honeyfall Wall', anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=200)),
        Wall(226, 'Sandfall Wall', anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=200)),
        Wall(347, "Shimmerfall Wall", anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=150,
        )),
        Wall(227, 'Snowfall Wall', anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Wall(168, 'Confetti Wall', anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Wall(169, 'Midnight Confetti Wall', anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Wall(242, 'Gold Starry Wall', anim=WallAnimData(type=AnimationType.STARRY, num_frames=8, frame_duration=300)),
        Wall(243, 'Blue Starry Wall', anim=WallAnimData(type=AnimationType.STARRY, num_frames=8, frame_duration=300)),
    ),
    Category.METAL: (
        Wall(12, 'Copper Brick Wall'),
        Wall(146, 'Copper Plating Wall', pattern=WallPattern.SLAB),
        Wall(45, 'Tin Brick Wall'),
        Wall(167, 'Tin Plating Fence', pattern=WallPattern.SLAB),
        Wall(231, 'Iron Brick Wall'),
        Wall(145, 'Iron Fence'),
        Wall(245, 'Wrought Iron Fence'),
        Wall(232, 'Lead Brick Wall'),
        Wall(107, 'Lead Fence'),
        Wall(11, 'Silver Brick Wall'),
        Wall(46, 'Tungsten Brick Wall'),
        Wall(10, 'Gold Brick Wall'),
        Wall(47, 'Platinum Brick Wall'),
        Wall(33, 'Demonite Brick Wall'),
        Wall(174, 'Crimtane Brick Wall'),
        Wall(182, 'Meteorite Brick Wall'),
        Wall(177, 'Hellstone Brick Wall'),
        Wall(25, 'Cobalt Brick Wall'),
        Wall(109, 'Palladium Column Wall'),
        Wall(26, 'Mythril Brick Wall'),
        Wall(110, 'Bubblegum Block Wall'),
        Wall(32, 'Adamantite Beam Wall'),
        Wall(111, 'Titanstone Block Wall'),
        Wall(352, "Hallowed Brick Wall"),
        Wall(173, 'Chlorophyte Brick Wall'),
        Wall(175, 'Shroomite Plating Wall'),
        Wall(237, 'Solar Brick Wall'),
        Wall(238, 'Vortex Brick Wall'),
        Wall(239, 'Nebula Brick Wall'),
        Wall(240, 'Stardust Brick Wall'),
        Wall(176, 'Martian Conduit Wall'),
        Wall(224, 'Luminite Brick Wall', pattern=WallPattern.CHECKER),
        Wall(323, 'Lunar Rust Brick Wall', pattern=WallPattern.CHECKER),
        Wall(324, 'Dark Celestial Brick Wall', pattern=WallPattern.CHECKER),
        Wall(325, 'Astra Brick Wall', pattern=WallPattern.CHECKER),
        Wall(326, 'Cosmic Ember Brick Wall', pattern=WallPattern.CHECKER),
        Wall(327, 'Cryocore Brick Wall', pattern=WallPattern.CHECKER),
        Wall(328, 'Mercury Brick Wall', pattern=WallPattern.CHECKER),
        Wall(329, 'Star Royal Brick Wall', pattern=WallPattern.CHECKER),
        Wall(330, 'Heavenforge Brick Wall', pattern=WallPattern.CHECKER),
    ),
    Category.GEMSPARK: (
        Wall(154, 'Amethyst Gemspark Wall'),
        Wall(166, 'Topaz Gemspark Wall'),
        Wall(165, 'Sapphire Gemspark Wall'),
        Wall(156, 'Emerald Gemspark Wall'),
        Wall(164, 'Ruby Gemspark Wall'),
        Wall(155, 'Diamond Gemspark Wall'),
        Wall(153, 'Amber Gemspark Wall'),
        Wall(158, 'Offline Amethyst\nGemspark Wall'),
        Wall(163, 'Offline Topaz\nGemspark Wall'),
        Wall(162, 'Offline Sapphire\nGemspark Wall'),
        Wall(160, 'Offline Emerald\nGemspark Wall'),
        Wall(161, 'Offline Ruby\nGemspark Wall'),
        Wall(159, 'Offline Diamond\nGemspark Wall'),
        Wall(157, 'Offline Amber\nGemspark Wall'),
    ),
    Category.WALLPAPER: (
        Wall(116, 'Christmas Tree Wallpaper'),
        Wall(117, 'Ornament Wallpaper'),
        Wall(118, 'Candy Cane Wallpaper'),
        Wall(119, 'Festive Wallpaper'),
        Wall(120, 'Stars Wallpaper'),
        Wall(121, 'Squiggles Wallpaper'),
        Wall(122, 'Snowflake Wallpaper'),
        Wall(123, 'Krampus Horn Wallpaper'),
        Wall(124, 'Bluegreen Wallpaper'),
        Wall(125, 'Grinch Finger Wallpaper'),
        Wall(126, 'Fancy Gray Wallpaper'),
        Wall(127, 'Ice Floe Wallpaper'),
        Wall(128, 'Music Wallpaper'),
        Wall(129, 'Purple Rain Wallpaper'),
        Wall(130, 'Rainbow Wallpaper'),
        Wall(131, 'Sparkle Stone Wallpaper'),
        Wall(132, 'Starlit Heaven Wallpaper'),
        Wall(133, 'Bubble Wallpaper'),
        Wall(134, 'Copper Pipe Wallpaper'),
        Wall(135, 'Ducky Wallpaper'),
        Wall(144, 'Rune Wallpaper', anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=9, frame_duration=80, repeat_last=10, bounce=True)),
        Wall(148, 'Sail'),
    ),
    Category.ANCIENT: (
        Wall(331, 'Ancient Blue Brick\nWall'),
        Wall(333, 'Ancient Pink Brick\nWall'),
        Wall(332, 'Ancient Green Brick\nWall'),
        Wall(334, 'Ancient Gold Brick\nWall'),
        Wall(335, 'Ancient Silver Brick\nWall'),
        Wall(336, 'Ancient Copper Brick\nWall'),
        Wall(337, 'Ancient Obsidian Brick\nWall'),
        Wall(338, 'Ancient Hellstone Brick\nWall'),
        Wall(339, 'Ancient Cobalt Brick\nWall'),
        Wall(340, 'Ancient Mythril Brick\nWall'),
    ),
    Category.DUNGEON: (
        Wall(7,  'Blue Brick Wall'),
        Wall(94, 'Blue Slab Wall'),
        Wall(95, 'Blue Tiled Wall'),
        Wall(9,  'Pink Brick Wall'),
        Wall(96, 'Pink Slab Wall'),
        Wall(97, 'Pink Tiled Wall'),
        Wall(8,  'Green Brick Wall'),
        Wall(98, 'Green Slab Wall'),
        Wall(99, 'Green Tiled Wall'),
    ),
    Category.NEW: (
    ),
    # 100: {'name': 'Blue Slab Wall', 'category': 'ignore'},
    # 101: {'name': 'Blue Tiled Wall', 'category': 'ignore'},
    # 102: {'name': 'Pink Slab Wall', 'category': 'ignore'},
    # 103: {'name': 'Pink Tiled Wall', 'category': 'ignore'},
    # 104: {'name': 'Green Slab Wall', 'category': 'ignore'},
    # 105: {'name': 'Green Tiled Wall', 'category': 'ignore'},
    # 112: {'name': 'Lihzahrd Brick Wall', 'category': 'ignore'},
    # 183: {'name': 'Marble Wall', 'category': 'ignore'},
    # 184: {'name': 'Granite Wall', 'category': 'ignore'},
}


# ------ Image Lookup Tables ------ #

# Lookup table for what border tiles to include in the image
BORDER_INCLUDE_LUT = {
    (0, 0):  (-1, 0, 0, 0),
    (1, 0):  (0, -1, 0, 0),
    (2, 0):  (0, -1, 0, 0),
    (3, 0):  (0, -1, 0, 0),
    (4, 0):  (0, 0, 1, 0),
    (5, 0):  (-1, 0, 1, 0),
    (6, 0):  (-1, -1, 1, 0),
    (7, 0):  (-1, -1, 1, 0),
    (8, 0):  (-1, -1, 1, 0),
    (9, 0):  (-1, -1, 0, 1),
    (10, 0): (0, 0, 0, 0),
    (11, 0): (0, 0, 0, 0),
    (12, 0): (0, -1, 1, 1),
    (0, 1):  (-1, 0, 0, 0),
    (1, 1):  (0, 0, 0, 0),
    (2, 1):  (0, 0, 0, 0),
    (3, 1):  (0, 0, 0, 0),
    (4, 1):  (0, 0, 1, 0),
    (5, 1):  (-1, 0, 1, 0),
    (6, 1):  (0, 0, 0, 0),
    (7, 1):  (0, 0, 0, 0),
    (8, 1):  (0, 0, 0, 0),
    (9, 1):  (-1, -1, 0, 1),
    (10, 1): (0, 0, 0, 0),
    (11, 1): (0, 0, 0, 0),
    (12, 1): (0, -1, 1, 1),
    (0, 2):  (-1, 0, 0, 0),
    (1, 2):  (0, 0, 0, 1),
    (2, 2):  (0, 0, 0, 1),
    (3, 2):  (0, 0, 0, 1),
    (4, 2):  (0, 0, 1, 0),
    (5, 2):  (-1, 0, 1, 0),
    (6, 2):  (0, 0, 0, 0),
    (7, 2):  (0, 0, 0, 0),
    (8, 2):  (0, 0, 0, 0),
    (9, 2):  (-1, -1, 0, 1),
    (10, 2): (0, 0, 0, 0),
    (11, 2): (0, 0, 0, 0),
    (12, 2): (0, -1, 1, 1),
    (0, 3):  (-1, -1, 0, 0),
    (1, 3):  (0, -1, 1, 0),
    (2, 3):  (-1, -1, 0, 0),
    (3, 3):  (0, -1, 1, 0),
    (4, 3):  (-1, -1, 0, 0),
    (5, 3):  (0, -1, 1, 0),
    (6, 3):  (-1, 0, 1, 1),
    (7, 3):  (-1, 0, 1, 1),
    (8, 3):  (-1, 0, 1, 1),
    (9, 3):  (-1, -1, 1, 1),
    (10, 3): (-1, -1, 1, 1),
    (11, 3): (-1, -1, 1, 1),
    (12, 3): (0, 0, 0, 0),
    (0, 4):  (-1, 0, 0, 1),
    (1, 4):  (0, 0, 1, 1),
    (2, 4):  (-1, 0, 0, 1),
    (3, 4):  (0, 0, 1, 1),
    (4, 4):  (-1, 0, 0, 1),
    (5, 4):  (0, 0, 1, 1),
    (6, 4):  (0, -1, 0, 1),
    (7, 4):  (0, -1, 0, 1),
    (8, 4):  (0, -1, 0, 1),
    (9, 4):  (0, 0, 0, 0),
    (10, 4): (0, 0, 0, 0),
    (11, 4): (0, 0, 0, 0),
    (12, 4): (0, 0, 0, 0),
    (0, 5):  (-1, 0, 0, 0),  # Used by slab and plating blocks
    (1, 5):  (0, -1, 0, 0),
    (2, 5):  (0, 0, 0, 0),
    (3, 5):  (0, 0, 0, 1),
    (4, 5):  (0, 0, 1, 0),
    (5, 5):  (-1, 0, 1, 0),
    (6, 5):  (-1, -1, 1, 0),
    (7, 5):  (0, 0, 0, 0),
    (8, 5):  (0, 0, 0, 0),
    (9, 5):  (-1, -1, 0, 1),
    (10, 5): (0, 0, 0, 0),
    (11, 5): (0, 0, 0, 0),
    (12, 5): (0, -1, 1, 1),
    (0, 6):  (-1, -1, 0, 0),
    (1, 6):  (0, -1, 1, 0),
    (2, 6):  (-1, 0, 0, 1),
    (3, 6):  (0, 0, 1, 1),
    (4, 6):  (-1, 0, 1, 1),
    (5, 6):  (0, -1, 0, -1),
    (6, 6):  (-1, -1, 1, 1),
}

# Used for non-blending single frame blocks
# DEFAULT_NO_BLEND_PATTERN_LUT = (
#     ((0, 3), (2, 0), (1, 3),),
#     ((0, 1), (2, 1), (4, 1),),
#     ((0, 4), (2, 2), (1, 4),),
# )
DEFAULT_NO_BLEND_PATTERN_LUT = FrameInfo(
    info=LutInfo(
        tiles_x=18, tiles_y=5,
        pixels_from_border = 4 * SHEET_SCALE,
        tile_space = 10 * SHEET_SCALE,
    ),
    index_table=(
        ((0, 3), (2, 0), (1, 3),),
        ((0, 1), (7, 1), (4, 1),),
        ((0, 4), (2, 2), (1, 4),),
    )
)

# Used for non-blending non animated two frame blocks
# CHECKER_NO_BLEND_PATTERN_LUT = (
#     ((0, 3), (2, 0), (1, 3),),
#     ((0, 2), (1, 6), (4, 2),),
#     ((0, 4), (2, 2), (1, 4),),
# )
CHECKER_NO_BLEND_PATTERN_LUT = FrameInfo(
    info=LutInfo(
        tiles_x=18, tiles_y=7,
        pixels_from_border = 4 * SHEET_SCALE,
        tile_space = 10 * SHEET_SCALE,
    ),
    index_table=(
        ((0, 3), (2, 0), (1, 3),),
        ((0, 2), (2, 5), (4, 2),),
        ((0, 4), (2, 2), (1, 4),),
    )
)

# Used for non-blending non animated two frame blocks
# LAYER_NO_BLEND_PATTERN_LUT = (
#     ((0, 3), (1, 0), (1, 3),),
#     ((0, 1), (2, 1), (4, 1),),
#     ((0, 4), (1, 2), (1, 4),),
# )
LAYER_NO_BLEND_PATTERN_LUT = FrameInfo(
    info=LutInfo(
        tiles_x=18, tiles_y=7,
        pixels_from_border = 4 * SHEET_SCALE,
        tile_space = 10 * SHEET_SCALE,
    ),
    index_table=(
        ((0, 3), (1, 0), (1, 3),),
        ((0, 1), (2, 1), (4, 1),),
        ((0, 4), (1, 2), (1, 4),),
    )
)

# Pattern used by slabs and plates
# SLAB_PATTERN_LUT = (
#     ((4, 3), (1, 0), (1, 3),),
#     ((0, 1), (1, 6), (4, 1),),
#     ((0, 4), (3, 2), (1, 4),),
# )
SLAB_PATTERN_LUT = FrameInfo(
    info=LutInfo(
        tiles_x=18, tiles_y=7,
        pixels_from_border = 4 * SHEET_SCALE,
        tile_space = 10 * SHEET_SCALE,
    ),
    index_table=(
        ((4, 3), (1, 0), (1, 3),),
        ((0, 1), (2, 5), (4, 1),),
        ((0, 4), (3, 2), (1, 4),),
    )
)

@dataclass
class CategoryLayout:
    category: Category
    layout: LayoutBehaviour = LayoutBehaviour.ALTERNATING

@dataclass
class ColumnInfo:
    x_offset_to_next: int
    categories: Sequence[CategoryLayout]

CATEGORY_LAYOUT_INFOS = (
    ColumnInfo(x_offset_to_next=300, categories=(
        CategoryLayout(Category.NATURAL),
        CategoryLayout(Category.DUNGEON),
        CategoryLayout(Category.ANCIENT),
    )),
    ColumnInfo(x_offset_to_next=300, categories=(
        CategoryLayout(Category.WOOD),
        CategoryLayout(Category.STONE2),
        CategoryLayout(Category.SAND),
        CategoryLayout(Category.STONE3),
    )),
    ColumnInfo(x_offset_to_next=300, categories=(
        CategoryLayout(Category.STONE),
        CategoryLayout(Category.GLASS),
    )),
    ColumnInfo(x_offset_to_next=300, categories=(
        CategoryLayout(Category.MISC_BRICK),
        CategoryLayout(Category.WALLPAPER),
    )),
    ColumnInfo(x_offset_to_next=300, categories=(
        CategoryLayout(Category.TRADITIONAL),
        CategoryLayout(Category.MISC),
        CategoryLayout(Category.GEMSPARK),
    )),
    ColumnInfo(x_offset_to_next=300, categories=(
        CategoryLayout(Category.METAL),
    )),
)

LAYOUT_OFFSETS = LayoutOffsets(
    text_x_offset = TILE_SIZE * 5.5,
    text_y_offset = TILE_SIZE + FONT_SIZE,
    row_advance = 3,
    category_advance = 3,
)

def extract_tile(
        img: Image.Image, indices: tuple[int, int],
        num_frames_y: int, frame: int, info: LutInfo,
    ) -> Image.Image:
    lo, uo, ro, do = map(lambda t: t * TILE_BORDER_PIXELS, BORDER_INCLUDE_LUT[indices])
    return image_manipulation.extract_tile_animated_border(
        img, indices, num_frames_y, frame,
        tile_size=(TILE_SIZE, TILE_SIZE), info=info, 
        border_offsets=(lo, uo, ro, do))

TILE_IMG_PREPASS: dict[int, Callable[[Image.Image], None]] = {
    168: blocks_meta.confetti_block_transparency_workaround,
    227: blocks_meta.confetti_block_transparency_workaround,
}

def render_wall_default(img: Image.Image, wall: Wall, lut: FrameInfo) -> bytes:
    """Render a block to a base64 encoded png image"""
    tile_list: list[Image.Image] = []

    _, frames_y = data.fix_frame_dims(wall.anim)

    for row in lut.index_table:
        for indices in row:
            tile = extract_tile(
                img, indices, frames_y, 0, lut.info,
                # ,wall.anim.frame_offset
                )
            tile_list.append(tile)

    final_img = image_manipulation.image_grid(tile_list, wall.section_size())
    byte_file = io.BytesIO()
    final_img.save(byte_file, format=ImageType.PNG.name)
    if data.DEBUG_SAVE_BLOCK_SECTIONS:
        final_img.save(f'{RENDERED_SECTION_PATH}/{wall.tile_number} {wall.sanitised_name()}.png')
    return b64encode(byte_file.getvalue())

def render_wall_animated(img: Image.Image, wall: Wall, lut: FrameInfo) -> bytes:
    """Render an animated block to a base64 encoded gif image"""
    tile_list: list[Image.Image] = []
    
    frame_duration = wall.anim.frame_duration
    _, frames_y = data.fix_frame_dims(wall.anim)

    match wall.anim.type:
        case AnimationType.BASIC:
            for f in range(wall.anim.num_frames):
                tile_sequence = []
                for row in lut.index_table:
                    for index in row:
                        tile = extract_tile(
                            img, index, frames_y, f, lut.info)
                        tile_sequence.append(tile)
                frame = image_manipulation.image_grid(tile_sequence, wall.section_size())
                frame.resize((32, 32))
                tile_list.append(frame)
                        
        case AnimationType.RAINBOW:
            img_mask = None
            try:
                # Try to get a rainbow image mask
                with Image.open(f"{BLOCK_IMAGE_FOLDER_PATH}/masks/Tiles_{wall.tile_number}_mask.png") as mask_img:
                    img_mask = mask_img.copy()
            except FileNotFoundError:
                pass

            for f in range(wall.anim.num_frames):
                tile_sequence = []
                mask_sequence = []
                for row in lut.index_table:
                    for index in row:
                        tile = extract_tile(img, index, frames_y, 0, lut.info)
                        tile_sequence.append(tile)
                        # Extract alpha mask tile
                        if img_mask:
                            mask_tile = extract_tile(img_mask, index, frames_y, 0, lut.info)
                            mask_sequence.append(mask_tile)

                frame = image_manipulation.image_grid(tile_sequence, wall.section_size())
                shifted_frame = image_manipulation.image_hue_shift(frame, f / wall.anim.num_frames)

                # Alpha blend if the tile has a mask
                if img_mask:
                    mask_frame = image_manipulation.image_grid(mask_sequence, wall.section_size())
                    shifted_frame = image_manipulation.alpha_blend_img(frame, shifted_frame, mask_frame)

                shifted_frame.resize((32, 32))
                tile_list.append(shifted_frame)
                    
        case AnimationType.STARRY:
            # Starry block frames are duplicated, double speed to compensate
            frame_duration = wall.anim.frame_duration // 2
            starry_night_anim_offset = [
                [12, 9, 6],
                [9, 6, 3],
                [6, 3, 0]]
            # starry_night_anim_offset = [
            #     [4, 3, 2],
            #     [3, 2, 1],
            #     [2, 1, 0]]
            # starry_night_anim_offset = [
            #     [6, 5, 4],
            #     [4, 3, 2],
            #     [2, 1, 0]]

            intermediate_frames = []
            num_intermediates = wall.anim.num_frames * 2
            for f in range(num_intermediates):
                intermediate_frames.append([
                    [None, None, None],
                    [None, None, None],
                    [None, None, None],
                ])

            for f in range(wall.anim.num_frames):
                # for row in lut:
                #     for index in row:
                for j, row in enumerate(lut.index_table):
                    for i, index in enumerate(row):
                        # index = indices[(i, j)]
                        tile = extract_tile(img, index, frames_y, f, lut.info)
                        offset = starry_night_anim_offset[j][i]
                        intermediate_frames[(f * 2 + offset) % num_intermediates][j][i] = tile
                        intermediate_frames[(f * 2 + offset + 1) % num_intermediates][j][i] = tile

            for f in range(num_intermediates):
                tile_sequence = []
                frame = intermediate_frames[f]
                for j in range(len(lut.index_table)):
                    row = frame[j]
                    for i in range(len(row)):
                        tile_sequence.append(row[i])
                frame = image_manipulation.image_grid(tile_sequence, wall.section_size())
                tile_list.append(frame)

    # # Pretty ugly but gets the wall to animate in reverse and with extended frames
    # # Used for the rune wall
    # repeat_frame_last = None
    # repeat_frame_first = None
    # repeat_duration = None
    # if 'repeat_last' in wa:
    #     repeat_frame_last = tile_list[-1]
    #     repeat_frame_first = tile_list[0]
    #     repeat_duration = wa['duration'] * wa['repeat_last']
    # if 'reverse' in wa:
    #     tile_tmp_list = tile_list
    #     dur_tmp_list = duration_list

    #     tile_tmp_list.append(repeat_frame_last)
    #     dur_tmp_list.append(repeat_duration // 2)
    #     # print(list(reversed(tile_list)))
    #     tile_tmp_list.extend(list(reversed(tile_list))[0:-1])
    #     dur_tmp_list.extend(list(reversed(duration_list)))
    #     tile_tmp_list.append(repeat_frame_first)
    #     dur_tmp_list.append(repeat_duration)
    #     # print((tile_tmp_list, dur_tmp_list))
    #     tile_list = tile_tmp_list
    #     duration_list = dur_tmp_list
    #     duration_list.pop(0)

    # repeat_frame_last = None
    # repeat_frame_first = None
    # repeat_duration = None

    bounced = []
    if wall.anim.bounce:
        bounced = list(reversed(tile_list))

    repeated = []
    repeated_bounced = []
    if wall.anim.repeat_last > 0:

        # TODO Avoid duplicating repeat frame n times by passing a different duration to gif_img.save
        # wall.anim.frame_duration * wall.anim.repeat_last?
        repeated = [tile_list[-1] for _ in range(wall.anim.repeat_last)]
        
        # Repeat bounced frames to transition back smoothly
        if len(bounced) > 0:
            repeated_bounced = [bounced[-1] for _ in range(wall.anim.repeat_last)]
        
    tile_list.extend(repeated)
    tile_list.extend(bounced)
    tile_list.extend(repeated_bounced)
        

    if wall.anim.is_reversed:
        gif_img = tile_list[0]
        tile_list = list(reversed(tile_list))
        tile_list.pop(-1)
    else:
        gif_img = tile_list[0]
        tile_list.pop(0)
    
    byte_file = io.BytesIO()

    gif_img.save(
        byte_file, format=ImageType.GIF.name,
        save_all=True, append_images=tile_list, disposal=2, loop=0,
        duration=frame_duration,
        background=0, optimise=False, interlace=True
    )
    if data.DEBUG_SAVE_BLOCK_SECTIONS:
        gif_img.save(
            f'{RENDERED_SECTION_PATH}/{wall.tile_number} {wall.sanitised_name()}.gif',
            save_all=True, append_images=tile_list, disposal=2, loop=0,
            duration=frame_duration,
            background=0, optimise=False, interlace=True
        )

    return b64encode(byte_file.getvalue())


class WallMetadata(Metadata):

    # Blocks

    @staticmethod
    def get_tile_dictionary() -> dict[Category, Sequence[Wall]]:
        return BLOCK_DICTIONARY

    # Lookup tables

    @staticmethod
    def get_template_and_lut(pattern: WallPattern) -> FrameInfo:
        match pattern:
            case WallPattern.DEFAULT:
                # template = DEFAULT_NO_BLEND_PATTERN_TEMPLATE
                lut = DEFAULT_NO_BLEND_PATTERN_LUT
            case WallPattern.CHECKER:
                # template = CHECKER_NO_BLEND_PATTERN_TEMPLATE
                lut = CHECKER_NO_BLEND_PATTERN_LUT
            case WallPattern.SLAB:
                # template = SLAB_PATTERN_TEMPLATE
                lut = SLAB_PATTERN_LUT
            case WallPattern.LAYER:
                # template = LAYER_NO_BLEND_PATTERN_TEMPLATE
                lut = LAYER_NO_BLEND_PATTERN_LUT
            # case WallPattern.BOULDER:
            #     # template = BOULDER_PATTERN_TEMPLATE
            #     lut = BOULDER_PATTERN_LUT
        # return template, lut
        return lut

    @staticmethod
    def get_block_path(tile_number: int) -> str:
        return f"{BLOCK_IMAGE_FOLDER_PATH}/Wall_{tile_number}.png"

    # Process images before 

    @staticmethod
    def get_tile_img_prepasses() -> dict[int, Callable[[Image.Image], None]]:
        return TILE_IMG_PREPASS

    @staticmethod
    def image_folder_path() -> str:
        return BLOCK_IMAGE_FOLDER_PATH

    @staticmethod
    def rendered_image_folder_path() -> str:
        return RENDERED_SECTION_PATH
    
    # Render blocks

    @staticmethod
    def render_block(img: Image.Image, block: Wall, lut: FrameInfo) -> RenderedSection:
        if block.anim.type == AnimationType.NONE:
            render = RenderedSection(
                block.tile_number, ImageType.PNG,
                render_wall_default(img, block, lut))
        else:
            render = RenderedSection(
                block.tile_number, ImageType.GIF,
                render_wall_animated(img, block, lut))
        return render

    # Where to place blocks when generating svg

    @staticmethod
    def get_category_layout_info() -> Sequence[ColumnInfo]:
        return CATEGORY_LAYOUT_INFOS

    @staticmethod
    def get_layout_offsets() -> LayoutOffsets:
        return LAYOUT_OFFSETS
    