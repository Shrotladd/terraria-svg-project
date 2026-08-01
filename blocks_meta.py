
from typing import Any, Callable, Sequence
from abc import abstractmethod
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
    # RAINBOW_CLOUD = auto()
    RAINBOW_BOULDER = auto()

@dataclass(kw_only=True) # dataclass inheritance is weird without kw_only
class BlockAnimData(AnimData):
    type: AnimationType = AnimationType.NONE

@dataclass
class Block:
    tile_number: int
    name: str
    # category: Category
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
    
    def sanitised_name(self) -> str:
        """Name with invalid path characters removed"""
        return self.name.replace("\n", "")
    
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
        Block(0,   'Dirt'),
        Block(2,   'Grass'),
        Block(477, 'Mowed Grass'),
        Block(23,  'Corrupt Grass'),
        Block(199, 'Crimson Grass'),
        Block(109, 'Hallowed Grass'),
        Block(492, 'Mowed Hallowed Grass'),
        Block(40,  'Clay'),
        Block(59,  'Mud Block'),
        Block(60,  'Jungle Grass'),
        Block(70,  'Mushroom Grass'),
        Block(661, 'Corrupt Jungle Grass'),
        Block(662, 'Crimson Jungle Grass'),
        Block(57,  'Ash Block'),
        Block(633, 'Ash Grass'),
        Block(123, 'Silt Block'),
    ),
    Category.DESERT: (
        Block(53,  'Sand Block'),
        Block(397, 'Hardened Sand Block'),
        Block(396, 'Sandstone Block'),
        Block(479, 'Smooth Sandstone'),
        Block(112, 'Ebonsand Block'),
        Block(398, 'Hardened Ebonsand Block'),
        Block(400, 'Ebonsandstone Block'),
        Block(234, 'Crimsand Block'),
        Block(399, 'Hardened Crimsand Block'),
        Block(401, 'Crimsandstone Block'),
        Block(116, 'Pearlsand Block'),
        Block(402, 'Hardened Pearlsand Block'),
        Block(403, 'Pearlsandstone Block'),
        Block(404, 'Desert Fossil'),
        Block(407, 'Sturdy Fossil'),
    ),
    Category.COLD: (
        Block(147, 'Snow Block'),
        Block(224, 'Slush Block'),
        Block(161, 'Ice Block'),
        Block(163, 'Purple Ice'),
        Block(200, 'Red Ice Block'),
        Block(164, 'Pink Ice'),
        Block(162, 'Thin Ice'),
        Block(127, 'Magical Ice Block'),
    ),
    Category.WOOD: (
        Block(30,  'Wood'),
        Block(157, 'Ebonwood'),
        Block(208, 'Shadewood'),
        Block(159, 'Pearlwood'),
        Block(321, 'Boreal Wood'),
        Block(158, 'Rich Mahogany'),
        Block(322, 'Palm Wood'),
        Block(311, 'Dynasty Wood'),
        Block(635, 'Ash Wood'),
        Block(253, 'Spooky Wood'),
        Block(191, 'Living Wood'),
        Block(192, 'Leaf Block'),
        Block(383, 'Living Mahogany', pattern=BlockPattern.CHECKER),
        Block(384, 'Mahogany Leaf Block'),
        Block(562, 'Bamboo'),
        Block(563, 'Large Bamboo'),
        Block(741, 'Pine Wood', pattern=BlockPattern.CHECKER),
        Block(734, 'Feywood'),
    ),
    
    Category.MISC: (
        Block(229, 'Honey Block'),
        Block(230, 'Crispy Honey Block'),
        Block(225, 'Hive'),
        Block(145, 'Candy Cane Block'),
        Block(146, 'Green Candy Cane Block'),
        Block(170, 'Pine Tree Block'),
        
        Block(189, 'Cloud'),
        Block(196, 'Rain Cloud'),
        Block(460, 'Snow Cloud'),
        Block(719, 'Rainbow Cloud', pattern=BlockPattern.DEFAULT_BLEND, anim = BlockAnimData(
            type=AnimationType.STARRY, num_frames=14, frames_x=4, frames_y=4, frame_duration=100)),
        Block(718, 'Star Cloud'),
        Block(717, 'Lava Cloud', anim = BlockAnimData(
            type=AnimationType.LAVA_CLOUD)),
        
        Block(195, 'Flesh Block'),
        Block(474, 'Lesion Block'),
        Block(666, 'Poo Block'),
        Block(194, 'Bone Block'),
        Block(251, 'Pumpkin'),
        Block(252, 'Hay'),
        Block(190, 'Glowing Mushroom'),
        Block(188, 'Cactus'),
        Block(315, 'Coralstone Block'),
        Block(495, 'Shell Pile'),
        Block(272, 'Cog', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=2)),
        Block(198, 'Asphalt Block'),
        Block(385, 'Crystal Block'),
        Block(541, 'Echo Block'),
        Block(496, 'Anti-Portal Block'),
        Block(379, 'Bubble', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(546, 'Grate'),
        Block(641, 'Reef Block'),
        Block(659, 'Aetherium Block'),
        Block(748, 'Aquarium Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=120)),
        Block(747, 'Forbidden Block'),
        Block(746, 'Office Block', pattern=BlockPattern.CHECKER),
        Block(744, 'Librarian Block'),
        Block(742, 'Harpy Block', pattern=BlockPattern.CHECKER),
        Block(739, 'Jellyfish Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4, frame_duration=200
        )),
        Block(738, 'Flinx Fur Block'),
        Block(737, 'Gothic Brick', pattern=BlockPattern.CHECKER),
        Block(736, 'Easter Block', pattern=BlockPattern.LAYER),
        Block(341, 'Living Demon Fire Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(336, 'Living Fire Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(343, 'Living Ichor Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(340, 'Living Cursed Fire Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(342, 'Living Frost Fire Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(344, 'Living Ultrabright Fire Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4)),
        Block(351, 'Smoke Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=3, frame_duration=80)),
    ),
    Category.STONE: (
        Block(1, 'Stone'),
        Block(25, 'Ebonstone'),
        Block(117, 'Pearlstone Block'),
        Block(203, 'Crimstone Block'),
        Block(367, 'Marble Block'),
        Block(357, 'Smooth Marble Block', pattern=BlockPattern.CHECKER),
        Block(368, 'Granite Block'),
        Block(369, 'Smooth Granite Block'),
        Block(179, 'Green Moss Stone'),
        Block(512, 'Green Moss Gray Brick'),
        Block(180, 'Brown Moss Stone'),
        Block(513, 'Brown Moss Gray Brick'),
        Block(181, 'Red Moss Stone'),
        Block(514, 'Red Moss Gray Brick'),
        Block(182, 'Blue Moss Stone'),
        Block(515, 'Blue Moss Gray Brick'),
        Block(183, 'Purple Moss Stone'),
        Block(516, 'Purple Moss Gray Brick'),
        Block(381, 'Lava Moss Stone'),
        Block(517, 'Lava Moss Gray Brick'),
        Block(534, 'Krypton Moss Stone'),
        Block(535, 'Krypton Moss Gray Brick'),
        Block(536, 'Xenon Moss Stone'),
        Block(537, 'Xenon Moss Gray Brick'),
        Block(539, 'Argon Moss Stone'),
        Block(540, 'Argon Moss Gray Brick'),
        Block(625, 'Neon Moss Stone'),
        Block(626, 'Neon Moss Gray Brick'),
        Block(627, 'Helium Moss Stone', anim=BlockAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=80)),
        Block(628, 'Helium Moss Gray Brick', anim=BlockAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=80)),
        Block(67,  'Amethyst Stone Block'),
        Block(66,  'Topaz Stone Block'),
        Block(63,  'Sapphire Stone Block'),
        Block(65,  'Emerald Stone Block'),
        Block(64,  'Ruby Stone Block'),
        Block(68,  'Diamond Stone Block'),
        Block(566, 'Amber Stone Block'),
    ),
    Category.BRICKS: (
        Block(38, 'Gray Brick'),
        Block(273, 'Stone (Accent) Slab', pattern=BlockPattern.SLAB),
        Block(39, 'Red Brick'),
        Block(151, 'Sandstone Brick'),
        Block(274, 'Sandstone Slab', pattern=BlockPattern.SLAB),
        Block(152, 'Ebonstone Brick'),
        Block(478, 'Crimstone Brick'),
        Block(118, 'Pearlstone Brick'),
        Block(119, 'Iridescent Brick'),
        Block(120, 'Mud Brick'),
        Block(148, 'Snow Brick'),
        Block(206, 'Ice Brick'),
        Block(722, 'Fallen Star Block'),
        Block(202, 'Sunplate Block'),
        Block(743, 'Moonplate Block', pattern=BlockPattern.CHECKER),
        Block(160, 'Rainbow Brick', anim=BlockAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=80)),
        Block(41, 'Blue Brick'),
        Block(481, 'Cracked Blue Brick'),
        Block(43, 'Green Brick'),
        Block(482, 'Cracked Green Brick'),
        Block(44, 'Pink Brick'),
        Block(483, 'Cracked Pink Brick'),
        Block(687, 'Lava Moss Brick'),
        Block(688, 'Argon Moss Brick'),
        Block(689, 'Krypton Moss Brick'),
        Block(690, 'Xenon Moss Brick'),
        Block(691, 'Neon Moss Brick'),
        Block(692, 'Helium Moss Brick', anim=BlockAnimData(
            type=AnimationType.RAINBOW, num_frames=64, frame_duration=80)),
        Block(226, 'Lihzahrd Brick'),
        Block(667, 'Aetherium Brick'),
    ),
    Category.TRADITIONAL: (
        Block(156, 'Gray Stucco'),
        Block(153, 'Red Stucco'),
        Block(154, 'Yellow Stucco'),
        Block(155, 'Green Stucco'),
        Block(312, 'Red Dynasty Shingles'),
        Block(313, 'Blue Dynasty Shingles'),
    ),
    Category.GLASS: (
        Block(54,  'Glass'),
        Block(326, 'Waterfall Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Block(327, 'Lavafall Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=150)),
        Block(345, 'Honeyfall Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=150)),
        Block(458, 'Sandfall Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=200)),
        Block(708, 'Shimmerfall Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=150)),
        Block(328, 'Confetti Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Block(329, 'Midnight Confetti Block', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
        Block(507, 'Gold Starry Block', anim=BlockAnimData(
            type=AnimationType.STARRY, num_frames=8, frame_duration=333)),
        Block(508, 'Blue Starry Block', anim=BlockAnimData(
            type=AnimationType.STARRY, num_frames=8, frame_duration=333)),
        Block(459, 'Snowfall Wall', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=8, frame_duration=80)),
    ),
    Category.TEAM_BLOCK: (
        # Team blocks aren't animated but use frame offset to get the brighter block texture
        Block(426, 'Red Team Block'), #anim=BlockAnimData(num_frames=2, frame_offset=1)),
        Block(430, 'Green Team Block'), #anim=BlockAnimData(num_frames=2, frame_offset=1)),
        Block(431, 'Blue Team Block'), #anim=BlockAnimData(num_frames=2, frame_offset=1)),
        Block(432, 'Yellow Team Block'), #anim=BlockAnimData(num_frames=2, frame_offset=1)),
        Block(433, 'Pink Team Block'), #anim=BlockAnimData(num_frames=2, frame_offset=1)),
        Block(434, 'White Team Block'), #anim=BlockAnimData(num_frames=2, frame_offset=1)),
        
        Block(727, 'Dull Red Team Block'),
        Block(728, 'Dull Green Team Block'),
        Block(729, 'Dull Blue Team Block'),
        Block(730, 'Dull Yellow Team Block'),
        Block(731, 'Dull Pink Team Block'),
        Block(732, 'Dull White Team Block'),
    ),
    Category.ORES: (
        Block(7,   'Copper Ore'),
        Block(166, 'Tin Ore'),
        Block(6,   'Iron Ore'),
        Block(167, 'Lead Ore'),
        Block(9,   'Silver Ore'),
        Block(168, 'Tungsten Ore'),
        Block(8,   'Gold Ore'),
        Block(169, 'Platinum Ore'),
        Block(37,  'Meteorite'),
        Block(22,  'Demonite Ore'),
        Block(204, 'Crimtane Ore'),
        Block(56,  'Obsidian'),
        Block(58,  'Hellstone'),
        Block(107, 'Cobalt Ore'),
        Block(221, 'Palladium Ore'),
        Block(108, 'Mythril Ore'),
        Block(222, 'Orichalcum Ore'),
        Block(111, 'Adamantite Ore'),
        Block(223, 'Titanium Ore'),
        Block(211, 'Chlorophyte Ore'),
        Block(408, 'Luminite'),
    ),
    Category.ORE_BRICK: (
        Block(47, 'Copper Brick'),
        Block(284, 'Copper Plating', pattern=BlockPattern.SLAB),
        Block(175, 'Tin Brick'),
        Block(325, 'Tin Plating', pattern=BlockPattern.SLAB),
        Block(472, 'Iron Brick'),
        Block(473, 'Lead Brick'),
        Block(46, 'Silver Brick'),
        Block(176, 'Tungsten Brick'),
        Block(45, 'Gold Brick'),
        Block(177, 'Platinum Brick'),
        Block(370, 'Meteorite Brick'),
        Block(140, 'Demonite Brick'),
        Block(347, 'Crimtane Brick'),
        Block(75, 'Obsidian Brick'),
        Block(76, 'Hellstone Brick'),
        Block(121, 'Cobalt Brick'),
        Block(248, 'Palladium Column'),
        Block(122, 'Mythril Brick'),
        Block(249, 'Bubblegum Block'),
        Block(150, 'Adamantite Beam'),
        Block(250, 'Titanstone Block'),
        Block(735, 'Hallowed Brick', pattern=BlockPattern.CHECKER),
        Block(346, 'Chlorophyte Brick'),
        Block(348, 'Shroomite Plating'),
        Block(350, 'Martian Conduit Plating'),
        Block(409, 'Luminite Brick', pattern=BlockPattern.CHECKER),
        Block(669, 'Lunar Rust Brick', pattern=BlockPattern.CHECKER),
        Block(670, 'Dark Celestial Brick', pattern=BlockPattern.CHECKER),
        Block(671, 'Astra Brick', pattern=BlockPattern.CHECKER),
        Block(672, 'Cosmic Ember Brick', pattern=BlockPattern.CHECKER),
        Block(673, 'Cryocore Brick', pattern=BlockPattern.CHECKER),
        Block(674, 'Mercury Brick', pattern=BlockPattern.CHECKER),
        Block(675, 'Star Royale Brick', pattern=BlockPattern.CHECKER),
        Block(676, 'Heavenforge Brick', pattern=BlockPattern.CHECKER),
    ),
    Category.LUNAR_BLOCK: (
        Block(500, 'Solar Brick'),
        Block(415, 'Solar Fragment Block'),
        Block(416, 'Vortex Fragment Block'),
        Block(501, 'Vortex Brick'),
        Block(417, 'Nebula Fragment Block'),
        Block(502, 'Nebula Brick'),
        Block(418, 'Stardust Fragment Block'),
        Block(503, 'Stardust Brick'),
    ),
    Category.GEMSPARK: (
        Block(262, 'Amethyst Gemspark Block'),
        Block(263, 'Topaz Gemspark Block'),
        Block(264, 'Sapphire Gemspark Block'),
        Block(265, 'Emerald Gemspark Block'),
        Block(266, 'Ruby Gemspark Block'),
        Block(267, 'Diamond Gemspark Block'),
        Block(268, 'Amber Gemspark Block'),
        Block(255, 'Offline Amethyst Gemspark Block'),
        Block(256, 'Offline Topaz Gemspark Block'),
        Block(257, 'Offline Sapphire Gemspark Block'),
        Block(258, 'Offline Emerald Gemspark Block'),
        Block(259, 'Offline Ruby Gemspark Block'),
        Block(260, 'Offline Diamond Gemspark Block'),
        Block(261, 'Offline Amber Gemspark Block'),
    ),
    Category.SLIME: (
        Block(193, 'Slime Block'),
        Block(197, 'Frozen Slime Block'),
        Block(371, 'Pink Slime Block'),
    ),
    Category.SPIKES: (
        Block(745, 'Spike Block', pattern=BlockPattern.CHECKER),
        Block(48, 'Spike'),
        Block(232, 'Wooden Spike'),
        Block(750, 'Sharp Spike Block'),
        Block(740, 'Toybreaker Brick'),
    ),
    Category.SPIDER: (
        Block(51, 'Cobweb'),
        Block(498, 'Spider Nest Block'),
    ),
    Category.ANCIENT: (
        Block(677, 'Ancient Blue Brick'),
        Block(678, 'Ancient Green Brick'),
        Block(679, 'Ancient Pink Brick'),
        Block(680, 'Ancient Gold Brick'),
        Block(681, 'Ancient Silver Brick'),
        Block(682, 'Ancient Copper Brick'),
        Block(683, 'Ancient Obsidian Brick'),
        Block(684, 'Ancient Hellstone Brick'),
        Block(685, 'Ancient Cobalt Brick'),
        Block(686, 'Ancient Mythril Brick'),
    ),
    Category.TECH: (
        Block(130, 'Active Stone Block'),
        Block(131, 'Inactive Stone Block'),
        Block(421, 'Conveyor Belt (Clockwise)', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4, frame_duration=70)),
        Block(422, 'Conveyor Belt\n(Counter Clockwise)', anim=BlockAnimData(
            type=AnimationType.BASIC, num_frames=4, frame_duration=70, is_reversed=True)),
    ),
    Category.BALLOON: (
        Block(446, 'Silly Pink Balloon'),
        Block(447, 'Silly Purple Balloon'),
        Block(448, 'Silly Green Balloon'),
    ),
    Category.CLIMABLE: (
        Block(213, 'Rope'),
        Block(214, 'Chain'),
        Block(353, 'Vine Rope'),
        Block(365, 'Silk Rope'),
        Block(366, 'Web Rope'),
        Block(449, 'Blue Streamer'),
        Block(450, 'Green Streamer'),
        Block(451, 'Pink Streamer'),
    ),
    Category.COINS: (
        Block(330, 'Copper Coin'),
        Block(331, 'Silver Coin'),
        Block(332, 'Gold Coin'),
        Block(333, 'Platinum Coin'),
    ),
    # TODO improve boulder rendering and placement, rainbow boulder needs animation
    Category.BOULDER: (
        Block(749, 'Boulder Block', pattern=BlockPattern.CHECKER),
        Block(716, 'Boulder', pattern=BlockPattern.BOULDER),
        Block(664, 'Bouncy Boulder', pattern=BlockPattern.BOULDER),
        Block(715, 'Ghoulder', pattern=BlockPattern.BOULDER),
        Block(714, 'Spider Boulder', pattern=BlockPattern.BOULDER),
        Block(713, 'Lava Boulder', pattern=BlockPattern.BOULDER),
        Block(712, 'Poo Boulder', pattern=BlockPattern.BOULDER),
        Block(711, 'Rainbow Boulder', pattern=BlockPattern.BOULDER, anim=BlockAnimData(
            type=AnimationType.RAINBOW_BOULDER, num_frames=32, frame_duration=16)),
    ),
}


