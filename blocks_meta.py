
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
    LayoutBehaviour, RenderedSection, ImageType, AnimData, FrameInfo, LutInfo, Metadata, LayoutOffsets,
    Name, Lang,
    TILE_SIZE, SHEET_SCALE)

BLOCK_IMAGE_FOLDER_PATH = 'terraria_blocks'
RENDERED_SECTION_PATH = 'rendered_block_sections'


@unique
class BlockPattern(Enum):
    """How the blocks in a frame are organised"""
    DEFAULT = auto() # Used by most blocks such as dirt
    DEFAULT_BLEND = auto()
    CHECKER = auto() # Used for 2 frame non animated blocks
    SLAB = auto()    # Used for slabs and some plating
    LAYER = auto()
    BOULDER = auto()

@unique
class AnimationType(Enum):
    NONE = auto()
    # Change frame every x miliseconds
    BASIC = auto()
    # Rainbow moss and bricks, generate a hue shifted gif
    RAINBOW = auto()
    # Starry blocks
    STARRY = auto()
    LAVA_CLOUD = auto()
    RAINBOW_BOULDER = auto()

@dataclass(kw_only=True) # dataclass inheritance is weird without kw_only
class BlockAnimData(AnimData):
    type: AnimationType = AnimationType.NONE

@dataclass
class Block:
    tile_number: int
    name: Name
    pattern: BlockPattern = BlockPattern.DEFAULT
    anim: BlockAnimData = field(default_factory=lambda: BlockAnimData())

    def section_size(self) -> int:
        """Number of pixels that make up a final square"""
        match self.pattern:
            case BlockPattern.BOULDER:
                return 2
            case _:
                return 3

    def section_final_size(self) -> tuple[int, int]:
        match self.pattern:
            case BlockPattern.BOULDER:
                size_lut = BOULDER_SIZE_LUT[self.tile_number]
                return (size_lut[0][0] + size_lut[1][0],
                        size_lut[0][1] + size_lut[2][1] )
            case _:
                return (3 * TILE_SIZE, 3 * TILE_SIZE)
    
    def sanitised_name(self, lang: Lang) -> str:
        """Name with invalid path characters removed"""
        return self.name.get(lang).replace("\n", "")
    
@unique
class Category(Enum):
    SOIL = auto()
    DESERT = auto()
    COLD = auto()
    WOOD = auto()
    MISC = auto()
    STONE = auto()
    BRICKS = auto()
    TRADITIONAL = auto()
    GLASS = auto()
    TEAM_BLOCK = auto()
    ORES = auto()
    ORE_BRICK = auto()
    GEMSPARK = auto()
    LUNAR_BLOCK = auto()
    CATEGORY = auto()
    SLIME = auto()
    SPIKES = auto()
    SPIDER = auto()
    ANCIENT = auto()
    TECH = auto()
    BALLOON = auto()
    CLIMABLE = auto()
    COINS = auto()
    BOULDER = auto()
    # NEW = auto()


