import os

class HitWall(Exception):
    pass

MAX_MANA = 1000
STARTING_HP = 100
ELEMENTAL_STARTING_HP = 20
ELEMENTAL_STARTING_SPELL_COUNT = 2

MANA_FROM_KILL = 500
MANA_FROM_ELEMENTAL_TO_PLAYER_KILL_RATIO = 1/2
MANA_FROM_ELEMENTAL_KILL = int(MANA_FROM_KILL * MANA_FROM_ELEMENTAL_TO_PLAYER_KILL_RATIO)
MANA_FROM_MANA_BLAST_KILL_MULTIPLIER = 1/2

INFUSION_HP_COST = 49
MANA_COSTS = {
  "fireball": 300,
  "boulder": 75,
  "wind": 50,
  "wave": 150,
  "lightning_bolt": 250,
  "life_drain": 75,
  "shockwave": 100,
  "ice_spikes": 125,
  "infusion": 500,
  "enhance": 100,
  "soul_search": 150,
  "per_shield_hp": 10,
  "invisibility": 160,
  "summon_elemental": 850,
  "hex": 300,
  "cripple": 100
} # mana blast uses all mana, shield uses a specified amount

ATTACK_DAMAGE = {
  "punch": 30,
  "slash": 15,
  "charge": 10, # for lvl 1, it get's quadratically stronger over time/distance
  "crash": 10,
  "fireball": 100, # before it's exploded
  "explosion_1": 60, # radius = 1
  "explosion_2": 35, # radius = 2
  "boulder": 60, # being hit by a boulder, gets multiplied by velocity
  "wind": 5,
  "wave": 30,
  "lightning_bolt": 75,
  "life_drain": 20,
  "ice_spike": 50,
  "shockwave_1": 50, # radius = 1
  "shockwave_2": 25, # radius = 2
  "shockwave_1_crit": 75, # critical attack 
  "shockwave_2_crit": 50,  #
  "avalanche": 25
}

DEATH_MESSAGES = {
    "punch": "got punched to death",
    "slash": "got slashed to death",
    "charge": "got rammed to death",
    "parry": lambda attack, source_name: f"tried to {attack} {source_name} but got parried and died",
    "crash": "died by crashing into a wall",
    "fireball": "was hit by a fireball and died",
    "explosion_1": "died in a firery explosion",
    "explosion_2": "went too close to an explosion and died",
    "boulder": "was crushed to death by a boulder",
    "wind": "was torn apart by fierce wind",
    "wave": "was hit by a wave and died",
    "lightning_bolt": "died from getting struck by lightning",
    "life_drain": "died from having their essence drained",
    "ice_spike": "was impaled by an emerging ice spike",
    "shockwave": "was dissintegrated by a shockwave",
    "mana_blast": "got pulverized by a blast of mana",
    "infusion": "was annihilated by their own dark magic",
    "avalanche": "was crushed by avalanche",
    "error": lambda error_message: f"died in a violent explosion. Their final words were: {error_message}"
}

BOT = {
  "coordinates": [None, None],
  "hp": STARTING_HP,
  "mana": 0,
  "velocity_x": 0,
  "velocity_y": 0,
  "shield": 0,
  "invisibility": 0,
  "hexed": None,
  "elemental_protocol": None,
  "visible_stats": {
    "name": None,
    "type": "bot",
    "orientation": None,
    "hp_sector": "very high", # possible values: very low, low, high, very high
    "shield_sector": "none", # possible values: none, weak, moderate, strong
    "previous_action": "",
    "infused": False,
    "enhancement": 0,
    "hybernation": 0,
    "is_meditating": False,
    "is_parrying": False,
    "stun": 0,
    "slowness": 0,
    "crippled": 0,
    "charge_progress": 0,
    "charge_destination": 0,
    "distance": None
  }
}

ELEMENTAL = {
    "hp": ELEMENTAL_STARTING_HP,
    "velocity_x": 0,
    "velocity_y": 0,
    "visible_stats": {
        "type": "elemental",
        "element": None, # possible values: fire, state.water, earth, wind, lightning, darkness
        "allegiance": None,
        "remaining_spell_count": None,
        "orientation": None,
        "hp_sector": "very high",
        "infused": False,
        "stun": 0,
        "slowness": 0,
        "crippled": 0,
        "distance": None
    }
}

PERIMETER = {
  "type": "perimeter",
  "distance": None
}

BOULDER = {
  "velocity_x": 0,
  "velocity_y": 0,
  "source_name": None,
  "visible_stats": {
    "type": "boulder",
    "infused": False,
    "crippled": 0,
    "distance": None,
  }
}

WATER = {
  "velocity_x": 0,
  "velocity_y": 0,
  "source_name": None,
  "visible_stats": {
    "type": "water",
    "infused": False,
    "crippled": 0,
    "distance": None,
  }
}