# ------ Image Lookup Tables ------ #

# Used for non-blending single frame blocks
# DEFAULT_NO_BLEND_PATTERN_LUT = (
#     ((0, 3), (2, 0), (1, 3),),
#     ((0, 1), (2, 1), (4, 1),),
#     ((0, 4), (2, 2), (1, 4),),
# )
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
# CHECKER_NO_BLEND_PATTERN_LUT = (
#     ((0, 3), (2, 0), (1, 3),),
#     ((0, 2), (1, 6), (4, 2),),
#     ((0, 4), (2, 2), (1, 4),),
# )
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
# LAYER_NO_BLEND_PATTERN_LUT = (
#     ((0, 3), (1, 0), (1, 3),),
#     ((0, 1), (2, 1), (4, 1),),
#     ((0, 4), (1, 2), (1, 4),),
# )
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
# SLAB_PATTERN_LUT = (
#     ((4, 3), (1, 0), (1, 3),),
#     ((0, 1), (1, 6), (4, 1),),
#     ((0, 4), (3, 2), (1, 4),),
# )
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

# BOULDER_PATTERN_LUT = (
#     ((0, 0), (1, 0)),
#     ((0, 1), (1, 1)),
# )
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

@dataclass
class ColumnInfo:
    x_offset_to_next: int
    categories: Sequence[CategoryLayout]