BLOCK_DICTIONARY: dict[Category, Sequence[Block]] = {
    Category.SOIL: (
        Block(0,   Name(en='Dirt')),
        Block(2,   Name(en='Grass')),
        Block(477, Name(en='Mowed Grass')),
        Block(23,  Name(en='Corrupt Grass')),
        Block(199, Name(en='Crimson Grass')),
        Block(109, Name(en='Hallowed Grass')),
        Block(492, Name(en='Mowed Hallowed Grass')),
        Block(40,  Name(en='Clay')),
        Block(59,  Name(en='Mud Block')),
        Block(60,  Name(en='Jungle Grass')),
        Block(70,  Name(en='Mushroom Grass')),
        Block(661, Name(en='Corrupt Jungle Grass')),
        Block(662, Name(en='Crimson Jungle Grass')),
        Block(57,  Name(en='Ash Block')),
        Block(633, Name(en='Ash Grass')),
        Block(123, Name(en='Silt Block')),
    ),
    Category.DESERT: (
        Block(53,  Name(en='Sand Block')),
        Block(397, Name(en='Hardened Sand Block')),
        Block(396, Name(en='Sandstone Block')),
        Block(479, Name(en='Smooth Sandstone')),
        Block(112, Name(en='Ebonsand Block')),
        Block(398, Name(en='Hardened Ebonsand Block')),
        Block(400, Name(en='Ebonsandstone Block')),
        Block(234, Name(en='Crimsand Block')),
        Block(399, Name(en='Hardened Crimsand Block')),
        Block(401, Name(en='Crimsandstone Block')),
        Block(116, Name(en='Pearlsand Block')),
        Block(402, Name(en='Hardened Pearlsand Block')),
        Block(403, Name(en='Pearlsandstone Block')),
        Block(404, Name(en='Desert Fossil')),
        Block(407, Name(en='Sturdy Fossil')),
    ),
    Category.COLD: (
        Block(147, Name(en='Snow Block')),
        Block(224, Name(en='Slush Block')),
        Block(161, Name(en='Ice Block')),
        Block(163, Name(en='Purple Ice')),
        Block(200, Name(en='Red Ice Block')),
        Block(164, Name(en='Pink Ice')),
        Block(162, Name(en='Thin Ice')),
        Block(127, Name(en='Magical Ice Block')),
    ),
    Category.WOOD: (
        Block(30,  Name(en='Wood')),
        Block(157, Name(en='Ebonwood')),
        Block(208, Name(en='Shadewood')),
        Block(159, Name(en='Pearlwood')),
        Block(321, Name(en='Boreal Wood')),
        Block(158, Name(en='Rich Mahogany')),
        Block(322, Name(en='Palm Wood')),
        Block(311, Name(en='Dynasty Wood')),
        Block(635, Name(en='Ash Wood')),
        Block(253, Name(en='Spooky Wood')),
        Block(191, Name(en='Living Wood')),
        Block(192, Name(en='Leaf Block')),
        Block(383, Name(en='Living Mahogany'), pattern=BlockPattern.CHECKER),
        Block(384, Name(en='Mahogany Leaf Block')),
        Block(562, Name(en='Bamboo')),
        Block(563, Name(en='Large Bamboo')),
        Block(741, Name(en='Pine Wood'), pattern=BlockPattern.CHECKER),
        Block(734, Name(en='Feywood')),
    ),
    
    Category.MISC: (
        Block(229, Name(en='Honey Block')),
        Block(230, Name(en='Crispy Honey Block')),
        Block(225, Name(en='Hive')),
        Block(145, Name(en='Candy Cane Block')),
        Block(146, Name(en='Green Candy Cane Block')),
        Block(170, Name(en='Pine Tree Block')),
        
        Block(189, Name(en='Cloud')),
        Block(196, Name(en='Rain Cloud')),
        Block(460, Name(en='Snow Cloud')),
        Block(719, Name(en='Rainbow Cloud'), pattern=BlockPattern.DEFAULT_BLEND, anim = BlockAnimData(
            type=AnimationType.STARRY, num_frames=14, frames_x=4, frames_y=4, frame_duration=100)),
        Block(718, Name(en='Star Cloud')),
        Block(717, Name(en='Lava Cloud'), anim = BlockAnimData(
            type=AnimationType.LAVA_CLOUD)),
        
        Block(195, Name(en='Flesh Block')),
        Block(474, Name(en='Lesion Block')),
        Block(666, Name(en='Poo Block')),
        Block(194, Name(en='Bone Block')),
        Block(251, Name(en='Pumpkin')),
        Block(252, Name(en='Hay')),
        Block(190, Name(en='Glowing Mushroom')),
        Block(188, Name(en='Cactus')),
        Block(315, Name(en='Coralstone Block')),
        Block(495, Name(en='Shell Pile')),
        Block(272, Name(en='Cog'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=2)),
        Block(198, Name(en='Asphalt Block')),
        Block(385, Name(en='Crystal Block')),
        Block(541, Name(en='Echo Block')),
        Block(496, Name(en='Anti-Portal Block')),
        Block(379, Name(en='Bubble'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(546, Name(en='Grate')),
        Block(641, Name(en='Reef Block')),
        Block(659, Name(en='Aetherium Block')),
        Block(748, Name(en='Aquarium Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=120)),
        Block(747, Name(en='Forbidden Block')),
        Block(746, Name(en='Office Block'), pattern=BlockPattern.CHECKER),
        Block(744, Name(en='Librarian Block')),
        Block(742, Name(en='Harpy Block'), pattern=BlockPattern.CHECKER),
        Block(739, Name(en='Jellyfish Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4, frame_duration=200
        )),
        Block(738, Name(en='Flinx Fur Block')),
        Block(737, Name(en='Gothic Brick'), pattern=BlockPattern.CHECKER),
        Block(736, Name(en='Easter Block'), pattern=BlockPattern.LAYER),
        Block(341, Name(en='Living Demon Fire Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(336, Name(en='Living Fire Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(343, Name(en='Living Ichor Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(340, Name(en='Living Cursed Fire Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(342, Name(en='Living Frost Fire Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(344, Name(en='Living Ultrabright Fire Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(351, Name(en='Smoke Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=3, frame_duration=80)),
    ),
    Category.STONE: (
        Block(1, Name(en='Stone')),
        Block(25, Name(en='Ebonstone')),
        Block(117, Name(en='Pearlstone Block')),
        Block(203, Name(en='Crimstone Block')),
        Block(367, Name(en='Marble Block')),
        Block(357, Name(en='Smooth Marble Block'), pattern=BlockPattern.CHECKER),
        Block(368, Name(en='Granite Block')),
        Block(369, Name(en='Smooth Granite Block')),
        Block(179, Name(en='Green Moss Stone')),
        Block(512, Name(en='Green Moss Gray Brick')),
        Block(180, Name(en='Brown Moss Stone')),
        Block(513, Name(en='Brown Moss Gray Brick')),
        Block(181, Name(en='Red Moss Stone')),
        Block(514, Name(en='Red Moss Gray Brick')),
        Block(182, Name(en='Blue Moss Stone')),
        Block(515, Name(en='Blue Moss Gray Brick')),
        Block(183, Name(en='Purple Moss Stone')),
        Block(516, Name(en='Purple Moss Gray Brick')),
        Block(381, Name(en='Lava Moss Stone')),
        Block(517, Name(en='Lava Moss Gray Brick')),
        Block(534, Name(en='Krypton Moss Stone')),
        Block(535, Name(en='Krypton Moss Gray Brick')),
        Block(536, Name(en='Xenon Moss Stone')),
        Block(537, Name(en='Xenon Moss Gray Brick')),
        Block(539, Name(en='Argon Moss Stone')),
        Block(540, Name(en='Argon Moss Gray Brick')),
        Block(625, Name(en='Neon Moss Stone')),
        Block(626, Name(en='Neon Moss Gray Brick')),
        Block(627, Name(en='Helium Moss Stone'), anim=BlockAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=80)),
        Block(628, Name(en='Helium Moss Gray Brick'), anim=BlockAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=80)),
        Block(67,  Name(en='Amethyst Stone Block')),
        Block(66,  Name(en='Topaz Stone Block')),
        Block(63,  Name(en='Sapphire Stone Block')),
        Block(65,  Name(en='Emerald Stone Block')),
        Block(64,  Name(en='Ruby Stone Block')),
        Block(68,  Name(en='Diamond Stone Block')),
        Block(566, Name(en='Amber Stone Block')),
    ),
    Category.BRICKS: (
        Block(38,  Name(en='Gray Brick')),
        Block(273, Name(en='Stone (Accent) Slab'), pattern=BlockPattern.SLAB),
        Block(39,  Name(en='Red Brick')),
        Block(151, Name(en='Sandstone Brick')),
        Block(274, Name(en='Sandstone Slab'), pattern=BlockPattern.SLAB),
        Block(152, Name(en='Ebonstone Brick')),
        Block(478, Name(en='Crimstone Brick')),
        Block(118, Name(en='Pearlstone Brick')),
        Block(119, Name(en='Iridescent Brick')),
        Block(120, Name(en='Mud Brick')),
        Block(148, Name(en='Snow Brick')),
        Block(206, Name(en='Ice Brick')),
        Block(722, Name(en='Fallen Star Block')),
        Block(202, Name(en='Sunplate Block')),
        Block(743, Name(en='Moonplate Block'), pattern=BlockPattern.CHECKER),
        Block(160, Name(en='Rainbow Brick'), anim=BlockAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=80)),
        Block(41,  Name(en='Blue Brick')),
        Block(481, Name(en='Cracked Blue Brick')),
        Block(43,  Name(en='Green Brick')),
        Block(482, Name(en='Cracked Green Brick')),
        Block(44,  Name(en='Pink Brick')),
        Block(483, Name(en='Cracked Pink Brick')),
        Block(687, Name(en='Lava Moss Brick')),
        Block(688, Name(en='Argon Moss Brick')),
        Block(689, Name(en='Krypton Moss Brick')),
        Block(690, Name(en='Xenon Moss Brick')),
        Block(691, Name(en='Neon Moss Brick')),
        Block(692, Name(en='Helium Moss Brick'), anim=BlockAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=80)),
        Block(226, Name(en='Lihzahrd Brick')),
        Block(667, Name(en='Aetherium Brick')),
    ),
    Category.TRADITIONAL: (
        Block(156, Name(en='Gray Stucco')),
        Block(153, Name(en='Red Stucco')),
        Block(154, Name(en='Yellow Stucco')),
        Block(155, Name(en='Green Stucco')),
        Block(312, Name(en='Red Dynasty Shingles')),
        Block(313, Name(en='Blue Dynasty Shingles')),
    ),
    Category.GLASS: (
        Block(54,  Name(en='Glass')),
        Block(326, Name(en='Waterfall Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Block(327, Name(en='Lavafall Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=150)),
        Block(345, Name(en='Honeyfall Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=150)),
        Block(458, Name(en='Sandfall Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=200)),
        Block(708, Name(en='Shimmerfall Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=150)),
        Block(328, Name(en='Confetti Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Block(329, Name(en='Midnight Confetti Block'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Block(507, Name(en='Gold Starry Block'), anim=BlockAnimData(
            type=AnimationType.STARRY, num_frames=8, frame_duration=333)),
        Block(508, Name(en='Blue Starry Block'), anim=BlockAnimData(
            type=AnimationType.STARRY, num_frames=8, frame_duration=333)),
        Block(459, Name(en='Snowfall Wall'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
    ),
    Category.TEAM_BLOCK: (
        # Team blocks aren't animated but use frame offset to get the brighter block texture
        Block(426, Name(en='Red Team Block')),
        Block(430, Name(en='Green Team Block')),
        Block(431, Name(en='Blue Team Block')),
        Block(432, Name(en='Yellow Team Block')),
        Block(433, Name(en='Pink Team Block')),
        Block(434, Name(en='White Team Block')),
        
        Block(727, Name(en='Dull Red Team Block')),
        Block(728, Name(en='Dull Green Team Block')),
        Block(729, Name(en='Dull Blue Team Block')),
        Block(730, Name(en='Dull Yellow Team Block')),
        Block(731, Name(en='Dull Pink Team Block')),
        Block(732, Name(en='Dull White Team Block')),
    ),
    Category.ORES: (
        Block(7,   Name(en='Copper Ore')),
        Block(166, Name(en='Tin Ore')),
        Block(6,   Name(en='Iron Ore')),
        Block(167, Name(en='Lead Ore')),
        Block(9,   Name(en='Silver Ore')),
        Block(168, Name(en='Tungsten Ore')),
        Block(8,   Name(en='Gold Ore')),
        Block(169, Name(en='Platinum Ore')),
        Block(37,  Name(en='Meteorite')),
        Block(22,  Name(en='Demonite Ore')),
        Block(204, Name(en='Crimtane Ore')),
        Block(56,  Name(en='Obsidian')),
        Block(58,  Name(en='Hellstone')),
        Block(107, Name(en='Cobalt Ore')),
        Block(221, Name(en='Palladium Ore')),
        Block(108, Name(en='Mythril Ore')),
        Block(222, Name(en='Orichalcum Ore')),
        Block(111, Name(en='Adamantite Ore')),
        Block(223, Name(en='Titanium Ore')),
        Block(211, Name(en='Chlorophyte Ore')),
        Block(408, Name(en='Luminite')),
    ),
    Category.ORE_BRICK: (
        Block(47,  Name(en='Copper Brick')),
        Block(284, Name(en='Copper Plating'), pattern=BlockPattern.SLAB),
        Block(175, Name(en='Tin Brick')),
        Block(325, Name(en='Tin Plating'), pattern=BlockPattern.SLAB),
        Block(472, Name(en='Iron Brick')),
        Block(473, Name(en='Lead Brick')),
        Block(46,  Name(en='Silver Brick')),
        Block(176, Name(en='Tungsten Brick')),
        Block(45,  Name(en='Gold Brick')),
        Block(177, Name(en='Platinum Brick')),
        Block(370, Name(en='Meteorite Brick')),
        Block(140, Name(en='Demonite Brick')),
        Block(347, Name(en='Crimtane Brick')),
        Block(75,  Name(en='Obsidian Brick')),
        Block(76,  Name(en='Hellstone Brick')),
        Block(121, Name(en='Cobalt Brick')),
        Block(248, Name(en='Palladium Column')),
        Block(122, Name(en='Mythril Brick')),
        Block(249, Name(en='Bubblegum Block')),
        Block(150, Name(en='Adamantite Beam')),
        Block(250, Name(en='Titanstone Block')),
        Block(735, Name(en='Hallowed Brick'), pattern=BlockPattern.CHECKER),
        Block(346, Name(en='Chlorophyte Brick')),
        Block(348, Name(en='Shroomite Plating')),
        Block(350, Name(en='Martian Conduit Plating')),
        Block(409, Name(en='Luminite Brick'), pattern=BlockPattern.CHECKER),
        Block(669, Name(en='Lunar Rust Brick'), pattern=BlockPattern.CHECKER),
        Block(670, Name(en='Dark Celestial Brick'), pattern=BlockPattern.CHECKER),
        Block(671, Name(en='Astra Brick'), pattern=BlockPattern.CHECKER),
        Block(672, Name(en='Cosmic Ember Brick'), pattern=BlockPattern.CHECKER),
        Block(673, Name(en='Cryocore Brick'), pattern=BlockPattern.CHECKER),
        Block(674, Name(en='Mercury Brick'), pattern=BlockPattern.CHECKER),
        Block(675, Name(en='Star Royale Brick'), pattern=BlockPattern.CHECKER),
        Block(676, Name(en='Heavenforge Brick'), pattern=BlockPattern.CHECKER),
    ),
    Category.LUNAR_BLOCK: (
        Block(500, Name(en='Solar Brick')),
        Block(415, Name(en='Solar Fragment Block')),
        Block(416, Name(en='Vortex Fragment Block')),
        Block(501, Name(en='Vortex Brick')),
        Block(417, Name(en='Nebula Fragment Block')),
        Block(502, Name(en='Nebula Brick')),
        Block(418, Name(en='Stardust Fragment Block')),
        Block(503, Name(en='Stardust Brick')),
    ),
    Category.GEMSPARK: (
        Block(262, Name(en='Amethyst Gemspark Block')),
        Block(263, Name(en='Topaz Gemspark Block')),
        Block(264, Name(en='Sapphire Gemspark Block')),
        Block(265, Name(en='Emerald Gemspark Block')),
        Block(266, Name(en='Ruby Gemspark Block')),
        Block(267, Name(en='Diamond Gemspark Block')),
        Block(268, Name(en='Amber Gemspark Block')),
        Block(255, Name(en='Offline Amethyst Gemspark Block')),
        Block(256, Name(en='Offline Topaz Gemspark Block')),
        Block(257, Name(en='Offline Sapphire Gemspark Block')),
        Block(258, Name(en='Offline Emerald Gemspark Block')),
        Block(259, Name(en='Offline Ruby Gemspark Block')),
        Block(260, Name(en='Offline Diamond Gemspark Block')),
        Block(261, Name(en='Offline Amber Gemspark Block')),
    ),
    Category.SLIME: (
        Block(193, Name(en='Slime Block')),
        Block(197, Name(en='Frozen Slime Block')),
        Block(371, Name(en='Pink Slime Block')),
    ),
    Category.SPIKES: (
        Block(745, Name(en='Spike Block'), pattern=BlockPattern.CHECKER),
        Block(48,  Name(en='Spike')),
        Block(232, Name(en='Wooden Spike')),
        Block(750, Name(en='Sharp Spike Block')),
        Block(740, Name(en='Toybreaker Brick')),
    ),
    Category.SPIDER: (
        Block(51,  Name(en='Cobweb')),
        Block(498, Name(en='Spider Nest Block')),
    ),
    Category.ANCIENT: (
        Block(677, Name(en='Ancient Blue Brick')),
        Block(678, Name(en='Ancient Green Brick')),
        Block(679, Name(en='Ancient Pink Brick')),
        Block(680, Name(en='Ancient Gold Brick')),
        Block(681, Name(en='Ancient Silver Brick')),
        Block(682, Name(en='Ancient Copper Brick')),
        Block(683, Name(en='Ancient Obsidian Brick')),
        Block(684, Name(en='Ancient Hellstone Brick')),
        Block(685, Name(en='Ancient Cobalt Brick')),
        Block(686, Name(en='Ancient Mythril Brick')),
    ),
    Category.TECH: (
        Block(130, Name(en='Active Stone Block')),
        Block(131, Name(en='Inactive Stone Block')),
        Block(421, Name(en='Conveyor Belt (Clockwise)'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4, frame_duration=70)),
        Block(422, Name(en='Conveyor Belt\n(Counter Clockwise)'), anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4, frame_duration=70, is_reversed=True)),
    ),
    Category.BALLOON: (
        Block(446, Name(en='Silly Pink Balloon')),
        Block(447, Name(en='Silly Purple Balloon')),
        Block(448, Name(en='Silly Green Balloon')),
    ),
    Category.CLIMABLE: (
        Block(213, Name(en='Rope')),
        Block(214, Name(en='Chain')),
        Block(353, Name(en='Vine Rope')),
        Block(365, Name(en='Silk Rope')),
        Block(366, Name(en='Web Rope')),
        Block(449, Name(en='Blue Streamer')),
        Block(450, Name(en='Green Streamer')),
        Block(451, Name(en='Pink Streamer')),
    ),
    Category.COINS: (
        Block(330, Name(en='Copper Coin')),
        Block(331, Name(en='Silver Coin')),
        Block(332, Name(en='Gold Coin')),
        Block(333, Name(en='Platinum Coin')),
    ),
    # TODO improve boulder rendering and placement, rainbow boulder needs animation
    Category.BOULDER: (
        Block(749, Name(en='Boulder Block'), pattern=BlockPattern.CHECKER),
        Block(716, Name(en='Boulder'), pattern=BlockPattern.BOULDER),
        Block(664, Name(en='Bouncy Boulder'), pattern=BlockPattern.BOULDER),
        Block(715, Name(en='Ghoulder'), pattern=BlockPattern.BOULDER),
        Block(714, Name(en='Spider Boulder'), pattern=BlockPattern.BOULDER),
        Block(713, Name(en='Lava Boulder'), pattern=BlockPattern.BOULDER),
        Block(712, Name(en='Poo Boulder'), pattern=BlockPattern.BOULDER),
        Block(711, Name(en='Rainbow Boulder'), pattern=BlockPattern.BOULDER, anim=BlockAnimData(
            type=AnimationType.RAINBOW_BOULDER, num_frames=32, frame_duration=16)),
    ),
}


# ------ Image Lookup Tables ------ #

# Used for non-blending single frame blocks
DEFAULT_NO_BLEND_PATTERN_LUT = FrameInfo(
    info=LutInfo(
        tiles_x=18, tiles_y=5
    ),
    index_table=(
        ((0, 3), (2, 0), (1, 3),),
        ((0, 1), (2, 1), (4, 1),),
        ((0, 4), (2, 2), (1, 4),),
    )
)
DEFAULT_BLENDED_PATTERN_LUT = FrameInfo(
    info=LutInfo(
        tiles_x=16, tiles_y=15,
    ),
    index_table=DEFAULT_NO_BLEND_PATTERN_LUT.index_table,
)

# Used for non-blending non animated two frame blocks
CHECKER_NO_BLEND_PATTERN_LUT = FrameInfo(
    info=LutInfo(
        tiles_x=18, tiles_y=10,
    ),
    index_table=(
        ((0, 3), (2, 0), (1, 3),),
        ((0, 2), (1, 6), (4, 2),),
        ((0, 4), (2, 2), (1, 4),),
    )
)

# Used for non-blending non animated two frame blocks
LAYER_NO_BLEND_PATTERN_LUT = FrameInfo(
    info=LutInfo(
        tiles_x=18, tiles_y=10,
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
        tiles_x=18, tiles_y=10,
    ),
    index_table=(
        ((4, 3), (1, 0), (1, 3),),
        ((0, 1), (1, 6), (4, 1),),
        ((0, 4), (3, 2), (1, 4),),
    )
)

BOULDER_PATTERN_LUT = FrameInfo(
    info=LutInfo(
        tiles_x=2, tiles_y=2,
    ),
    index_table=(
        ((0, 0), (1, 0)),
        ((0, 1), (1, 1)),
    )
)

X88  = (8 * SHEET_SCALE, 8 * SHEET_SCALE)
X89 = (8 * SHEET_SCALE, 9 * SHEET_SCALE)
X98 = (9 * SHEET_SCALE, 8 * SHEET_SCALE)
X99 = (9 * SHEET_SCALE, 9 * SHEET_SCALE)
X810 = (8 * SHEET_SCALE, 10 * SHEET_SCALE)
X910 = (9 * SHEET_SCALE, 10 * SHEET_SCALE)
X1010 = (10 * SHEET_SCALE, 10 * SHEET_SCALE)

BOULDER_SIZE_LUT = {
    # Boulder
    716: (X88, X88, X89, X89),
    # Bouncy Boulder
    664: (X88, X88, X88, X88),
    # Ghoulder
    715: (X88, X88, X89, X89),
    # Spider Boulder
    714: (X88, X88, X89, X89),
    # Lava Boulder
    713: (X88, X88, X89, X89),
    # Poo Boulder
    712: (X88, X88, X89, X89),
    # Rainbow Boulder
    711: (X88, X98, X810, X910),
}


# ------LAYOUT------ #


@dataclass
class CategoryLayout:
    category: Category
    layout: LayoutBehaviour = LayoutBehaviour.ALTERNATING

CATEGORY_LAYOUT_INFOS = (
    (
        CategoryLayout(Category.SOIL),
        CategoryLayout(Category.DESERT),
        CategoryLayout(Category.COLD),
        CategoryLayout(Category.MISC),
    ),
    (
        CategoryLayout(Category.STONE),
        CategoryLayout(Category.BRICKS),
        CategoryLayout(Category.GEMSPARK),
    ),
    (
        CategoryLayout(Category.ORE_BRICK),
        CategoryLayout(Category.ORES),
        CategoryLayout(Category.LUNAR_BLOCK),
        CategoryLayout(Category.TRADITIONAL),
        CategoryLayout(Category.WOOD),
    ),
    (
        CategoryLayout(Category.ANCIENT),
        CategoryLayout(Category.GLASS),
        CategoryLayout(Category.TECH),
        CategoryLayout(Category.TEAM_BLOCK),
        CategoryLayout(Category.SLIME),
        CategoryLayout(Category.SPIDER),
        CategoryLayout(Category.BALLOON),
        CategoryLayout(Category.CLIMABLE),
        CategoryLayout(Category.COINS),
        CategoryLayout(Category.SPIKES),
        CategoryLayout(Category.BOULDER),
    )
)

LAYOUT_OFFSETS = LayoutOffsets()

def confetti_block_transparency_workaround(img: Image.Image) -> None:
    # Force confetti to have transparency
    # Since gif is a garbage format

    # Open image and access pixels
    pixels = img.load()
    if pixels is None:
        print("Could not find confetti block image file", file=sys.stderr)
        sys.exit(1)

    # If pixel is any of these colors, make them transparent
    key_colors = (
        (0x05, 0x0A, 0x0D, 0x4C),
        (0x05, 0x0A, 0x0D, 0x4D),
    )
    transparent_color = (0, 0, 0, 0)

    for y in range(img.size[1]):
        for x in range(img.size[0]):
            if any(pixels[x, y] == key_colors[k] for k in range(len(key_colors))):
                pixels[x, y] = transparent_color

TILE_IMG_PREPASS: dict[int, Callable[[Image.Image], None]] = {
    328: confetti_block_transparency_workaround,
}


def extract_tile(
        img: Image.Image, indices: tuple[int, int], num_frames_y: int, frame: int, info: LutInfo,
        tile_size: tuple[int, int] = (TILE_SIZE, TILE_SIZE)
    ) -> Image.Image:
    return image_manipulation.extract_tile_animated_border(
        img, indices, num_frames_y, frame,
        tile_size, info
    )

def render_block_default(img: Image.Image, block: Block, lut: FrameInfo) -> bytes:
    """Render a block to a base64 encoded png image"""
    tile_list: list[Image.Image] = []

    _, frames_y = data.fix_frame_dims(block.anim)

    for row in lut.index_table:
        for indices in row:
            tile = extract_tile(
                img, indices, frames_y, block.anim.frame_offset, lut.info)
            tile_list.append(tile)

    final_img = image_manipulation.image_grid(tile_list, block.section_size())
    byte_file = io.BytesIO()
    final_img.save(byte_file, format=ImageType.PNG.name)
    if data.DEBUG_SAVE_BLOCK_SECTIONS:
        final_img.save(f'{RENDERED_SECTION_PATH}/{block.tile_number} {block.sanitised_name(Lang.en)}.png')
    return b64encode(byte_file.getvalue())

def render_block_boulder(img: Image.Image, block: Block) -> bytes:
    """Render a block to a base64 encoded png image"""
    tile_list: list[Image.Image] = []

    lut_info = LutInfo(tiles_x=2, tiles_y=2)
    tile_sizes = BOULDER_SIZE_LUT[block.tile_number]
    x_size, y_size = block.section_final_size()
    
    for y in range(2):
        for x in range(2):
            indices = (x, y)
            tile = extract_tile(img, indices, 1, 0, lut_info, tile_sizes[x + y * 2])
            tile_list.append(tile)
    
    final_img = Image.new('RGBA', (x_size, y_size), color=(0, 0, 0, 0))

    next_col = tile_list[0].size[0]
    next_row = tile_list[0].size[1]

    final_img.paste(tile_list[0], (
        (0, 0)
    ))
    final_img.paste(tile_list[1], (
        (next_col, 0)
    ))
    final_img.paste(tile_list[2], (
        (0, next_row)
    ))
    final_img.paste(tile_list[3], (
        (next_col, next_row)
    ))

    byte_file = io.BytesIO()
    final_img.save(byte_file, format=ImageType.PNG.name)
    if data.DEBUG_SAVE_BLOCK_SECTIONS:
        final_img.save(f'{RENDERED_SECTION_PATH}/{block.tile_number} {block.sanitised_name(Lang.en)}.png')
    return b64encode(byte_file.getvalue())

def render_block_animated(img: Image.Image, block: Block, lut: FrameInfo) -> bytes:
    """Render an animated block to a base64 encoded gif image"""
    tile_list: list[Image.Image] = []
    
    frame_duration = block.anim.frame_duration

    _, frames_y = data.fix_frame_dims(block.anim)

    match block.anim.type:
        case AnimationType.BASIC:
            for f in range(block.anim.num_frames):
                tile_sequence = []
                for row in lut.index_table:
                    for index in row:
                        tile = extract_tile(img, index, frames_y, f, lut.info)
                        tile_sequence.append(tile)
                frame = image_manipulation.image_grid(tile_sequence, block.section_size())
                tile_list.append(frame)
                        
        case AnimationType.RAINBOW:
            img_mask = None
            try:
                # Try to get a rainbow image mask
                with Image.open(f"{BLOCK_IMAGE_FOLDER_PATH}/masks/Tiles_{block.tile_number}_mask.png") as mask_img:
                    img_mask = mask_img.copy()
            except FileNotFoundError:
                pass

            for f in range(block.anim.num_frames):
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

                frame = image_manipulation.image_grid(tile_sequence, block.section_size())
                shifted_frame = image_manipulation.image_hue_shift(frame, f / block.anim.num_frames)

                # Alpha blend if the tile has a mask
                if img_mask:
                    mask_frame = image_manipulation.image_grid(mask_sequence, block.section_size())
                    shifted_frame = image_manipulation.alpha_blend_img(frame, shifted_frame, mask_frame)

                shifted_frame.resize((32, 32))
                tile_list.append(shifted_frame)
                    
        case AnimationType.STARRY:
            # Starry block frames are duplicated, double speed to compensate
            frame_duration = block.anim.frame_duration // 2
            starry_night_anim_offset = [
                [12, 9, 6],
                [9, 6, 3],
                [6, 3, 0]]

            intermediate_frames = []
            num_intermediates = block.anim.num_frames * 2
            for f in range(num_intermediates):
                intermediate_frames.append([
                    [None, None, None],
                    [None, None, None],
                    [None, None, None],
                ])

            for f in range(block.anim.num_frames):
                for j, row in enumerate(lut.index_table):
                    for i, index in enumerate(row):
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
                frame = image_manipulation.image_grid(tile_sequence, block.section_size())
                tile_list.append(frame)

        case AnimationType.LAVA_CLOUD:
            # TODO correctly animate lava cloud
            return render_block_default(img, block, lut)

        case AnimationType.RAINBOW_BOULDER:
            # TODO correctly animate rainbow boulder
            return render_block_default(img, block, lut)

    if block.anim.is_reversed:
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
            f'{RENDERED_SECTION_PATH}/{block.tile_number} {block.sanitised_name(Lang.en)}.gif',
            save_all=True, append_images=tile_list, disposal=2, loop=0,
            duration=frame_duration,
            background=0, optimise=False, interlace=True
        )

    return b64encode(byte_file.getvalue())


class BlockMetadata(Metadata):

    @staticmethod
    def get_tile_dictionary() -> dict[Category, Sequence[Block]]:
        return BLOCK_DICTIONARY

    @staticmethod
    def get_category_layout_info() -> Sequence[Sequence[CategoryLayout]]:
        return CATEGORY_LAYOUT_INFOS
    
    @staticmethod
    def get_layout_offsets() -> LayoutOffsets:
        return LAYOUT_OFFSETS

    # ------ Workarounds ------ #

    @staticmethod
    def get_tile_img_prepasses() -> dict[int, Callable[[Image.Image], None]]:
        return TILE_IMG_PREPASS
    
    # ------ Getter api ------ #

    @staticmethod
    def get_template_and_lut(pattern: BlockPattern) -> FrameInfo:
        match pattern:
            case BlockPattern.DEFAULT:
                lut = DEFAULT_NO_BLEND_PATTERN_LUT
            case BlockPattern.DEFAULT_BLEND:
                lut = DEFAULT_BLENDED_PATTERN_LUT
            case BlockPattern.CHECKER:
                lut = CHECKER_NO_BLEND_PATTERN_LUT
            case BlockPattern.SLAB:
                lut = SLAB_PATTERN_LUT
            case BlockPattern.LAYER:
                lut = LAYER_NO_BLEND_PATTERN_LUT
            case BlockPattern.BOULDER:
                lut = BOULDER_PATTERN_LUT
        return lut

    @staticmethod
    def get_block_path(tile_number: int) -> str:
        return f"{BLOCK_IMAGE_FOLDER_PATH}/Tiles_{tile_number}.png"

    @staticmethod
    def image_folder_path() -> str:
        return BLOCK_IMAGE_FOLDER_PATH

    @staticmethod
    def rendered_image_folder_path() -> str:
        return RENDERED_SECTION_PATH
    
    # ------ Render api ------ #

    @staticmethod
    def render_block(img: Image.Image, block: Block, lut: FrameInfo) -> RenderedSection:
        
        if block.pattern == BlockPattern.BOULDER:
            render = RenderedSection(
                block.tile_number, ImageType.PNG,
                render_block_boulder(img, block))
        else:
            if block.anim.type == AnimationType.NONE:
                render = RenderedSection(
                    block.tile_number, ImageType.PNG,
                    render_block_default(img, block, lut))
            else:
                render = RenderedSection(
                    block.tile_number, ImageType.GIF,
                    render_block_animated(img, block, lut))
                
        return render