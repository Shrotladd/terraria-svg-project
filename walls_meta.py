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
    Name, Lang,
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
    name: Name
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
    
    def sanitised_name(self, lang: Lang) -> str:
        """Name with invalid path characters removed"""
        return self.name.get(lang).replace("\n", "")

BLOCK_DICTIONARY: dict[Category, Sequence[Wall]] = {
    Category.NATURAL: (
        Wall(16,  Name(en='Dirt Wall')),
        Wall(59,  Name(en='Rocky Dirt Wall')),
        Wall(170, Name(en='Cave Dirt Wall')),
        Wall(171, Name(en='Rough Dirt Wall')),
        Wall(196, Name(en='Layered Dirt Wall')),
        Wall(197, Name(en='Crumbling Dirt Wall')),
        Wall(198, Name(en='Cracked Dirt Wall')),
        Wall(199, Name(en='Wavy Dirt Wall')),
        Wall(15,  Name(en='Mud Wall')),
        Wall(205, Name(en='Leafy Jungle Wall')),
        Wall(207, Name(en='Jungle Vine Wall')),
        Wall(63,  Name(en='Grass Wall')),
        Wall(64,  Name(en='Jungle Wall')),
        Wall(65,  Name(en='Flower Wall')),
        Wall(69,  Name(en='Corrupt Grass Wall')),
        Wall(81,  Name(en='Crimson Grass Wall')),
        Wall(70,  Name(en='Hallowed Grass Wall')),
        Wall(40,  Name(en='Snow Wall')),
        Wall(71,  Name(en='Ice Wall')),
        Wall(74,  Name(en='Mushroom Wall')),
        Wall(80,  Name(en='Mushroom Wall\n(Natural)')),
        Wall(208, Name(en='Ember Wall')),
        Wall(209, Name(en='Cinder Wall')),
        Wall(210, Name(en='Magma Wall')),
        Wall(211, Name(en='Smouldering Stone Wall')),
        Wall(79,  Name(en='Obsidian Wall')),
    ),
    Category.WOOD: (
        Wall(4,   Name(en='Wood Wall')),
        Wall(42,  Name(en='Rich Mahogany Wall')),
        Wall(149, Name(en='Boreal Wood Wall')),
        Wall(312, Name(en='Bamboo Wall')),
        Wall(313, Name(en='Large Bamboo Wall')),
        Wall(151, Name(en='Palm Wood Wall')),
        Wall(316, Name(en='Ash Wood Wall')),
        Wall(41,  Name(en='Ebonwood Wall')),
        Wall(85,  Name(en='Shadewood Wall')),
        Wall(43,  Name(en='Pearlwood Wall')),
        Wall(115, Name(en='Spooky Wood Wall')),
        Wall(27,  Name(en='Planked Wall')),
        Wall(72,  Name(en='Cactus Wall')),
        Wall(106, Name(en='Wooden Fence')),
        Wall(139, Name(en='Rich Mahogany Fence')),
        Wall(150, Name(en='Boreal Wood Fence')),
        Wall(315, Name(en='Bamboo Fence')),
        Wall(152, Name(en='Palm Wood Fence')),
        Wall(317, Name(en='Ash Wood Fence')),
        Wall(138, Name(en='Ebonwood Fence')),
        Wall(141, Name(en='Shadewood Fence')),
        Wall(140, Name(en='Pearlwood Fence')),
        Wall(78,  Name(en='Living Wood Wall')),
        Wall(60,  Name(en='Living Leaf Wall')),
        Wall(358, Name(en='Pine Wood Wall'), pattern=WallPattern.CHECKER),
        Wall(353, Name(en='Pine Tree Wall')),
        Wall(351, Name(en='Feywood Wall')),
    ),
    Category.STONE2: (
        Wall(54,  Name(en='Green Mossy Wall')),
        Wall(55,  Name(en='Brown Mossy Wall')),
        Wall(56,  Name(en='Red Mossy Wall')),
        Wall(57,  Name(en='Blue Mossy Wall')),
        Wall(58,  Name(en='Purple Mossy Wall')),
    ),
    Category.STONE3: (
        Wall(48,  Name(en='Amethyst Stone Wall')),
        Wall(49,  Name(en='Topaz Stone Wall')),
        Wall(53,  Name(en='Diamond Stone Wall')),
        Wall(314, Name(en='Amber Stone Wall')),
        Wall(50,  Name(en='Sapphire Stone Wall')),
        Wall(51,  Name(en='Emerald Stone Wall')),
        Wall(52,  Name(en='Ruby Stone Wall')),
    ),
    Category.STONE: (
        Wall(1,   Name(en='Stone Wall')),
        Wall(61,  Name(en='Old Stone Wall')),
        Wall(185, Name(en='Craggy Stone Wall'), pattern=WallPattern.SLAB),
        Wall(204, Name(en='Lichen Stone Wall')),
        Wall(206, Name(en='Ivy Stone Wall')),
        Wall(212, Name(en='Worn Stone Wall')),
        Wall(213, Name(en='Stalactite Stone Wall')),
        Wall(214, Name(en='Mottled Stone Wall')),
        Wall(215, Name(en='Fractured Stone Wall')),
        Wall(319, Name(en='Reef Wall')),
        Wall(178, Name(en='Marble Wall')),
        Wall(179, Name(en='Smooth Marble Wall'), pattern=WallPattern.SLAB),
        Wall(180, Name(en='Granite Wall')),
        Wall(181, Name(en='Smooth Granite Wall')),
        Wall(3,   Name(en='Ebonstone Wall')),
        # Wall(246, 'Ebonstone Wall', 'category': 'ignore'},
        Wall(188, Name(en='Corrupt Growth Wall')),
        Wall(189, Name(en='Corrupt Mass Wall')),
        Wall(191, Name(en='Corrupt Tendril Wall')),
        Wall(190, Name(en='Corrupt Pustule Wall')),
        Wall(83,  Name(en='Crimstone Wall')),
        Wall(192, Name(en='Crimson Crust Wall')),
        Wall(193, Name(en='Crimson Scab Wall')),
        Wall(194, Name(en='Crimson Teeth Wall')),
        Wall(195, Name(en='Crimson Blister Wall')),
        Wall(233, Name(en='Lesion Block Wall')),
        Wall(236, Name(en='Spider Nest Wall')),
        Wall(28,  Name(en='Pearlstone Wall')),
        Wall(201, Name(en='Hallowed Cavern Wall')),
        Wall(200, Name(en='Hallowed Prism Wall')),
        Wall(202, Name(en='Hallowed Shard Wall')),
        Wall(203, Name(en='Hallowed Crystalline Wall')),
        Wall(186, Name(en='Crystal Block Wall')),
        Wall(321, Name(en='Aetherium Wall')),
        Wall(322, Name(en='Aetherium Brick Wall')),
    ),
    Category.MISC_BRICK: (
        Wall(147, Name(en='Stone Slab Wall'), pattern=WallPattern.SLAB),
        Wall(6,   Name(en='Red Brick Wall')),
        Wall(5,   Name(en='Gray Brick Wall')),
        Wall(31,  Name(en='Snow Brick Wall')),
        Wall(84,  Name(en='Ice Brick Wall')),
        Wall(44,  Name(en='Rainbow Brick Wall'), anim=WallAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=60)),
        Wall(34,  Name(en='Sandstone Brick Wall')),
        Wall(35,  Name(en='Ebonstone Brick Wall')),
        Wall(234, Name(en='Crimstone Brick Wall')),
        Wall(24,  Name(en='Mudstone Brick Wall')),
        Wall(82,  Name(en='Disc Wall')),
        Wall(348, Name(en='Fall Star Wall')),
        Wall(360, Name(en='Crescent Wall')),
        Wall(14,  Name(en='Obsidian Brick Wall')),
        Wall(23,  Name(en='Iridescent Brick Wall')),
        Wall(13,  Name(en='Hellstone Brick Wall')),
        Wall(22,  Name(en='Pearlstone Brick Wall')),
        Wall(87,  Name(en='Lihzahrd Brick Wall')),
        Wall(341, Name(en='Lava Moss Brick Wall')),
        Wall(342, Name(en='Argon Moss Brick Wall')),
        Wall(343, Name(en='Krypton Moss Brick Wall')),
        Wall(344, Name(en='Xenon Moss Brick Wall')),
        Wall(345, Name(en='Neon Moss Brick Wall')),
        Wall(346, Name(en='Helium Moss Brick Wall'), anim = WallAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=60)),
    ),
    Category.SAND: (
        Wall(187, Name(en='Sandstone Wall')),
        Wall(235, Name(en='Smooth Sandstone Wall')),
        Wall(216, Name(en='Hardened Sand Wall')),
        Wall(223, Name(en='Desert Fossil Wall')),
        Wall(220, Name(en='Ebonsandstone Wall')),
        Wall(217, Name(en='Hardened Ebonsand Wall')),
        Wall(221, Name(en='Crimsandstone Wall')),
        Wall(218, Name(en='Hardened Crimsand Wall')),
        Wall(222, Name(en='Pearlsandstone Wall')),
        Wall(219, Name(en='Hardened Pearlsand Wall')),
    ),
    Category.TRADITIONAL: (
        Wall(39,  Name(en='Gray Stucco Wall')),
        Wall(36,  Name(en='Red Stucco Wall')),
        Wall(37,  Name(en='Yellow Stucco Wall')),
        Wall(38,  Name(en='Green Stucco Wall')),
        Wall(142, Name(en='White Dynasty Wall')),
        Wall(143, Name(en='Blue Dynasty Wall')),
    ),
    Category.MISC: (
        Wall(29,  Name(en='Candy Cane Wall')),
        Wall(30,  Name(en='Green Candy Cane Wall')),
        Wall(62,  Name(en='Spider Wall')),
        Wall(66,  Name(en='Grass Wall')),
        Wall(67,  Name(en='Jungle Wall')),
        Wall(68,  Name(en='Flower Wall')),
        Wall(73,  Name(en='Cloud Wall')),
        Wall(75,  Name(en='Bone Block Wall')),
        Wall(76,  Name(en='Slime Block Wall')),
        Wall(77,  Name(en='Flesh Block Wall')),
        Wall(86,  Name(en='Hive Wall')),
        Wall(113, Name(en='Pumpkin Wall')),
        Wall(114, Name(en='Hay Wall')),
        Wall(225, Name(en='Cog Wall'), anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=2, frame_duration=100)),
        Wall(228, Name(en='Silly Pink Balloon Wall')),
        Wall(229, Name(en='Silly Purple Balloon Wall')),
        Wall(230, Name(en='Silly Green Balloon Wall')),
        Wall(318, Name(en='Echo Wall')),
        Wall(320, Name(en='Poo Wall')),
        Wall(363, Name(en='Office Wall'), pattern=WallPattern.CHECKER),
        Wall(366, Name(en='Boulder Wall'), pattern=WallPattern.CHECKER),
        Wall(359, Name(en='Harpy Wall'), pattern=WallPattern.CHECKER),
        Wall(362, Name(en='Spike Wall'), pattern=WallPattern.CHECKER),
        Wall(354, Name(en='Easter Wall'), pattern=WallPattern.LAYER),
        Wall(357, Name(en='Jellyfish Wall'), anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=100,
        )),
        Wall(365, Name(en='Aquarium Wall'), anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=130,
        )),
        Wall(355, Name(en='Gothic Brick Wall'), pattern=WallPattern.CHECKER),
        Wall(364, Name(en='Forbidden Wall')),
        Wall(361, Name(en='Librarian Wall')),
        Wall(356, Name(en='Flinx Fur Wall')),
    ),
    Category.GLASS: (
        Wall(21,  Name(en='Glass Wall')),
        Wall(88,  Name(en='Purple Stained Glass')),
        Wall(92,  Name(en='Red Stained Glass')),
        Wall(241, Name(en='Orange Stained Glass')),
        Wall(89,  Name(en='Yellow Stained Glass')),
        Wall(91,  Name(en='Green Stained Glass')),
        Wall(90,  Name(en='Blue Stained Glass')),
        Wall(93,  Name(en='Multicolored Stained\nGlass')),
        Wall(136, Name(en='Waterfall Wall'), anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Wall(137, Name(en='Lavafall Wall'), anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=200)),
        Wall(172, Name(en='Honeyfall Wall'), anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=200)),
        Wall(226, Name(en='Sandfall Wall'), anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=200)),
        Wall(347, Name(en='Shimmerfall Wall'), anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=150,
        )),
        Wall(227, Name(en='Snowfall Wall'), anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Wall(168, Name(en='Confetti Wall'), anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Wall(169, Name(en='Midnight Confetti Wall'), anim=WallAnimData(type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Wall(242, Name(en='Gold Starry Wall'), anim=WallAnimData(type=AnimationType.STARRY, num_frames=8, frame_duration=300)),
        Wall(243, Name(en='Blue Starry Wall'), anim=WallAnimData(type=AnimationType.STARRY, num_frames=8, frame_duration=300)),
    ),
    Category.METAL: (
        Wall(12,  Name(en='Copper Brick Wall')),
        Wall(146, Name(en='Copper Plating Wall'), pattern=WallPattern.SLAB),
        Wall(45,  Name(en='Tin Brick Wall')),
        Wall(167, Name(en='Tin Plating Wall'), pattern=WallPattern.SLAB),
        Wall(231, Name(en='Iron Brick Wall')),
        Wall(145, Name(en='Iron Fence')),
        Wall(245, Name(en='Wrought Iron Fence')),
        Wall(232, Name(en='Lead Brick Wall')),
        Wall(107, Name(en='Lead Fence')),
        Wall(11,  Name(en='Silver Brick Wall')),
        Wall(46,  Name(en='Tungsten Brick Wall')),
        Wall(10,  Name(en='Gold Brick Wall')),
        Wall(47,  Name(en='Platinum Brick Wall')),
        Wall(33,  Name(en='Demonite Brick Wall')),
        Wall(174, Name(en='Crimtane Brick Wall')),
        Wall(182, Name(en='Meteorite Brick Wall')),
        Wall(177, Name(en='Hellstone Brick Wall')),
        Wall(25,  Name(en='Cobalt Brick Wall')),
        Wall(109, Name(en='Palladium Column Wall')),
        Wall(26,  Name(en='Mythril Brick Wall')),
        Wall(110, Name(en='Bubblegum Block Wall')),
        Wall(32,  Name(en='Adamantite Beam Wall')),
        Wall(111, Name(en='Titanstone Block Wall')),
        Wall(352, Name(en="Hallowed Brick Wall")),
        Wall(173, Name(en='Chlorophyte Brick Wall')),
        Wall(175, Name(en='Shroomite Plating Wall')),
        Wall(237, Name(en='Solar Brick Wall')),
        Wall(238, Name(en='Vortex Brick Wall')),
        Wall(239, Name(en='Nebula Brick Wall')),
        Wall(240, Name(en='Stardust Brick Wall')),
        Wall(176, Name(en='Martian Conduit Wall')),
        Wall(224, Name(en='Luminite Brick Wall'), pattern=WallPattern.CHECKER),
        Wall(323, Name(en='Lunar Rust Brick Wall'), pattern=WallPattern.CHECKER),
        Wall(324, Name(en='Dark Celestial Brick Wall'), pattern=WallPattern.CHECKER),
        Wall(325, Name(en='Astra Brick Wall'), pattern=WallPattern.CHECKER),
        Wall(326, Name(en='Cosmic Ember Brick Wall'), pattern=WallPattern.CHECKER),
        Wall(327, Name(en='Cryocore Brick Wall'), pattern=WallPattern.CHECKER),
        Wall(328, Name(en='Mercury Brick Wall'), pattern=WallPattern.CHECKER),
        Wall(329, Name(en='Star Royal Brick Wall'), pattern=WallPattern.CHECKER),
        Wall(330, Name(en='Heavenforge Brick Wall'), pattern=WallPattern.CHECKER),
    ),
    Category.GEMSPARK: (
        Wall(154, Name(en='Amethyst Gemspark Wall')),
        Wall(166, Name(en='Topaz Gemspark Wall')),
        Wall(165, Name(en='Sapphire Gemspark Wall')),
        Wall(156, Name(en='Emerald Gemspark Wall')),
        Wall(164, Name(en='Ruby Gemspark Wall')),
        Wall(155, Name(en='Diamond Gemspark Wall')),
        Wall(153, Name(en='Amber Gemspark Wall')),
        Wall(158, Name(en='Offline Amethyst\nGemspark Wall')),
        Wall(163, Name(en='Offline Topaz\nGemspark Wall')),
        Wall(162, Name(en='Offline Sapphire\nGemspark Wall')),
        Wall(160, Name(en='Offline Emerald\nGemspark Wall')),
        Wall(161, Name(en='Offline Ruby\nGemspark Wall')),
        Wall(159, Name(en='Offline Diamond\nGemspark Wall')),
        Wall(157, Name(en='Offline Amber\nGemspark Wall')),
    ),
    Category.WALLPAPER: (
        Wall(116, Name(en='Christmas Tree Wallpaper')),
        Wall(117, Name(en='Ornament Wallpaper')),
        Wall(118, Name(en='Candy Cane Wallpaper')),
        Wall(119, Name(en='Festive Wallpaper')),
        Wall(120, Name(en='Stars Wallpaper')),
        Wall(121, Name(en='Squiggles Wallpaper')),
        Wall(122, Name(en='Snowflake Wallpaper')),
        Wall(123, Name(en='Krampus Horn Wallpaper')),
        Wall(124, Name(en='Bluegreen Wallpaper')),
        Wall(125, Name(en='Grinch Finger Wallpaper')),
        Wall(126, Name(en='Fancy Gray Wallpaper')),
        Wall(127, Name(en='Ice Floe Wallpaper')),
        Wall(128, Name(en='Music Wallpaper')),
        Wall(129, Name(en='Purple Rain Wallpaper')),
        Wall(130, Name(en='Rainbow Wallpaper')),
        Wall(131, Name(en='Sparkle Stone Wallpaper')),
        Wall(132, Name(en='Starlit Heaven Wallpaper')),
        Wall(133, Name(en='Bubble Wallpaper')),
        Wall(134, Name(en='Copper Pipe Wallpaper')),
        Wall(135, Name(en='Ducky Wallpaper')),
        Wall(144, Name(en='Rune Wallpaper'), anim=WallAnimData(
            type=AnimationType.BASIC, num_frames=9, frame_duration=80, repeat_last=10, bounce=True)),
        Wall(148, Name(en='Sail')),
    ),
    Category.ANCIENT: (
        Wall(331, Name(en='Ancient Blue Brick\nWall')),
        Wall(333, Name(en='Ancient Pink Brick\nWall')),
        Wall(332, Name(en='Ancient Green Brick\nWall')),
        Wall(334, Name(en='Ancient Gold Brick\nWall')),
        Wall(335, Name(en='Ancient Silver Brick\nWall')),
        Wall(336, Name(en='Ancient Copper Brick\nWall')),
        Wall(337, Name(en='Ancient Obsidian Brick\nWall')),
        Wall(338, Name(en='Ancient Hellstone Brick\nWall')),
        Wall(339, Name(en='Ancient Cobalt Brick\nWall')),
        Wall(340, Name(en='Ancient Mythril Brick\nWall')),
    ),
    Category.DUNGEON: (
        Wall(7,  Name(en='Blue Brick Wall')),
        Wall(94, Name(en='Blue Slab Wall')),
        Wall(95, Name(en='Blue Tiled Wall')),
        Wall(9,  Name(en='Pink Brick Wall')),
        Wall(96, Name(en='Pink Slab Wall')),
        Wall(97, Name(en='Pink Tiled Wall')),
        Wall(8,  Name(en='Green Brick Wall')),
        Wall(98, Name(en='Green Slab Wall')),
        Wall(99, Name(en='Green Tiled Wall')),
    ),
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
        final_img.save(f'{RENDERED_SECTION_PATH}/{wall.tile_number} {wall.sanitised_name(Lang.en)}.png')
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
            f'{RENDERED_SECTION_PATH}/{wall.tile_number} {wall.sanitised_name(Lang.en)}.gif',
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
                lut = DEFAULT_NO_BLEND_PATTERN_LUT
            case WallPattern.CHECKER:
                lut = CHECKER_NO_BLEND_PATTERN_LUT
            case WallPattern.SLAB:
                lut = SLAB_PATTERN_LUT
            case WallPattern.LAYER:
                lut = LAYER_NO_BLEND_PATTERN_LUT
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
    