CATEGORY_LAYOUT_INFOS = (
    ColumnInfo(x_offset_to_next=300, categories=(
        CategoryLayout(Category.SOIL),
        CategoryLayout(Category.DESERT),
        CategoryLayout(Category.COLD),
        CategoryLayout(Category.MISC),
    )),
    ColumnInfo(x_offset_to_next=350, categories=(
        CategoryLayout(Category.STONE),
        CategoryLayout(Category.BRICKS),
        CategoryLayout(Category.GEMSPARK),
    )),
    ColumnInfo(x_offset_to_next=300, categories=(
        CategoryLayout(Category.ORE_BRICK),
        CategoryLayout(Category.ORES),
        CategoryLayout(Category.LUNAR_BLOCK),
        CategoryLayout(Category.TRADITIONAL),
        CategoryLayout(Category.WOOD),
    )),
    ColumnInfo(x_offset_to_next=350, categories=(
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
        CategoryLayout(Category.BOULDER),#, layout=LayoutBehaviour.CENTER),
    )),
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
        final_img.save(f'{RENDERED_SECTION_PATH}/{block.tile_number} {block.sanitised_name()}.png')
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

    # print(block.name, x_size, y_size, next_col, next_row)

    byte_file = io.BytesIO()
    final_img.save(byte_file, format=ImageType.PNG.name)
    if data.DEBUG_SAVE_BLOCK_SECTIONS:
        final_img.save(f'{RENDERED_SECTION_PATH}/{block.tile_number} {block.sanitised_name()}.png')
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
                # frame.resize((32, 32))
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
            # starry_night_anim_offset = [
            #     [4, 3, 2],
            #     [3, 2, 1],
            #     [2, 1, 0]]
            # starry_night_anim_offset = [
            #     [6, 5, 4],
            #     [4, 3, 2],
            #     [2, 1, 0]]

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
            f'{RENDERED_SECTION_PATH}/{block.tile_number} {block.sanitised_name()}.gif',
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
    def get_category_layout_info() -> Sequence[ColumnInfo]:
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
    def get_template_and_lut(pattern: BlockPattern) -> FrameInfo: #tuple[Template, Lut]:
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