FIREBALL = {
  "velocity_x": 0,
  "velocity_y": 0,
  "source_name": None,
  "visible_stats": {
    "type": "fireball",
    "infused": False,
    "crippled": 0,
    "distance": None,
  }
}

ICE_SPIKE = {
    "time_remaining": None,
    "visible_stats": {
        "type": "ice_spike",
        "infused": False,
        "crippled": 0,
        "distance": None,
    }
}

ELEMENT_TO_SPELL = {
    "fire": "fireball",
    "earth": "shockwave",
    "water": "wave",
    "wind": "wind",
    "lightning": "lightning_bolt",
    "darkness": "life_drain",
    "ice": "ice_spike"
}

COMMANDS = ["move", "cast_spell", "meditate", "hybernate", "physical_attack"]
ACTIONS = COMMANDS + ["mana_blast", "shield"]
CARDINAL_DIRECTIONS = ["north", "east", "south", "west"]
CUSTOM_CARDINAL_DIRECTIONS = ["north", "south", "west", "east"]
SPELLS = ["fireball", "boulder", "wave", "wind", "lightning_bolt", "life_drain", "ice_spikes", "shockwave", "mana_blast", "shield", "infusion", "enhance", "soul_search", "invisibility", "summon_elemental", "hex", "cripple"]
PHYSICAL_ATTACKS = ["punch", "slash", "charge", "parry"]

SIDE_LENGTH = 20

CONFIRM_KILLS = True

# boolean values, but using 1 and 0 because quicker to edit
PAUSE_BETWEEN_TURNS = 0
PAUSE_BETWEEN_ROUNDS = 0
PLAYER_ONLINE = 0
DEBUG_MODE = 0
TEAM_MODE = 0
EASY_MODE = 1
EMPTY_MODE = 0
MAP_DISPLAYED = 0

START_OBSERVING = "R_bot" # only relevant if PLAYER_ONLINE = 0
STARTING_MAX_SHIELD = MAX_MANA // MANA_COSTS["per_shield_hp"]

TEAMS = [["A_bot", "F_bot", "H_bot", "J_bot", "L_bot", "M_bot", "N_bot", "Q_bot", "Player"], ["B_bot", "C_bot", "D_bot", "E_bot", "G_bot", "I_bot", "K_bot", "O_bot", "R_bot"]]

CHARGE_INTO_WATER_MULTIPLIER = 1/4
WAVE_START_VELOCITY = SIDE_LENGTH # idk, I want it to go to border

MANA_BLAST_AGAINST_ELEMENTAL_MULTIPLIER = 2
ELEMENTAL_DAMAGE_MULTIPLIER = 7/24

WIND_KNOCKBACK = 3

FIREBALL_START_VELOCITY = 4

ICE_SPIKE_STARTING_TIME = 3
ICE_SLOWNESS_TIME = 5

INVISIBILITY_TIME = 4

HEX_TIME = 5

ENHANCEMENT_TIME = 8

HYBERNATION_TIME = min(SIDE_LENGTH, 20) # to compansate for the fact that hybernation is more powerful on larger maps. max 20 turns because otherwise it wouldn't really be worth it

CRIPPLE_TIME = 7
CRIPPLE_TIME_FOR_HALF_DAMAGE = 3
CRIPPLE_EFFECT_ASYMPTOTE = 1/4

PLAYER_ONLINE_TEXT = ("online" if PLAYER_ONLINE else "offline") + ("_team" if TEAM_MODE else "_no_team")

AVALANCHE_START_MULTIPLIER = 1/2
AVALANCHE_STARTING_TIME = int(AVALANCHE_START_MULTIPLIER * SIDE_LENGTH**2)
AVALANCHE_START_TO_PERIODICITY_RATIO = 10
AVALANCHE_PERIODICITY = int(AVALANCHE_STARTING_TIME / AVALANCHE_START_TO_PERIODICITY_RATIO)

MAX_TIME = AVALANCHE_STARTING_TIME + SIDE_LENGTH/2 * AVALANCHE_PERIODICITY

BLANK_MEMORY_MAP = [[["_", float("inf")] for _ in range(SIDE_LENGTH)] for _ in range(SIDE_LENGTH)]
PURE_WHITE_LIGHTNESS_MAP = [[255] * SIDE_LENGTH] * SIDE_LENGTH

# Define the file name and path
FILE_NAME = "POFF_win_counts.txt"
FILE_PATH = os.path.join(os.path.dirname(__file__), FILE_NAME)

AI_NAME = "R_bot"

INPUT_SIZE = 21
HIDDEN_SIZE = 32
NUM_ACTIONS = len(ACTIONS)
NUM_ORIENT = len(CARDINAL_DIRECTIONS)