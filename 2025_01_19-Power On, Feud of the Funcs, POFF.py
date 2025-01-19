# TODO: physical_attack charge
# TODO: reward for kills
# TODO: fix elemental x avalanche issue

from copy import deepcopy
import os
from time import perf_counter
import random
from math import ceil
import itertools
import matplotlib.pyplot as plt

# Define the file name and path
file_name = "POFF_win_counts.txt"
file_path = os.path.join(os.path.expanduser("~"), "Documents", file_name)

# Check if the file exists
if os.path.exists(file_path):
    # If the file exists, read its contents into a string
    with open(file_path, "r") as file:
        contents = file.read()
        win_counts_data = contents.split(",")
    print("exists")
else:
    # If the file doesn't exist, create it
    with open(file_path, "w") as file:
        contents = "" # Create an empty file
        win_counts_data = None
    print("does not exist")
if win_counts_data is not None:
    win_counts = {}
    for player in win_counts_data:
        win_counts[player[0]] = int(player[1:])

MAX_MANA = 1000
STARTING_HP = 100
ELEMENTAL_STARTING_HP = 50
ELEMENTAL_STARTING_SPELL_COUNT = 2

INFUSION_HP_COST = 49
MANA_COSTS = {
  "fireball": 300,
  "boulder": 75,
  "wind": 50,
  "wave": 150,
  "lightning_bolt": 250,
  "life_drain": 75,
  "shockwave": 100,
  "infusion": 500,
  "enhance": 100,
  "soul_search": 150,
  "per_shield_hp": 10,
  "invisibility": 100,
  "summon_elemental": 550,
  "hex": 300
} # mana blast uses all mana, shield uses a specified amount

ATTACK_DAMAGE = {
  "punch": 30,
  "slash": 15,
  "crash": 10,
  "fireball": 100, # before it's exploded
  "explosion_1": 60, # radius = 1
  "explosion_2": 35, # radius = 2
  "boulder": 60, # being hit by a boulder, gets multiplied by velocity
  "wind": 5,
  "wave": 30,
  "lightning_bolt": 75,
  "life_drain": 20,
  "shockwave_1": 50, # radius = 1
  "shockwave_2": 25, # radius = 2
  "shockwave_1_crit": 75, # critical attack 
  "shockwave_2_crit": 50,  #
  "avalanche": 25
}

DEATH_MESSAGES = {
    "punch": "got punched to death",
    "slash": "got slashed to death",
    "crash": "died by crashing into a wall",
    "fireball": "was hit by a fireball and died",
    "explosion_1": "died in a firery explosion",
    "explosion_2": "went too close to an explosion and died",
    "boulder": "was crushed to death by a boulder",
    "wind": "was torn apart by fierce wind",
    "wave": "was hit by a wave and died",
    "lightning_bolt": "died from getting struck by lightning",
    "life_drain": "died from having their essence drained",
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
  "buisness_card": {
    "name": None,
    "type": "bot",
    "orientation": None,
    "hp_sector": "very high", # possible values: very low, low, high, very high
    "shield_sector": "none", # possible values: none, weak, moderate, strong
    "last_movement": "",
    "infused": False,
    "enhancement": 0,
    "hybernation": 0,
    "is_meditating": False,
    "stun": 0,
    "distance": None
  }
}

ELEMENTAL = {
    "hp": ELEMENTAL_STARTING_HP,
    "velocity_x": 0,
    "velocity_y": 0,
    "buisness_card": {
        "type": "elemental",
        "element": None, # possible values: fire, water, earth, wind, lightning, darkness
        "allegiance": None,
        "remaining_spell_count": None,
        "orientation": None,
        "hp_sector": "very high",
        "infused": False,
        "stun": 0,
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
  "buisness_card": {
    "type": "boulder",
    "infused": False,
    "distance": None,
  }
}

WATER = {
  "velocity_x": 0,
  "velocity_y": 0,
  "buisness_card": {
    "type": "water",
    "infused": False,
    "distance": None,
  }
}

FIREBALL = {
  "velocity_x": 0,
  "velocity_y": 0,
  "buisness_card": {
    "type": "fireball",
    "infused": False,
    "distance": None,
  }
}

COMMANDS = ["move", "cast_spell", "meditate", "hybernate",  "physical_attack"]
CARDINAL_DIRECTIONS = ["north", "east", "south", "west"]
SPELLS = ["fireball", "boulder", "wave", "wind", "lightning_bolt", "life_drain", "shockwave", "mana_blast", "shield", "infusion", "enhance", "soul_search", "invisibility", "summon_elemental", "hex"]
PHYSICAL_ATTACKS = ["punch", "slash"]

SIDE_LENGTH = 16

CONFIRM_KILLS = True

PAUSE_BETWEEN_TURNS = True
PAUSE_BETWEEN_ROUNDS = True
PLAYER_ONLINE = False

WIND_KNOCKBACK = 3
FIREBALL_START_VELOCITY = 4
WAVE_START_VELOCITY = SIDE_LENGTH # idk, I want it to go to border
HYBERNATION_TIME = 10
INVISIBILITY_TIME = 5
HEX_TIME = 3
ENHANCEMENT_TIME = 8

AVALANCHE_STARTING_TIME = SIDE_LENGTH**2 // 2
AVALANCHE_PERIODICITY = AVALANCHE_STARTING_TIME // 10

PLAYER_MEMORY_MAP_BLANK = [[["_", float("inf")] for _ in range(SIDE_LENGTH)] for _ in range(SIDE_LENGTH)]
PURE_WHITE_LIGHTNESS_MAP = [[255] * SIDE_LENGTH] * SIDE_LENGTH

def clear():
    """
    Clears the terminal screen.
    For Windows, uses the 'cls' command.
    For macOS and Linux, uses the 'clear' command.
    Requires: import os
    """
    # for windows
    if os.name == 'nt':
        os.system('cls')
    # for mac and linux (here, os.name is 'posix')
    else:
        os.system('clear')

def set_map(SIDE_LENGTH):
  board = []
  for _ in range(SIDE_LENGTH): # y
    board.append([])
    for _ in range(SIDE_LENGTH): # x
      board[-1].append("_")
  return board

def set_brightness(value, text):
    return f"\033[38;2;{int(value)};{int(value)};{int(value)}m{text}\033[0m"

def display_map(board, expected_character_count=1, lightness_map=deepcopy(PURE_WHITE_LIGHTNESS_MAP)):
  for y in range(SIDE_LENGTH):
    row = ""
    for x in range(SIDE_LENGTH):
      if board[y][x].isupper() and people[letters[board[y][x]]]["invisibility"]:
        row += f"\033[38;2;0;0;{lightness_map[y][x]}m{board[y][x]}\033[0m"
      elif board[y][x].isupper() and people[letters[board[y][x]]]["buisness_card"]["enhancement"]:
        row += f"\033[38;2;{lightness_map[y][x]};0;0\033[0m"
      else:
        row += set_brightness(lightness_map[y][x], str(board[y][x]))# + str(lightness_map[y][x])
      row += " " * (1 + expected_character_count - len(str(board[y][x])))
    print(row)

def display_info_message(info_message):
    """
    Displays the info message as a string on the terminal instead of a list.
    If it's a soul search, it shows the dictionary in organized form

    Args:
        info_message (list): The info message to be displayed.
    """
    if info_message[0] == "soul_search":
        organize("soul search", info_message[1])
    else:
        print(" ".join(info_message))

def opposite_orientation(orientation):
  """
  Returns the opposite orientation of the given orientation.

  Args:
    orientation (str): The orientation to be reversed.

  Returns:
    str: The opposite orientation of the given orientation.
  """
  if orientation == "north":
    return "south"
  elif orientation == "south":
    return "north"
  elif orientation == "east":
    return "west"
  elif orientation == "west":
    return "east"

def deltas(direction):
  if direction == "north":
    delta_y = -1
  elif direction == "south":
    delta_y = 1
  else:
    delta_y = 0

  if direction == "east":
    delta_x = 1
  elif direction == "west":
    delta_x = -1
  else:
    delta_x = 0
  return delta_x, delta_y

def retreat(current_orientation, coordinates, sideways=True):
    possible_directions = CARDINAL_DIRECTIONS.copy()

    if sideways:
        possible_directions.remove(current_orientation)
        possible_directions.remove(opposite_orientation(current_orientation))

    random.shuffle(possible_directions)

    if possible_directions[0] == "north" and coordinates[0] == 0:
        possible_directions.remove("north")
    if possible_directions[0] == "south" and coordinates[0] == SIDE_LENGTH - 1:
        possible_directions.remove("south")
    if possible_directions[0] == "west" and coordinates[1] == 0:
        possible_directions.remove("west")
    if possible_directions[0] == "east" and coordinates[1] == SIDE_LENGTH - 1:
        possible_directions.remove("east")

    return "move " + possible_directions[0] + " 2"

def displace(y, x, axis, direction):
    PLAYER_NAME = letters[board[y][x]]
    damage(PLAYER_NAME, ATTACK_DAMAGE["avalanche"], DEATH_MESSAGES["avalanche"])
    NEW_COORDINATES = [y + ((2*direction - 1)*(-1 if y < SIDE_LENGTH // 2 else 1) if axis else 0),
                       x + ((2*direction - 1)*(-1 if x < SIDE_LENGTH // 2 else 1) if 1-axis else 0)]
    if board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] == "_":
        pass
    elif board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] != board[NEW_COORDINATES[0]][NEW_COORDINATES[1]].lower():
        displace(NEW_COORDINATES[0], NEW_COORDINATES[1], axis, direction)
    elif board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] == "f":
        fireball_explode(NEW_COORDINATES[0], NEW_COORDINATES[1])
    elif board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] == "w":
        NEW_KEY = f"{NEW_COORDINATES[0]} {NEW_COORDINATES[1]}"
        del water[NEW_KEY]
        damage(PLAYER_NAME, ATTACK_DAMAGE["wave"], DEATH_MESSAGES["wave"], False, "water")
    elif board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] in ["b", "p"]:
        damage(PLAYER_NAME, people[PLAYER_NAME]["hp"]+people[PLAYER_NAME]["shield"], DEATH_MESSAGES["avalanche"])
    if people[PLAYER_NAME]["hp"] > 0:
        board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] = board[y][x]
        people[PLAYER_NAME]["coordinates"] = NEW_COORDINATES
    board[y][x] = "p"

def get_axis(deltas, inverse=False):
    return 0 if deltas[0 if not inverse else 1] else 1

def organize(title, dictionary, indentation=1, screen_length=200):
    """
    Displays the key-value pairs of the dictionary
    :param dictionary: dict - the dictionary you wish to see organized
    :return: None
    :raises: ValueError - if the provided dictionary is not a dictionary
    """
    print(f"\n{' '*4*(indentation-1)}{title}:")
    if type(dictionary) != dict:
        raise ValueError(f"Hey, thats not a dictionary! It's currently a {type(dictionary)}.")
    else:
        longest = 0
        for i in range(len(list(dictionary.keys()))):
            if len(str(list(dictionary.keys())[i])) > longest:
                longest = len(str(list(dictionary.keys())[i]))
        for i in range(len(list(dictionary.keys()))):
            KEY = list(dictionary.keys())[i]
            VALUE = dictionary[KEY]
            if type(VALUE) == dict:
                organize(KEY, VALUE, indentation+1, screen_length)
            else:
                MORE_THAN_ONE_LINE = len(" "*4*indentation+KEY+":"+" "*(longest+1-len(KEY))+str(VALUE)) > screen_length
                if MORE_THAN_ONE_LINE:
                    print("")
                print(" "*4*indentation+KEY+":"+" "*(longest+1-len(KEY))+str(VALUE))
                if MORE_THAN_ONE_LINE:
                    print("")

def int_convertable(string):
    try:
        int(string)
        return True
    except ValueError:
        return False

def get_target(coordinates, delta_x, delta_y, respect_invisibility=True, is_player=True):
    if is_player:
        player_memory_maps[player][coordinates[0]][coordinates[1]] = [player[0], 0]
    target_letter = "p"
    
    for square in range(coordinates[abs(delta_x)]+(delta_x+delta_y), SIDE_LENGTH if delta_x+delta_y == 1 else -1, (delta_x+delta_y)):
        target_letter = board[square if delta_y else coordinates[0]][square if delta_x else coordinates[1]]
        if is_player:
            player_memory_maps[player][square if delta_y else coordinates[0]][square if delta_x else coordinates[1]] = [target_letter, 0]
        
        if target_letter != "_":
            if target_letter.isupper():  # to check if there's a player there
                if respect_invisibility and people[letters[target_letter]]["invisibility"]:  # if said player is invisible
                    # pretends like there's nothing there
                    if is_player:
                        player_memory_maps[player][square if delta_y else coordinates[0]][square if delta_x else coordinates[1]] = ["_", 0]
                    continue
            break
        else:
            target_letter = "p"

    if target_letter in ["b", "w", "f", "e"]:
        KEY = f"{square if delta_y else people[player]['coordinates'][0]} {square if delta_x else people[player]['coordinates'][1]}"
        try:
            target = deepcopy((boulders if target_letter == "b" else water if target_letter == "w" else fireballs if target_letter == "f" else elementals)[KEY]["buisness_card"])
            target["distance"] = abs(coordinates[abs(delta_x)]-square)
            if target_letter == "e":
                target["hp_sector"] = ["very low", "low", "high", "very high"][min(elementals[KEY]["hp"] // (ELEMENTAL_STARTING_HP // 4), 3)]
        except KeyError:
            KEY_SPLITTED = list(map(int, KEY.split()))
            board[KEY_SPLITTED[0]][KEY_SPLITTED[1]] = "_"
            target_letter = "p"
    
    if target_letter == "p":
        square = -1 if delta_x+delta_y == -1+avalanche_progress[abs(delta_x)] else SIDE_LENGTH - avalanche_progress[abs(delta_x)]
        target = PERIMETER.copy()  # use deepcopy() if neccesary, although rn it isn't
        target["distance"] = abs(people[player]['coordinates'][abs(delta_x)]-square)
    elif target_letter not in ["b", "w", "f", "e"]:
        target = deepcopy(people[letters[target_letter]]["buisness_card"])
        target["distance"] = abs(people[player]['coordinates'][abs(delta_x)]-square)
        target["hp_sector"] = ["very low", "low", "high", "very high"][min(people[letters[target_letter]]["hp"] // (STARTING_HP // 4), 3)]
    
    return target

def A_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = [stats["hp"]]
    orientation = stats["buisness_card"]["orientation"]
    if target["type"] == "bot":
        if target["hp_sector"] == "very high" or stats["mana"] < MANA_COSTS["lightning_bolt"]:
            if stats["hp"]+stats["shield"] <= ATTACK_DAMAGE["lightning_bolt"] and stats["mana"] >= MANA_COSTS["boulder"]:
                action = "cast_spell boulder"
            elif stats["invisibility"] <= 7 and target["orientation"] != opposite_orientation(stats["buisness_card"]["orientation"]) and stats["mana"] >= MANA_COSTS["invisibility"]:
                action = "cast_spell invisibility"
            else:
                options = ["wave", "fireball", "wind", "lightning_bolt", "life_drain", "mana_blast", "boulder", "shockwave"]
                for option in options.copy():
                    TOO_FAR = target["distance"] >= 7
                    TOO_CLOSE = target["distance"] <= 3 and stats["hp"] <= ATTACK_DAMAGE["explosion_1"]
                    if option == "mana_blast":
                      if stats["mana"] // 10 - target["distance"] * 10 <= 0:
                        options.remove(option)
                    elif stats["mana"] <= MANA_COSTS[option]:
                        options.remove(option)
                    elif option == "fireball" and (TOO_FAR or TOO_CLOSE):
                        options.remove(option)
                    elif option == "boulder" and target["distance"] == 1:
                        options.remove(option)
                    elif option == "shockwave" and target["distance"] > 2:
                        options.remove(option)
                if options:
                    action = "cast_spell " + random.choice(options)
                elif target["distance"] == 1:
                    action = "physical_attack punch"
                else:
                    action = "move " + random.choice(CARDINAL_DIRECTIONS.copy()) + " 2"
        else:
            action = "cast_spell lightning_bolt"
    elif target["type"] == "elemental" and target["allegiance"] != stats["buisness_card"]["name"]:
        if stats["mana"] >= MANA_COSTS["lightning_bolt"]:
            action = "cast_spell lightning_bolt"
        else:
            action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
    elif target["type"] not in ["perimeter", "elemental"] and stats["mana"] >= MANA_COSTS["wind"] and target["distance"] * sum(deltas(stats["buisness_card"]["orientation"])) + stats["coordinates"][0 if deltas(stats["buisness_card"]["orientation"])[1] else 1] not in [0, SIDE_LENGTH - 1]:
        action = "cast_spell wind"
    elif target["type"] not in ["perimeter", "elemental"]:
        action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
    elif target["distance"] == 1:
        orientation = opposite_orientation(stats["buisness_card"]["orientation"])
        action = f"move {orientation} 2"
    elif stats["hp"] < memory[-1]:
        DIRECTIONS = [d for d in CARDINAL_DIRECTIONS.copy() if d != orientation]
        action = "move " + random.choice(DIRECTIONS) + " 1"
    elif not stats["mana"]:
        action = "hybernate"
    elif stats["mana"] < MAX_MANA / 2:
        action = "meditate"
    elif random.randint(0, 1):
        orientation = random.choice(CARDINAL_DIRECTIONS.copy())
        action = "move " + orientation + " 2"
    elif random.randint(0, 1) and stats["mana"] >= MANA_COSTS["summon_elemental"] and target["distance"] != 1:
        action = f"cast_spell summon_elemental {random.choice(list(ELEMENT_TO_SPELL.keys()))}"
    elif stats["mana"] < MAX_MANA and not random.randint(0, 9) and stats["mana"] >= MANA_COSTS["invisibility"]:
        action = "cast_spell invisibility"
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    else:
        action = "cast_spell mana_blast"
    memory.append(stats["hp"])
    return action, orientation, memory

def B_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = [target]
    COORDINATES_SENTERED = [stats["coordinates"][dimension] in [(SIDE_LENGTH - 1) // 2, (SIDE_LENGTH - 1) // 2 + 1] for dimension in [0, 1]]
    CUSTOM_CARDINAL_DIRECTIONS = ["north", "south", "west", "east"]
    orientation = random.choice(CARDINAL_DIRECTIONS.copy())

    if target["type"] in ["bot", "elemental"]:
        MAXIMUM_HP = (["very low", "low", "high", "very high"].index(target["hp_sector"]) + 1) * (25 if target["type"] == "bot" else 13)
        MAXIMUM_SHIELD = 0 if target["type"] == "elemental" else ["none", "weak", "moderate", "strong"].index(target["shield_sector"]) * 33 + (1 if target["shield_sector"] == "strong" else 0) # I could use 100/3 but I don't trust the decimal imprecicion
        REQUIRED_DAMAGE = MAXIMUM_HP + MAXIMUM_SHIELD
        if ATTACK_DAMAGE["lightning_bolt"] >= REQUIRED_DAMAGE and stats["mana"] >= MANA_COSTS["lightning_bolt"]:
            action = "cast_spell lightning_bolt"
        elif (stats["mana"] // 10 + 1 - target["distance"]) * 10 >= REQUIRED_DAMAGE:
            action = "cast_spell mana_blast"
        elif stats["mana"] >= MANA_COSTS["lightning_bolt"] * 2 and stats["hp"] > ATTACK_DAMAGE["lightning_bolt"] and REQUIRED_DAMAGE <= ATTACK_DAMAGE["lightning_bolt"] * 2:
            action = "cast_spell lightning_bolt"
        elif stats["mana"] >= MANA_COSTS["wave"]:
            action = "cast_spell wave"
        elif target["distance"] == 1 and REQUIRED_DAMAGE <= ATTACK_DAMAGE["punch"]:
            action = "physical_attack punch"
        elif stats["mana"] >= MANA_COSTS["wind"] and stats["hp"]+stats["shield"] > ATTACK_DAMAGE["lightning_bolt"]:
            action = "cast_spell wind"
        elif not stats["invisibility"] and stats["mana"] >= MANA_COSTS["invisibility"]:
            action = "cast_spell invisibility"
        elif stats["invisibility"] and stats["mana"] < MANA_COSTS["lightning_bolt"]:
            action = "meditate"
        else:
            action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
        orientation = stats["buisness_card"]["orientation"]
    elif target["type"] != "perimeter":
        if target["distance"] > 3 and stats["mana"] >= MANA_COSTS["wind"]:
           action = "cast_spell wind"
        else:
           action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
    elif not all(COORDINATES_SENTERED):
        action = "move "
        for axis in [0, 1]:
            if not COORDINATES_SENTERED[axis]:
                if stats["coordinates"][axis] < (SIDE_LENGTH - 1) // 2:
                    action += CUSTOM_CARDINAL_DIRECTIONS[1 + 2 * axis]
                elif stats["coordinates"][axis] > (SIDE_LENGTH - 1) // 2 + 1:
                    action += CUSTOM_CARDINAL_DIRECTIONS[0 + 2 * axis]
                else:
                    raise Exception(f"Something is wrong with B_bot_func, {stats}, {COORDINATES_SENTERED}")
                break
        action += " 2"
    elif random.randint(0, 1) and len(memory) >= 5 and all(memory[-i]["type"] != "bot" for i in range(1, 6)) and stats["shield"] < max_shield and stats["mana"] >= MANA_COSTS["per_shield_hp"] * (max_shield/4):
        action = "cast_spell shield"
    elif (memory[-1]["type"] == "bot" and (random.randint(0, 1) and memory[-2]["type"] == "bot")) and stats["mana"] >= min(MANA_COSTS["wave"], MANA_COSTS["fireball"]):
        possibilities = ["wave", "fireball"]
        random.shuffle(possibilities)
        for possibility in possibilities:
            if stats["mana"] >= MANA_COSTS[possibility]:
                action = f"cast_spell {possibility}"
                break
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    else:
        action = "cast_spell mana_blast"
    memory.append(target)
    return action, orientation, memory

def C_bot_func(stats, target, memory, info_messages):
  if not memory:
    memory = [random.choice(["north", "south"]), "", stats["coordinates"]]
  orientation = stats["buisness_card"]["orientation"]
  if target["type"] in ["bot", "elemental"] and stats["mana"] >= MANA_COSTS["lightning_bolt"]:
    action = "cast_spell lightning_bolt"
  elif stats["mana"] < MAX_MANA:
    action = "meditate"
  elif memory[-1] == stats["coordinates"] and memory[-2] == "move":
    action = "cast_spell mana_blast"
    orientation = "west" if memory[0] == "south" else "east"
  elif (stats["coordinates"][0] < SIDE_LENGTH - 1 - avalanche_progress[0]) if memory[0] == "south" else (stats["coordinates"][0] > avalanche_progress[0]):
    action = f"move {memory[0]} 2"
    orientation = "west" if memory[0] == "south" else "east"
  elif stats["coordinates"][1] < SIDE_LENGTH - 1 - avalanche_progress[1] if memory[0] == "south" else (stats["coordinates"][1] > avalanche_progress[1]):
    action = f"move {'east' if memory[0] == 'south' else 'west'} 2"
    orientation = "north" if memory[0] == "south" else "south"
  else:
    action = "cast_spell mana_blast"
  memory.append(action.split()[0])
  memory.append(stats["coordinates"])
  return action, orientation, memory

def D_bot_func(stats, target, memory, info_messages):
  if not memory:
     memory = [stats["shield"]]
  lock_orientation = False
  DELTAS = list(reversed(deltas(stats["buisness_card"]["orientation"])))
  if target["type"] in ["bot", "elemental"]:
    lock_orientation = True
    if stats["mana"] >= MANA_COSTS["lightning_bolt"]:
        action = "cast_spell lightning_bolt"
    elif target["distance"] == 1:
        action = "physical_attack punch"
    elif target["orientation"] != opposite_orientation(stats["buisness_card"]["orientation"]):
        action = "meditate"
    else:
        action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
  elif target["type"] != "perimeter" and target["distance"] * sum(DELTAS) + stats["coordinates"][0 if DELTAS[0] else 1] not in [avalanche_progress[0 if DELTAS[0] else 1], SIDE_LENGTH - 1 - avalanche_progress[0 if DELTAS[0] else 1]]:
    #print(f"d. DELTAS: {DELTAS}, coordinates: {stats['coordinates']}, sum(DELTAS): {sum(DELTAS)}), target: {target}") # debug
    if stats["mana"] >= MANA_COSTS["wind"]:
        action = "cast_spell wind"
    elif target["type"] == "boulder" and target["distance"] > 2:
        lock_orientation = True
        action = "meditate"
    else:
        action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
  elif stats["shield"] < memory[-1]:
    action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]), sideways=False)
  else:
    if stats["shield"] < max_shield and stats["mana"] >= MANA_COSTS["per_shield_hp"] and (random.randint(0, 1 if stats["mana"] < MAX_MANA / 4 else 2) or stats["mana"] > MAX_MANA / 2):
        action = "cast_spell shield"
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    elif random.randint(0, 1):
        action = "cast_spell mana_blast"
    elif random.randint(0, 1) and target["distance"] > 2:
        action = "cast_spell fireball"
    elif random.randint(0, 1) and target["distance"] > 1:
        action = "cast_spell wave"
    elif target["distance"] > 1:
        action = "cast_spell boulder"
    else:
        action = "cast_spell mana_blast"
  if lock_orientation:
    orientation = stats["buisness_card"]["orientation"]
  else:
     orientation = random.choice(CARDINAL_DIRECTIONS.copy())
  memory.append(stats["shield"])
  return action, orientation, memory 

def E_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = [random.choice(CARDINAL_DIRECTIONS.copy()), [stats, target, random.randint(0, 1)]]
    orientation = random.choice(CARDINAL_DIRECTIONS.copy())
    scan_direction = memory[-1][2]
    DELTAS = deltas(stats["buisness_card"]["orientation"])
    AXIS = get_axis(DELTAS, True)
    SIGN = DELTAS[0 if AXIS else 1]
    DIRECTION = memory[0]
    DIRECTION_DELTAS = deltas(DIRECTION)
    DIRECTION_AXIS = get_axis(DIRECTION_DELTAS, True)
    DIRECTION_SIGN = DIRECTION_DELTAS[0 if DIRECTION_AXIS else 1]
    SPARE_MANA = stats["mana"] - MANA_COSTS['lightning_bolt'] * 2
    if target["type"] in ["bot", "elemental"]:
        if stats["mana"] >= MANA_COSTS["lightning_bolt"]:
           action = "cast_spell lightning_bolt"
        elif stats["mana"] >= MANA_COSTS["wave"]:
           action = "cast_spell wave"
        elif target["distance"] == 1:
           action = "physical_attack punch"
        else:
           action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
        orientation = stats["buisness_card"]["orientation"]
    elif target["type"] != "perimeter":
        if target["type"] == "boulder" and target["distance"] * SIGN + stats["coordinates"][AXIS] == avalanche_progress[AXIS] if SIGN == -1 else SIDE_LENGTH - 1 - avalanche_progress[AXIS]:
            if stats["mana"] < MAX_MANA:
               action = "meditate"
            elif stats["shield"] < max_shield:
               action = "cast_spell shield"
            else:
               action = "cast_spell mana_blast"
        elif stats["mana"] >= MANA_COSTS["wind"]:
            action = "cast_spell wind"
        else:
            action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
    elif stats["mana"] < MANA_COSTS["lightning_bolt"]:
        action = "meditate"
    elif memory[-1][1]["type"] == "bot" and stats["mana"] >= MANA_COSTS["wave"]:
        action = "cast_spell wave"
    elif stats["coordinates"][DIRECTION_AXIS] != (avalanche_progress[DIRECTION_AXIS] if DIRECTION_SIGN == -1 else SIDE_LENGTH - 1 - avalanche_progress[DIRECTION_AXIS]):
        action = f"move {DIRECTION} 2"
        orientation = DIRECTION
    elif memory[-1][0]["hp"] < stats["hp"] or memory[-1][0]["shield"] < stats["shield"]:
        action = f"move {opposite_orientation(DIRECTION)} 2"
        memory[0] = opposite_orientation(DIRECTION)
        orientation = opposite_orientation(DIRECTION)
    elif SPARE_MANA < 0:
        action = "meditate"
    elif random.randint(0, 15):
        if DIRECTION_AXIS == 0:
           side_directions = ["west", "east"]
        elif DIRECTION_AXIS == 1:
           side_directions = ["north", "south"]
        else:
           raise Exception(f"Invalid axis, should be 0 or 1, is {DIRECTION_AXIS}")
        if stats["coordinates"][0 if DIRECTION_AXIS else 1] in (0, SIDE_LENGTH - 1):
            scan_direction = 0 if scan_direction else 1 # to toggle
        action = f"move {side_directions[scan_direction]} 1"
        orientation = opposite_orientation(DIRECTION)
    elif random.randint(0, 1) and stats["mana"] < MAX_MANA:
        action = "meditate"
        if random.randint(0, 1):
            other_directions = [d for d in CARDINAL_DIRECTIONS.copy() if d != opposite_orientation(DIRECTION)]
            orientation = random.choice(other_directions)
    elif random.randint(0, 1) and SPARE_MANA >= MANA_COSTS["per_shield_hp"] and stats["shield"] < max_shield:
        action = f"cast_spell shield {SPARE_MANA}"
    elif random.randint(0, 1) and stats["mana"] >= MANA_COSTS["fireball"]:
        action = "cast_spell fireball"
    elif random.randint(0, 1) and stats["mana"] >= MANA_COSTS["wave"]:
        action = "cast_spell wave"
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    elif stats["shield"] < max_shield:
        action = "cast_spell shield"
    else:
        action = "cast_spell mana_blast"
    memory.append([stats, target, scan_direction])
    return action, orientation, memory

def F_bot_get_orientation(stats, memory, default_orientation):
    if memory[-1] is not None:
        TARGET_COORDINATES = memory[-1][0]
        if stats["coordinates"] == TARGET_COORDINATES:
            if stats["buisness_card"]["orientation"] not in memory[-1][1]:
                memory[-1][1].append(stats["buisness_card"]["orientation"])
            if set(memory[-1][1]) == set(CARDINAL_DIRECTIONS):
                memory.append(None)
            else:
                remaining_orientations = set(CARDINAL_DIRECTIONS) - set(memory[-1][1])
                return random.choice(list(remaining_orientations)), memory
    return default_orientation, memory

def F_bot_func(stats, target, memory, info_messages):
    CUSTOM_CARDINAL_DIRECTIONS = ["north", "south", "west", "east"]
    orientation = random.choice(CARDINAL_DIRECTIONS)
    if not memory:
        INTERNAL_MAP_BLANK = [[float("inf") for _ in range(SIDE_LENGTH)] for _ in range(SIDE_LENGTH)]
        memory = [INTERNAL_MAP_BLANK.copy(), 0, deepcopy(stats), "", None]
    for row_index, row in enumerate(memory[0]):
        for column_index, _ in enumerate(row):
            memory[0][row_index][column_index] += 1
    delta_x, delta_y = deltas(stats["buisness_card"]["orientation"])
    for i in range(target["distance"]):
        memory[0][stats["coordinates"][0] + delta_y * i][stats["coordinates"][1] + delta_x * i] = 0

    if target["type"] == "bot":
        delta_x, delta_y = deltas(stats["buisness_card"]["orientation"])
        TARGET_COORDINATES = (stats["coordinates"][0] + delta_y * target["distance"], stats["coordinates"][1] + delta_x * target["distance"])
        if memory[-1] is None or memory[-1][0] != TARGET_COORDINATES:
            memory.append([TARGET_COORDINATES, [], target["name"]])
        if target["hp_sector"] != "very high" and stats["mana"] >= MANA_COSTS["lightning_bolt"]:
            action = "cast_spell lightning_bolt"
        elif not stats["invisibility"] and stats["mana"] >= MANA_COSTS["invisibility"] and target["orientation"] != opposite_orientation(stats["buisness_card"]["orientation"]):
            action = "cast_spell invisibility"
        elif stats["mana"] >= MANA_COSTS["fireball"]:
            action = "cast_spell fireball"
        elif stats["mana"] // 100 >= target["distance"]:
            action = "cast_spell mana_blast"
        elif stats["mana"] >= MANA_COSTS["wave"]:
            action = "cast_spell wave"
        elif target["distance"] == 1:
            action = "physical_attack punch"
        else:
            action = f"move {stats['buisness_card']['orientation']} 2"
        orientation = stats["buisness_card"]["orientation"]
    elif "soul_search" in [info_message[0] for info_message in info_messages]:
        SEARCH_INFO = [info_message[1] for info_message in info_messages if info_message[0] == "soul_search"][0]
        TARGET_COORDINATES = SEARCH_INFO["coordinates"]
        memory[-1] = [TARGET_COORDINATES, [], SEARCH_INFO]
        if stats["mana"] >= MANA_COSTS["enhance"]:
            action = "cast_spell enhance"
        else:
            action = "meditate"
    elif target["type"] != "perimeter":
        if target["distance"] > 3 and stats["mana"] >= MANA_COSTS["wind"] and random.randint(0, 1):
            action = "cast_spell wind"
        else:
            action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
            memory[-4] = 2
        orientation, memory = F_bot_get_orientation(stats, memory, orientation)
    elif memory[-1] is not None:
        TARGET_COORDINATES = memory[-1][0]
        if memory[-1][2] and memory[-1][2] in [info_message[0] for info_message in info_messages]:
            memory[-1][2] = ""
        if memory[-1][2] and TARGET_COORDINATES == (stats["coordinates"][0]+delta_y, stats["coordinates"][1]+delta_x):
            if stats["mana"] >= min(MANA_COSTS["wave"], MANA_COSTS["shockwave"]):
                options = ["wave", "shockwave"]
                for option in options.copy():
                    if stats["mana"] < MANA_COSTS[option]:
                        options.remove(option)
                action = "cast_spell " + random.choice(options)
            else:   
                action = "physical_attack slash"
        elif stats["coordinates"] == TARGET_COORDINATES:
            if stats["mana"] > MANA_COSTS["soul_search"] and stats["shield"] < max_shield and stats["mana"] > MANA_COSTS["per_shield_hp"] and not random.randint(0, 3):
                action = "cast_spell shield"
            elif stats["mana"] < MANA_COSTS["soul_search"] or (stats["mana"] < MAX_MANA and stats["shield"] >= max_shield):
                action = "meditate"
            else:
                action = "cast_spell "
                if stats["shield"] < max_shield and (random.randint(0, 1) or stats["mana"] % 100 != 0):
                    action += "shield"
                else:
                    action += "mana_blast"
                    #print(f"mana % 100: {stats['mana'] % 100}, mana: {stats['mana']}, max shield: {max_shield}, shield: {stats['shield']}") # debug
        elif memory[-2].split()[0] == "move" and memory[-3]["coordinates"] == stats["coordinates"]:
            if stats["mana"] >= 100:
                action = "cast_spell mana_blast"
            elif stats["mana"] >= MANA_COSTS["per_shield_hp"] and stats["shield"] < max_shield:
                action = "cast_spell shield"
            else:
                action = "meditate"
            orientation = memory[-2].split()[1]
        elif memory[-4]:
            if stats["mana"] >= MANA_COSTS["wave"]:
                action = "cast_spell wave"
            elif stats["mana"] >= MANA_COSTS["fireball"]:
                action = "cast_spell fireball"
            else:
                action = "meditate"
            orientation = stats["buisness_card"]["orientation"]
        else:    
            action = "move "
            for axis in [0, 1]:
                if stats["coordinates"][axis] != TARGET_COORDINATES[axis]:
                    if stats["coordinates"][axis] < TARGET_COORDINATES[axis]:
                        DIRECTION = CUSTOM_CARDINAL_DIRECTIONS[1 + 2 * axis]
                        action += DIRECTION
                    elif stats["coordinates"][axis] > TARGET_COORDINATES[axis]:
                        DIRECTION = CUSTOM_CARDINAL_DIRECTIONS[0 + 2 * axis]
                        action += DIRECTION
                    else:
                        raise Exception(f"Something is wrong with F_bot_func, {stats}, {TARGET_COORDINATES}")
                    DISTANCE = abs(stats["coordinates"][axis] - TARGET_COORDINATES[axis])
                    action += " " + str(DISTANCE) # we don't need to limit to 2 because that happens automatically
                    break
            if DISTANCE < 3:
                orientation = CARDINAL_DIRECTIONS[(CARDINAL_DIRECTIONS.index(action.split()[1])+1) % 4]
            else:
                orientation = DIRECTION
        orientation, memory = F_bot_get_orientation(stats, memory, orientation)
    elif stats["mana"] == MAX_MANA:
        if stats["shield"] < max_shield:
            action = "cast_spell shield"
        else:
            action = "cast_spell mana_blast"
    elif stats["mana"] >= MANA_COSTS["soul_search"]:
        action = "cast_spell soul_search"
        #print("f: soul search") # debug
    else:
        internal_map = memory[0] # purely for readability
        maximum_value = float("-inf")
        maximum_index = [0, 0]
        extremes = [[0, 0], [0, 0]]
        coordinates = [0, 0]
        for _ in range(3):
            for sign in [-1, 1]:
                for dimension in [0, 1]:
                    for value in range(coordinates[dimension] + sign, extremes[dimension][(sign+1)//2] +2*sign, sign):
                        coordinates[dimension] = value
                        if coordinates[0]+stats["coordinates"][0] >= 0 and coordinates[0]+stats["coordinates"][0] < SIDE_LENGTH and coordinates[1]+stats["coordinates"][1] >= 0 and coordinates[1]+stats["coordinates"][1] < SIDE_LENGTH:
                            LOCATION_VALUE = internal_map[coordinates[0]+stats["coordinates"][0]][coordinates[1]+stats["coordinates"][1]]
                            if LOCATION_VALUE > maximum_value:
                                maximum_value = LOCATION_VALUE
                                maximum_index = [coordinates[0]+stats["coordinates"][0], coordinates[1]+stats["coordinates"][1]].copy()
                    extremes[dimension][(sign+1)//2] = coordinates[dimension]
        memory[-1] = [tuple(maximum_index), [], ""]
        if stats["coordinates"][0] == 0:
           memory[-1][1].append("north")
        elif stats["coordinates"][0] == SIDE_LENGTH - 1:
           memory[-1][1].append("south")
        if stats["coordinates"][1] == 0:
           memory[-1][1].append("west")
        elif stats["coordinates"][1] == SIDE_LENGTH - 1:
           memory[-1][1].append("east")
        action = "meditate"
    if memory[-4] is not None and memory[-4] in range(3):
        memory[-4] -= 1 if memory[-4] else 0
    else:
        memory[-4] = 0
    memory[-3] = deepcopy(stats)
    memory[-2] = action
    #print(f"action: {action}, orientation: {orientation}") # debug
    #display_map(memory[0], 3) # debug
    return action, orientation, memory

def G_bot_func(stats, target, memory, info_messages):
    if not memory:
        y, x=stats["coordinates"]
        return "cast_spell shield 700", "north" if y<5 and y!=0 else ("south" if y>4 and y!=9 else ("west" if x<5 and x!=0 else "east")), {"time": 0, "objective": "flight", "hp": stats["hp"], "shield": stats["shield"]}
    VALUES={"init_shield": 700, "map": (SIDE_LENGTH - max(avalanche_progress)) // 2, "boulder": False} # edit: 5 -> (SIDE_LENGTH - max(avalanche_progress)) // 2. Sto originalt 5, men det tar verken hensyn til map størrelse eller skredet. 
    memory["time"]+=1
    coords=stats["coordinates"]

    if target["type"]=="bot":
        if target["distance"] <= 3:
            action="cast_spell fireball"
        if memory["time"]>5:
            action="cast_spell lightning" 
        else:
            action="cast_spell wave"

    if not coords[0]*(coords[0]-(VALUES["map"]*2-1))+coords[1]*(coords[1]-(VALUES["map"]*2-1)):
        memory["objective"]="freeze"

    if memory["objective"]=="freeze":
        #hp=memory["hp"]+memory["shield"]
        if target["type"]=="bot":
            action="cast_spell fireball" if target["distance"] <=2 else "cast_spell wave"

        elif target["distance"]==1:
            action="cast_spell wind"
        elif target["distance"]<6 and target["type"]!="wave":
            action="cast_spell wind"
        else:
            if stats["mana"]>(max_shield-stats["shield"])*10 and stats["shield"]<max_shield:
                action="cast_spell shield"
            elif stats["mana"]==1000:
                if not VALUES["boulder"]: # edit: drone -> boulder. Sto originalt drone, men det ga KeyError
                    action="cast_spell mana_blast"
                else:
                    action 
            elif stats["mana"]>900 and not target["type"] in ["boulder", "wave"] and VALUES["boulder"]:
                action="cast_spell boulder"
            else:
                action="meditate"
 
        orientation=list([["south", "north"][int(coords[0]/9)], ["east", "west"][int(coords[1]/9)]])
        if stats["buisness_card"]["orientation"] in orientation:
            orientation.remove(stats["buisness_card"]["orientation"])
        orientation=orientation[0]
    elif memory["objective"]=="flight":
        
        moves=list(["north", "west"][i] if stats["coordinates"][i]<VALUES["map"] else ["south", "east"][i] for i in [0, 1] if not stats["coordinates"][i] in (0, VALUES["map"]*2-1))
        #print(moves)

        
        if target["type"]=="perimeter":
            action=f"move {stats['buisness_card']['orientation']} 2"
            orientation=moves[-1]
        else:
            action="cast_spell wind" if target["distance"] <=2 else "cast_spell wave"
            orientation=moves[-1]
        
    memory["hp"]=stats["hp"]
    memory["shield"]=stats["shield"]
    #print(action)
    #print(orientation)
    #print(memory)
    
    mana_costs_local = MANA_COSTS.copy()
    mana_costs_local["shield"] = 0
    mana_costs_local["mana_blast"] = 0

    if action.split()[0]=="cast_spell":
        if mana_costs_local[action.split()[1]]>stats["mana"]:
            action="meditate"
    return action, orientation, memory

def get_viable_cardinal_directions(coordinates):
    viable_cardinal_directions = CARDINAL_DIRECTIONS.copy()
    if coordinates[0] == avalanche_progress[0]:
       viable_cardinal_directions.remove("north")
    if coordinates[0] == SIDE_LENGTH - 1 - avalanche_progress[0]:
       viable_cardinal_directions.remove("south")
    if coordinates[1] == avalanche_progress[1]:
       viable_cardinal_directions.remove("west")
    if coordinates[1] == SIDE_LENGTH - 1 - avalanche_progress[1]:
       viable_cardinal_directions.remove("east")
    return viable_cardinal_directions

def H_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = [None, stats["coordinates"], stats["hp"]+stats["shield"]]

    VIABLE_CARDINAL_DIRECTIONS = get_viable_cardinal_directions(stats["coordinates"])
    orientation = random.choice(VIABLE_CARDINAL_DIRECTIONS)
    
    keep_first_memory = True

    DELTA_X, DELTA_Y = deltas(stats["buisness_card"]["orientation"])
    DELTA = DELTA_X + DELTA_Y

    if target["type"] == "perimeter":
        TARGET_NEXT_TO_WALL = False
    elif target["distance"] * DELTA + stats["coordinates"][0 if DELTA_Y else 1] in [avalanche_progress[0 if DELTA_Y else 1], SIDE_LENGTH - 1 - avalanche_progress[0 if DELTA_Y else 1]]:
        TARGET_NEXT_TO_WALL = True
    else:
        TARGET_NEXT_TO_WALL = False
    
    if target["type"] in ["bot", "elemental"]:
        orientation = stats["buisness_card"]["orientation"]
        if target["distance"] == 1:
            if stats["mana"] == MAX_MANA:
               action = "cast_spell mana_blast"
            elif stats["mana"] >= MAX_MANA * (3/4):
               action = "cast_spell shockwave"
            else:
                action = "physical_attack punch"
        elif target["distance"] == 2 and stats["mana"] >= MANA_COSTS["shockwave"]:
            action = "cast_spell shockwave"
        elif target["distance"] >= 3 and target["distance"] <= 6 and stats["mana"] >= MANA_COSTS["fireball"]:
            action = "cast_spell fireball"
        elif target["distance"] >= 7 and stats["mana"] >= MANA_COSTS["lightning_bolt"]:
            action = "cast_spell lightning_bolt"
        elif target["distance"] >= 7 and stats["mana"] >= MANA_COSTS["life_drain"]:
            action = "cast_spell life_drain"
        elif stats["mana"] >= MANA_COSTS["wave"]:
            action = "cast_spell wave"
        elif stats["mana"] >= MANA_COSTS["wind"] and TARGET_NEXT_TO_WALL:
            action = "cast_spell wind"
        elif stats["mana"] >= MANA_COSTS["boulder"]:
            action = "cast_spell boulder"
        elif not stats["invisibility"] and stats["mana"] >= MANA_COSTS["invisibility"]:
            action = "cast_spell invisibility"
        elif stats["invisibility"] and stats["mana"] < MANA_COSTS["lightning_bolt"]:
            action = "meditate"
        else:
            action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
    elif target["type"] != "perimeter" and not (TARGET_NEXT_TO_WALL and target["type"] == "boulder"):
        if stats["mana"] >= MANA_COSTS["wind"] and not TARGET_NEXT_TO_WALL and target["type"] != "fireball":
            action = "cast_spell wind"
            orientation = stats["buisness_card"]["orientation"]
        else:
            action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
            keep_first_memory = False
    elif target["type"] == "boulder" and TARGET_NEXT_TO_WALL and target["distance"] == 1 and stats["mana"] >= MANA_COSTS["shockwave"]:
        action = "cast_spell shockwave"
    elif memory[-1] - (stats["hp"]+stats["shield"]) > 0 and (memory[-1] - (stats["hp"]+stats["shield"])) % 10:
        action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]), sideways=False)
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    elif stats["shield"] < max_shield:
        action = "cast_spell shield"
    elif stats["buisness_card"]["last_movement"].split()[0] == "move" and memory[-1] == stats["coordinates"]: # if tried to move but didn't (implies thing in the way)
        if stats["mana"] >= 10:
            action = "cast_spell mana_blast"
        else:
            action = "meditate"
        orientation = stats["buisness_card"]["last_movement"].split()[1]
    else: # code for hunting people
        if memory[0] is None:
            SCAN_CURRENT = False

            # code for finding furthest direction
            furthest = [0, 0]
            furthest_directions_sgn = [0, 0]
            for axis in [0, 1]:
                if stats["coordinates"][axis] <= SIDE_LENGTH // 2:
                    furthest[axis] = SIDE_LENGTH - 1 - stats["coordinates"][axis]
                    furthest_directions_sgn[axis] = 1
                else:
                    furthest[axis] = stats["coordinates"][axis]
                    furthest_directions_sgn[axis] = -1

            FURTHEST_DIRECTION_INDEX = furthest.index(max(furthest))
            FURTHEST_DIRECTION_SGN = furthest_directions_sgn[FURTHEST_DIRECTION_INDEX]
            
            # code for finding furthest perpendicular direction
            PERPENDICULAR_DIRECTION_INDEX = 1 - FURTHEST_DIRECTION_INDEX
            PERPENDICULAR_DIRECTION_SGN = furthest_directions_sgn[PERPENDICULAR_DIRECTION_INDEX]

            # set orientation to furthest and movement to furthest perpendicular
            if FURTHEST_DIRECTION_INDEX == 0:
                orientation = "south" if FURTHEST_DIRECTION_SGN == 1 else "north"
            else:
                orientation = "east" if FURTHEST_DIRECTION_SGN == 1 else "west"

            if PERPENDICULAR_DIRECTION_INDEX == 0:
                MOVEMENT_DIRECTION = "south" if PERPENDICULAR_DIRECTION_SGN == 1 else "north"
            else:
                MOVEMENT_DIRECTION = "east" if PERPENDICULAR_DIRECTION_SGN == 1 else "west"
        else:
            CURRENT_MOVEMENT_DIRECTION = memory[0][0]
            orientation = memory[0][1]
            MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = deltas(CURRENT_MOVEMENT_DIRECTION)
            #print(f"a {MOVEMENT_DELTA_X} {MOVEMENT_DELTA_Y} {stats['coordinates']} {stats['coordinates'][0 if MOVEMENT_DELTA_Y else 1]} {SIDE_LENGTH - 1} {MOVEMENT_DELTA_X + MOVEMENT_DELTA_Y}") # debug
            if (
                (MOVEMENT_DELTA_X + MOVEMENT_DELTA_Y == -1 and stats["coordinates"][0 if MOVEMENT_DELTA_Y else 1] == avalanche_progress[0 if MOVEMENT_DELTA_Y else 1])
                or (MOVEMENT_DELTA_X + MOVEMENT_DELTA_Y == 1 and stats["coordinates"][0 if MOVEMENT_DELTA_Y else 1] == SIDE_LENGTH - 1 - avalanche_progress[0 if MOVEMENT_DELTA_Y else 1])
            ):
                SCAN_CURRENT = True
                MOVEMENT_DIRECTION = opposite_orientation(CURRENT_MOVEMENT_DIRECTION)
                if stats["coordinates"][0 if DELTA_Y else 1] not in [avalanche_progress[0 if DELTA_Y else 1], SIDE_LENGTH - 1 - avalanche_progress[0 if DELTA_Y else 1]]:
                   orientation = opposite_orientation(orientation)
            else:
                SCAN_CURRENT = False
                MOVEMENT_DIRECTION = CURRENT_MOVEMENT_DIRECTION

        memory[0] = [MOVEMENT_DIRECTION, orientation]

        action = f"move {MOVEMENT_DIRECTION} 1" if not SCAN_CURRENT else f"physical_attack slash" # since mana and shield are at max, slash is the best idle thing to do
    
    memory.append(stats["coordinates"])
    memory.append(stats["hp"]+stats["shield"])

    if not keep_first_memory:
        memory[0] = None

    #print(f"action: {action}, orientation: {orientation}, memory[0]: {memory[0]}") # debug
    return action, orientation, memory

def I_bot_func(stats, target, memory, info_messages):
    VIABLE_CARDINAL_DIRECTIONS = get_viable_cardinal_directions(stats["coordinates"])
    delta_x, delta_y = deltas(stats["buisness_card"]["orientation"])
    orientation = random.choice(VIABLE_CARDINAL_DIRECTIONS)
    if target["type"] == "bot":
        orientation = stats["buisness_card"]["orientation"]
        if target["distance"] == 1:
            if stats["mana"] >= MANA_COSTS["shockwave"]:
                action = "cast_spell shockwave"
            else:
                action = "physical_attack punch"
        else:
            if stats["mana"] >= MANA_COSTS["summon_elemental"]:
                viable_elements = list(ELEMENT_TO_SPELL.keys())
                if not target["distance"] * (delta_x+delta_y) + stats["coordinates"][0 if delta_y else 1] in [avalanche_progress[0], SIDE_LENGTH - 1 - avalanche_progress[0]]:
                    viable_elements.remove("wind")
                elif target["distance"] > 3:
                    viable_elements.remove("earth")
                elif target["distance"] > 5:
                    viable_elements.remove("fire")
                action = f"cast_spell summon_elemental {random.choice(viable_elements)}"
            elif stats["mana"] >= MANA_COSTS["lightning_bolt"] and target["hp_sector"] != "very high" and target["shield_sector"] == "none":
                action = "cast_spell lightning_bolt"
            elif stats["invisibility"]:
                action = "meditate"
            elif stats["mana"] >= MANA_COSTS["invisibility"] and target["orientation"] != opposite_orientation(stats["buisness_card"]["orientation"]):
                action = "cast_spell invisibility"
            elif stats["mana"] >= MANA_COSTS["fireball"] and target["distance"] < 5:
                action = "cast_spell fireball"
            elif stats["mana"] >= MANA_COSTS["life_drain"]:
                action = "cast_spell life_drain"
            else:
                action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
    elif target["type"] == "elemental" and target["allegiance"] != stats["buisness_card"]["name"]:
        orientation = stats["buisness_card"]["orientation"]
        if stats["mana"] >= MANA_COSTS["lightning_bolt"] and target["element"] != "lightning":
            action = "cast_spell lightning_bolt"
        elif stats["mana"] >= MANA_COSTS["wave"] and target["element"] != "water":
            action = "cast_spell wave"
        elif target["distance"] in range(3, 8) and stats["mana"] >= MANA_COSTS["fireball"] and target["element"] != "fire":
            action = "cast_spell fireball"
        elif target["distance"] in range(1, 3) and stats["mana"] >= MANA_COSTS["shockwave"] and target["element"] != "earth":
            action = "cast_spell shockwave"
        elif stats["invisibility"]:
            action = "meditate"
        elif stats["mana"] >= MANA_COSTS["boulder"]:
            action = "cast_spell boulder"
        else:
            action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
    elif target["type"] == "perimeter" and target["distance"] == 1:
        orientation = opposite_orientation(stats["buisness_card"]["orientation"])
        action = f"move {orientation} 1"
    elif target["type"] in ["boulder", "fireball", "water"] and target["distance"] == 1:
        orientation = stats["buisness_card"]["orientation"]
        if stats["mana"] >= MANA_COSTS["wave"]:
            action = "cast_spell wave"
        else:
            action = retreat(stats["buisness_card"]["orientation"], list(stats["coordinates"]))
    elif not stats["mana"]:
        action = "hybernate"
    elif stats["mana"] == MAX_MANA and stats["shield"] >= max_shield:
        if target["distance"] == 1: # if the target is at distance 1 at this point, then it has to be an elemental
            if target["allegiance"] == stats["buisness_card"]["name"]:
                action = f"move {random.choice(list(set(VIABLE_CARDINAL_DIRECTIONS) - set(stats['buisness_card']['orientation'])))} 1"
            else:
                action = "cast_spell lightning_bolt"
        else:
            action = f"cast_spell summon_elemental {random.choice(['lightning', 'darkness'])}"
    elif stats["mana"] // MANA_COSTS["per_shield_hp"] + stats["shield"] >= max_shield and stats["shield"] < max_shield:
        action = "cast_spell shield"
    else:
        action = "meditate"
    return action, orientation, memory

def get_input(prompt, options, names):
    result = None
    while result is None:
        result = input(prompt)
        if result in ["help", "h", "0", ""]:
            print("Write your input as 2 to 4 numbers seperated by spaces.\nThe first represents the command, what you want to do\nIf you picked a command other than meditate or hybernate, then the second number represents the specifier for that action (for example what spell if the action was cast spell)\nThe second option if you picked meditate or hybernate and the third option otherwise is the orientation you wish to face after the turn is over\nThe potential final option is an optional degree specifier, see the list below for when that happens")
            for index, option in enumerate(options):
                print(f"{index+1}. {COMMANDS[index].replace('_', ' ')}{' (optional: specify distance 1 or 2 if facing movement direction, otherwise max)' if COMMANDS[index] == 'move' else ''}")
                if type(option[0]) == list:
                    for sub_index, sub_option in enumerate(names[index]):
                        print(f"\u2008{sub_index+1}. {sub_option}{' (manditory: specify element)' if COMMANDS[index] == 'cast_spell' and names[index][sub_index] == 'summon_elemental' else ''}{' (optional: specify amount of mana used, otherwise max)' if (COMMANDS[index] == 'cast_spell' and names[index][sub_index] == 'shield') else ''}")
                        if COMMANDS[index] == 'cast_spell' and names[index][sub_index] == 'summon_elemental':
                            for sub_sub_index, sub_sub_option in enumerate(ELEMENT_TO_SPELL):
                                print(f"\u2008\u2008{sub_sub_index+1}. {sub_sub_option}")
            print("For orientation:")
            for index, orientation in enumerate(CARDINAL_DIRECTIONS):
                print(f"{index+1}. {orientation}")
            result = None
        else:
            parts = result.split()
            current = deepcopy(options)
            for part in parts:
                if not int_convertable(part):
                   result = None
                   break
                try:
                    current = deepcopy(current[int(part)-1])
                    if type(current) != list:
                        break
                except IndexError:
                    result = None
                    break
            if type(current) == list:
                result = None 
    return result

def Player_func(stats, target, memory, info_messages):
    global player_just_took_damage
    for info_message in info_messages:
        display_info_message(info_message)
    print("mental map:")
    LIGHTNESS_MAP = [[(255-18) * 1.1**(-square[1]) + 18 for square in row] for row in player_memory_maps[stats["buisness_card"]["name"]]]
    display_map([[square[0] for square in row] for row in player_memory_maps[stats["buisness_card"]["name"]]], 1, LIGHTNESS_MAP)
    if player_just_took_damage:
        # make all following text red
        print("\033[31m")
        player_just_took_damage = False

    print(f"max shield: {max_shield}")
    print(f"current time: {current_time}")
    print(f"avalanche progress: y: {avalanche_progress[0]}, x: {avalanche_progress[1]}")
    organize("your stats", stats, 1)
    organize("target", target, 2)
    if memory:
       print(f"memory: {memory}")

    DIRECTION_INPUTS = [str(i) for i in range(1, 5)]
    options = [deepcopy(DIRECTION_INPUTS) for _ in range(5)]
    options[0] = [deepcopy(DIRECTION_INPUTS) for _ in CARDINAL_DIRECTIONS] # move
    options[1] = [deepcopy(DIRECTION_INPUTS) for _ in SPELLS] # cast spell
    options[1][SPELLS.index("summon_elemental")] = [deepcopy(DIRECTION_INPUTS) for _ in ELEMENT_TO_SPELL]
    # meditate is unaltered
    # hybernate is unaltered
    options[4] = [deepcopy(DIRECTION_INPUTS) for _ in PHYSICAL_ATTACKS] # physical attack
    
    OPTIONS = [CARDINAL_DIRECTIONS.copy(), SPELLS.copy(), [], [], PHYSICAL_ATTACKS.copy()]
    
    command = get_input("action ", options, OPTIONS)

    parts = command.split()
    for i, _ in enumerate(parts):
        parts[i] = int(parts[i])
    action = COMMANDS.copy()[parts[0] - 1]
    if action not in ["meditate", "hybernate"]:
        action += " " + OPTIONS[parts[0] - 1][parts[1] - 1]
        if (action == "cast_spell shield" or action.split()[0] == "move") and len(parts) >= 4:
           action += " " + str(parts[3])
        elif action == "cast_spell shield":
           action += " " + str(max_shield * MANA_COSTS["per_shield_hp"])
        elif action.split()[0] == "move":
           action += " 4"
        elif action == "cast_spell soul_search" and len(parts) >= 4:
           action += " " + str(parts[3])
           if len(parts) >= 6:
              action += " " + str(parts[4]) + " " + str(parts[5])
        elif action.split()[1] == "summon_elemental":
            action += " " + list(ELEMENT_TO_SPELL.keys())[parts[2] - 1]
        elif len(parts) >= 4:
           raise Exception(f"Invalid situation. action: {action}, parts: {parts}")
    #print("b", parts, action) # debug
    orientation = CARDINAL_DIRECTIONS.copy()[parts[1 if action in ["meditate", "hybernate"] else (3 if action.split()[1] == "summon_elemental" else 2)] - 1]
    
    # make all following text white again
    print("\033[0m")

    return action, orientation, memory

def damage(target_name, amount, potential_death_message="died", pierce=False, damage_element=None, source_name=None):
  global player_just_took_damage

  if target_name[0].isupper(): # if the target is a bot
    # in case the target doesn't exist
    if target_name not in reaction_times:
        return
    
    # if the target is the player and there is any damage
    if amount > 0 and target_name == "Player" and potential_death_message != DEATH_MESSAGES["infusion"]:
        player_just_took_damage = True

    # attack power is doubled if the target is hybernating
    if people[target_name]["buisness_card"]["hybernation"]:
        amount *= 2

    # for shield damage
    if not pierce:
        people[target_name]["shield"] -= amount
        if people[target_name]["shield"] < 0:
            amount = -people[target_name]["shield"]
            people[target_name]["shield"] = 0
        else:
            amount = 0
        people[target_name]["buisness_card"]["shield_sector"] = ["none", "weak", "moderate", "strong"][ceil((people[target_name]["shield"]*3) / (MAX_MANA / MANA_COSTS["per_shield_hp"]))]
  
    # for any remaining damage to the target
    people[target_name]["hp"] -= amount

    # if the attack kills the target
    if people[target_name]["hp"] <= 0:
        if CONFIRM_KILLS:
            death_message_queue.append([target_name, potential_death_message])
            for player in reaction_times.copy():
                if people[player]["buisness_card"]["hybernation"]:
                    continue
                info_messages[player].append(death_message_queue[-1])
        board[people[target_name]["coordinates"][0]][people[target_name]["coordinates"][1]] = "_"
        final_reaction_times[target_name] = reaction_times[target_name]
        del reaction_times[target_name]
        if source_name is not None:
            EXTRA = (100 - people[source_name]["hp"]) // 4
            people[source_name]["hp"] = max(STARTING_HP, people[source_name]["hp"])
            if EXTRA > 0:
                people[source_name]["hp"] += EXTRA
  elif damage_element != elementals[target_name]["buisness_card"]["element"]: # if the target is an elemental and it's not their element
    elementals[target_name]["hp"] -= amount
    if elementals[target_name]["hp"] <= 0:
        COORDINATES = list(map(int, target_name.split()))
        if elementals[target_name]["buisness_card"]["element"] == "earth":
            board[COORDINATES[0]][COORDINATES[1]] = "b"
            boulders[f"{COORDINATES[0]} {COORDINATES[1]}"] = deepcopy(BOULDER)
        elif elementals[target_name]["buisness_card"]["element"] == "fire":
            fireball_explode(COORDINATES[0], COORDINATES[1], source_name=None, infused=elementals[target_name]["buisness_card"]["infused"])
        else:
            board[COORDINATES[0]][COORDINATES[1]] = "_"
        del elementals[target_name]
  
def fireball_explode(fireball_y, fireball_x, source_name, infused=False):
  if board[fireball_y][fireball_x] == "f":
    board[fireball_y][fireball_x] = "_"
  for relative_x in range(-2, 3):
    for relative_y in range(-2, 3):
        if fireball_y + relative_y < 0 or fireball_y + relative_y >= SIDE_LENGTH or fireball_x + relative_x < 0 or fireball_x + relative_x >= SIDE_LENGTH:
          continue
        target = board[fireball_y+relative_y][fireball_x+relative_x]
        distance = max(abs(relative_x), abs(relative_y))
        if target != target.lower(): # this rules out empty squares as well as inanimate objects
            POTENTIAL_DEATH_MESSAGE = DEATH_MESSAGES["fireball"] if distance == 0 else DEATH_MESSAGES["explosion_1"] if distance == 1 else DEATH_MESSAGES["explosion_2"]
            damage(letters[target], (2 if infused else 1) * (ATTACK_DAMAGE["fireball"] if distance == 0 else ATTACK_DAMAGE["explosion_1"] if distance == 1 else ATTACK_DAMAGE["explosion_2"]), POTENTIAL_DEATH_MESSAGE, False, "fire", source_name)

def add_bot(name, func):
    people[name] = deepcopy(BOT)
    people[name]["buisness_card"]["name"] = name
    reaction_times[name] = random.random()
    player_funcs[name] = func
    memories[name] = []
    player_memory_maps[name] = deepcopy(PLAYER_MEMORY_MAP_BLANK)
    letters[name[0]] = name
    info_messages[name] = []

def delete_self_func(stats, target, memory, info_messages):
    raise KeyboardInterrupt

def cast_fireball(coordinates, delta_x, delta_y, source_name, infused=False, **kwargs):
    try:
        board[coordinates[0] + delta_y][coordinates[1] + delta_x]
    except IndexError:
        pass
    else:
        if board[coordinates[0] + delta_y][coordinates[1] + delta_x] == "_":
            board[coordinates[0] + delta_y][coordinates[1] + delta_x] = "f"
            KEY = f"{coordinates[0] + delta_y} {coordinates[1] + delta_x}"
            fireballs[KEY] = deepcopy(FIREBALL)
            fireballs[KEY]["velocity_x"] = delta_x * FIREBALL_START_VELOCITY
            fireballs[KEY]["velocity_y"] = delta_y * FIREBALL_START_VELOCITY
            fireballs[KEY]["infused"] = infused
        else:
            fireball_explode(coordinates[0] + delta_y, coordinates[1] + delta_x, source_name, infused)

def cast_wave(coordinates, delta_x, delta_y, source_name, infused=False, **kwargs):
    for x in range(-1, 2) if delta_y else [delta_x]:
        for y in [delta_y] if delta_y else range(-1, 2):
            try:
                if coordinates[0] + y < 0 or coordinates[1] + x < 0:
                    continue
                if board[coordinates[0] + y][coordinates[1] + x] == "_":
                    board[coordinates[0] + y][coordinates[1] + x] = "w"
                elif board[coordinates[0] + y][coordinates[1] + x] != board[coordinates[0] + y][coordinates[1] + x].lower(): # to check if there's a player, since "_" == "_".lower() is True
                    damage(letters[board[coordinates[0] + y][coordinates[1] + x]], INFUSION_MULTIPLIER * ATTACK_DAMAGE["wave"], DEATH_MESSAGES["wave"], False, "water", source_name) # should we be multiplying the damage ...?
                    try:
                        # should we be multiplying the velocity on impact ...?
                        people[letters[board[coordinates[0] + y][coordinates[1] + x]]]["velocity_x"] += delta_x * INFUSION_MULTIPLIER
                        people[letters[board[coordinates[0] + y][coordinates[1] + x]]]["velocity_y"] += delta_y * INFUSION_MULTIPLIER
                    except KeyError:
                        pass
            except IndexError:
                continue
            water[f"{coordinates[0] + y} {coordinates[1] + x}"] = deepcopy(WATER)
            water[f"{coordinates[0] + y} {coordinates[1] + x}"]["velocity_x"] = delta_x * WAVE_START_VELOCITY 
            water[f"{coordinates[0] + y} {coordinates[1] + x}"]["velocity_y"] = delta_y * WAVE_START_VELOCITY
            water[f"{coordinates[0] + y} {coordinates[1] + x}"]["infused"] = infused

def cast_wind(coordinates, delta_x, delta_y, target, source_name, **kwargs):
    if target["type"] != "perimeter":
        if target["type"] in ["boulder", "fireball", "water", "elemental"]:
            KEY = f"{coordinates[0]+target['distance']*delta_y} {coordinates[1]+target['distance']*delta_x}"
            target_nonplayer = (boulders if target["type"] == "boulder" else water if target["type"] == "water" else fireballs if target["type"] == "fireball" else elementals)[KEY]
            target_nonplayer["velocity_x"] += WIND_KNOCKBACK * delta_x * INFUSION_MULTIPLIER
            target_nonplayer["velocity_y"] += WIND_KNOCKBACK * delta_y * INFUSION_MULTIPLIER
            if target["type"] == "elemental":
                damage(KEY, INFUSION_MULTIPLIER * ATTACK_DAMAGE["wind"], DEATH_MESSAGES["wind"], False, "wind", source_name)
        else:
            people[target["name"]]["velocity_x"] += WIND_KNOCKBACK * delta_x * INFUSION_MULTIPLIER
            people[target["name"]]["velocity_y"] += WIND_KNOCKBACK * delta_y * INFUSION_MULTIPLIER
            damage(target["name"], INFUSION_MULTIPLIER * ATTACK_DAMAGE["wind"], DEATH_MESSAGES["wind"], False, "wind", source_name)

def cast_lightning(coordinates, delta_x, delta_y, target, source_name, **kwargs):
    if target["type"] == "bot":
        damage(target["name"], INFUSION_MULTIPLIER * ATTACK_DAMAGE["lightning_bolt"], DEATH_MESSAGES["lightning_bolt"], False, "lightning", source_name)
    elif target["type"] == "elemental":
        KEY = f"{coordinates[0] + delta_y * target['distance']} {coordinates[1] + delta_x * target['distance']}"
        damage(KEY, INFUSION_MULTIPLIER * ATTACK_DAMAGE["lightning_bolt"], DEATH_MESSAGES["lightning_bolt"], False, "lightning")

def cast_life_drain(coordinates, delta_x, delta_y, target, name, source_name, **kwargs):
    if target["type"] == "bot":
        damage(target["name"], INFUSION_MULTIPLIER * ATTACK_DAMAGE["life_drain"], DEATH_MESSAGES["life_drain"], True, "darkness", source_name)

        # they only get to heal if it's attacking another bot, not elemental
        HEAL_AMOUNT = (INFUSION_MULTIPLIER * ATTACK_DAMAGE["life_drain"]) // 2
        if name[0].isupper():
            people[name]["hp"] += HEAL_AMOUNT
        else:
            people[elementals[name]["buisness_card"]["allegiance"]]["hp"] += HEAL_AMOUNT
    elif target["type"] == "elemental":
        KEY = f"{coordinates[0] + delta_y * target['distance']} {coordinates[1] + delta_x * target['distance']}"
        damage(KEY, INFUSION_MULTIPLIER * ATTACK_DAMAGE["life_drain"], DEATH_MESSAGES["life_drain"], True, "darkness")
    
def cast_shockwave(coordinates, delta_x, delta_y, source_name, **kwargs):
    DELTA = delta_y if delta_y else delta_x
    YX_SHOCKWAVE_PATTERN = ((range(-1, 2), range(-2, 3)), ((DELTA,), (DELTA * 2,)))
    XY_SHOCKWAVE_PATTERN = (YX_SHOCKWAVE_PATTERN[1], YX_SHOCKWAVE_PATTERN[0])
    
    if delta_x:
        SHOCKWAVE_PATTERN = YX_SHOCKWAVE_PATTERN
    else:
        SHOCKWAVE_PATTERN = XY_SHOCKWAVE_PATTERN
    
    IS_CRIT = not random.randint(0, 2)
    
    for relative_y, relative_x in itertools.chain(
        list(itertools.product(SHOCKWAVE_PATTERN[0][0], SHOCKWAVE_PATTERN[1][0])), 
        list(itertools.product(SHOCKWAVE_PATTERN[0][1], SHOCKWAVE_PATTERN[1][1]))
    ):
        try:
            y, x = coordinates[0] + relative_y, coordinates[1] + relative_x
            if y < 0 or x < 0:
                continue
            SQUARE = board[y][x]
            if SQUARE in letters:
                if SQUARE in ["b", "w", "f", "e"]:
                    KEY = f"{y} {x}"
                    objects = boulders if SQUARE == "b" else water if SQUARE == "w" else fireballs if SQUARE == "f" else elementals
                    if SQUARE == "f":
                        fireball_explode(y, x)
                        del objects[KEY]
                    elif SQUARE == "b" and IS_CRIT:
                        board[y][x] = "_"
                        del objects[KEY]
                    else:
                        objects[KEY]["velocity_x"] += delta_x * INFUSION_MULTIPLIER
                        objects[KEY]["velocity_y"] += delta_y * INFUSION_MULTIPLIER
                        if SQUARE == "e":
                            DAMAGE_LEVEL = 1 if max(abs(y - coordinates[0]), abs(x - coordinates[1])) == 1 else 2
                            if bool(random.randint(0, 2)) ^ (not IS_CRIT):
                                elementals[KEY]["buisness_card"]["stun"] = 1
                            damage(KEY, INFUSION_MULTIPLIER * ATTACK_DAMAGE[f"shockwave_{DAMAGE_LEVEL}{'_crit' if IS_CRIT else ''}"], DEATH_MESSAGES["shockwave"], False, "earth")
                elif SQUARE == "p":
                    pass # perimiter squares just ignore it
                else:
                    people[letters[SQUARE]]["velocity_x"] += delta_x
                    people[letters[SQUARE]]["velocity_y"] += delta_y
                    DAMAGE_LEVEL = 1 if max(abs(y - coordinates[0]), abs(x - coordinates[1])) == 1 else 2
                    damage(letters[SQUARE], INFUSION_MULTIPLIER * ATTACK_DAMAGE[f"shockwave_{DAMAGE_LEVEL}{'_crit' if IS_CRIT else ''}"], DEATH_MESSAGES["shockwave"], False, "earth", source_name)
                    if bool(random.randint(0, 2)) ^ (not IS_CRIT):
                        people[letters[SQUARE]]["buisness_card"]["stun"] = 1
        except IndexError:
            continue

ELEMENT_TO_SPELL = {
    "fire": "fireball",
    "earth": "shockwave",
    "water": "wave",
    "wind": "wind",
    "lightning": "lightning_bolt",
    "darkness": "life_drain"
}

SPELL_TO_FUNCTION = {
    "fireball": cast_fireball,
    "shockwave": cast_shockwave,
    "wave": cast_wave,
    "wind": cast_wind,
    "lightning_bolt": cast_lightning,
    "life_drain": cast_life_drain
}

if not PLAYER_ONLINE:
    Player_func = delete_self_func

previous_winner = ""

try:
  while True:
    max_shield = MAX_MANA // MANA_COSTS["per_shield_hp"]
    
    # set board to an empty 2d list of size SIDE_LENGTH
    board = set_map(SIDE_LENGTH)
    
    death_message_queue = []
    
    people = {}
    reaction_times = {}
    player_funcs = {}
    memories = {}
    player_memory_maps = {}
    info_messages = {}
    final_reaction_times = {}

    letters = {
      "b": "boulder",
      "f": "fireball",
      "w": "water",
      "p": "perimiter",
      "e": "elemental"
    }
    
    add_bot("A_bot", A_bot_func)
    add_bot("B_bot", B_bot_func)
    add_bot("C_bot", C_bot_func)
    add_bot("D_bot", D_bot_func)
    add_bot("E_bot", E_bot_func)
    add_bot("F_bot", F_bot_func)
    add_bot("G_bot", G_bot_func)
    add_bot("H_bot", H_bot_func)
    add_bot("I_bot", I_bot_func)
    add_bot("Player", Player_func)
    
    boulders = {}
    water = {}
    fireballs = {}
    elementals = {}

    avalanche_progress = [0, 0]
    
    # let's set some starting locations:
    numbers = list(range(SIDE_LENGTH))
    random.shuffle(numbers)
    
    numbers_even = [numbers[i] for i in range(0, SIDE_LENGTH, 2)]
    numbers_odd = [numbers[i] for i in range(1, SIDE_LENGTH, 2)]
    random.shuffle(numbers_even)
    random.shuffle(numbers_odd)
    
    for index, person in enumerate(people):
        if index <= SIDE_LENGTH//2 - 1:
           people[person]["coordinates"] = (numbers[index*2], numbers[index*2+1])
        elif index <= (SIDE_LENGTH//2 - 1) * 2:
           people[person]["coordinates"] = (numbers_odd[index-SIDE_LENGTH//2], numbers_even[index-SIDE_LENGTH//2])
        else:
           raise Exception("work something out, too many bots, find out what to do")
        
    for player in people:
        board[people[player]["coordinates"][0]][people[player]["coordinates"][1]] = people[player]["buisness_card"]["name"][0]
        people[player]["buisness_card"]["orientation"] = random.choice(CARDINAL_DIRECTIONS.copy())
    
    history = []
    current_time = 0
    
    player_just_took_damage = False

    while len(reaction_times) > 1:
      history.append(deepcopy(board))
      death_message_queue.clear()
      final_reaction_times = dict()
      if "Player" not in reaction_times:
          print(f"{' '}{previous_winner}")
          LIGHTNESS_MAP = [[(255-18) * 1.1**(-square[1]) + 18 for square in row] for row in player_memory_maps["F_bot"]]
          display_map([[square[0] for square in row] for row in player_memory_maps["F_bot"]], 1, LIGHTNESS_MAP)
          display_map(board)
          print(f"Max shield: {max_shield}")
          print(f"current time: {current_time}")
      
      player_actions = {}
      for player in deepcopy(reaction_times):
        if player not in reaction_times or people[player]["buisness_card"]["hybernation"]:
          continue
        delta_x, delta_y = deltas(people[player]["buisness_card"]["orientation"])
        for row in player_memory_maps[player]:
          for square in row:
            square[1] += 1

        player_memory_maps[player][people[player]["coordinates"][0]][people[player]["coordinates"][1]] = [player[0], 0]
        target = get_target(people[player]["coordinates"], delta_x, delta_y, True)
        
        if "Player" not in reaction_times:
            print(f"{player} hp: {people[player]['hp']}, mana: {people[player]['mana']}, shield: {people[player]['shield']}, time: {(reaction_times[player]*10**6):.2f} μs{', stunned' if people[player]['buisness_card']['stun'] else ''}")
            
        try:
          if people[player]["buisness_card"]["stun"]:
              action, DESIGNATAED_ORIENTATION, reaction_times[player] = "", people[player]["buisness_card"]["orientation"], 0
          else:
            START_TIME = perf_counter()
            action, DESIGNATAED_ORIENTATION, memories[player] = player_funcs[player if people[player]["hexed"] is None else people[player]["hexed"]["source"]](deepcopy(people[player]), deepcopy(target), deepcopy(memories[player]), info_messages[player])
            END_TIME = perf_counter()
            reaction_times[player] = END_TIME-START_TIME
          info_messages[player] = []
          if DESIGNATAED_ORIENTATION not in CARDINAL_DIRECTIONS:
            raise Exception("Invalid orientation")
          if action and action.split()[0] == "move":
            int(action.split()[2])
            if action.split()[1] not in CARDINAL_DIRECTIONS:
              raise Exception("Invalid direction")
          if action and action.split()[:2] == ["cast_spell", "shield"]:
            try:
                int(action.split()[2])
            except Exception:
                action = f"cast_spell shield {people[player]['mana']}"
          player_actions[player] = [action, DESIGNATAED_ORIENTATION]
        except KeyboardInterrupt: # for some reason this needs to be done seperately
            death_message_queue.append([player, DEATH_MESSAGES["error"]('KeyboardInterrupt')])
            del reaction_times[player]
            board[people[player]["coordinates"][0]][people[player]["coordinates"][1]] = "_"
            continue
        """except Exception as error_message:
            death_message_queue.append([player, DEATH_MESSAGES['error'](error_message)])
            del reaction_times[player]
            board[people[player]["coordinates"][0]][people[player]["coordinates"][1]] = "_"
            continue"""
        
      sorted_reaction_times = dict(sorted(reaction_times.items(), key=lambda item: item[1]))
    
      for player in sorted_reaction_times:
        if player not in reaction_times:
           continue
        if people[player]["buisness_card"]["hybernation"]:
            people[player]["buisness_card"]["hybernation"] -= 1
            if not people[player]["buisness_card"]["hybernation"]:
                people[player]["shield"] = max_shield
                people[player]["mana"] = MAX_MANA
            continue
        if people[player]["invisibility"]:
           people[player]["invisibility"] -= 1
        action, DESIGNATAED_ORIENTATION = player_actions[player]
        delta_x, delta_y = deltas(people[player]["buisness_card"]["orientation"])
        player_memory_maps[player][people[player]["coordinates"][0]][people[player]["coordinates"][1]] = [player[0], 0] # unsure if this is necessary
        target = get_target(people[player]["coordinates"], delta_x, delta_y, False)
        people[player]["buisness_card"]["last_movement"] = action
        INFUSION_MULTIPLIER = (2 if people[player]["buisness_card"]["infused"] else 1)
        ENHANCEMENT_MULTIPLIER = (2 if people[player]["buisness_card"]["enhancement"] else 1)
        if action != "meditate" or people[player]["buisness_card"]["stun"] or people[player]["buisness_card"]["hybernation"]:
          people[player]["buisness_card"]["is_meditating"] = False
        if people[player]["buisness_card"]["stun"]:
          people[player]["buisness_card"]["stun"] -= 1
        elif action.split()[0] == "move": # example: action = "move north 2"
          MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = deltas(action.split()[1])
          for _ in range(min(int(action.split()[2]), ENHANCEMENT_MULTIPLIER * (2 if people[player]["buisness_card"]["orientation"] == action.split()[1] else 1))):
            INDEX_TOO_LOW = min(people[player]["coordinates"][0] + MOVEMENT_DELTA_Y, people[player]["coordinates"][1] + MOVEMENT_DELTA_X, 0) < 0
            try:
              SQUARE_EMPTY = board[people[player]["coordinates"][0] + MOVEMENT_DELTA_Y][people[player]["coordinates"][1]+MOVEMENT_DELTA_X] == "_"
              INDEX_TOO_HIGH = False
            except IndexError:
              INDEX_TOO_HIGH = True
            if not INDEX_TOO_HIGH and not INDEX_TOO_LOW:
              if SQUARE_EMPTY:
                board[people[player]["coordinates"][0]][people[player]["coordinates"][1]] = "_"
                player_memory_maps[player][people[player]["coordinates"][0]][people[player]["coordinates"][1]] = ["_", 0]
                people[player]["coordinates"] = (people[player]["coordinates"][0] + MOVEMENT_DELTA_Y, people[player]["coordinates"][1] + MOVEMENT_DELTA_X)
                board[people[player]["coordinates"][0]][people[player]["coordinates"][1]] = player[0]
                player_memory_maps[player][people[player]["coordinates"][0]][people[player]["coordinates"][1]] = [player[0], 0]
        elif action.split()[0] == "cast_spell":
          if action.split()[1] == "fireball":
            if people[player]["mana"] >= MANA_COSTS["fireball"]:
                people[player]["mana"] -= MANA_COSTS["fireball"]
                cast_fireball(people[player]["coordinates"], delta_x, delta_y, source_name=player, infused=people[player]["buisness_card"]["infused"])
          elif action.split()[1] == "boulder":
            try:
                if people[player]["coordinates"][0] + delta_y < 0 or people[player]["coordinates"][1] + delta_x < 0:
                    raise IndexError
                if people[player]["mana"] >= MANA_COSTS["boulder"] and board[people[player]["coordinates"][0] + delta_y][people[player]["coordinates"][1] + delta_x] == "_":
                    people[player]["mana"] -= MANA_COSTS["boulder"]
                    boulders[f"{people[player]['coordinates'][0] + delta_y} {people[player]['coordinates'][1] + delta_x}"] = BOULDER.copy()
                    boulders[f"{people[player]['coordinates'][0] + delta_y} {people[player]['coordinates'][1] + delta_x}"]["infused"] = people[player]["buisness_card"]["infused"]
                    board[people[player]["coordinates"][0] + delta_y][people[player]["coordinates"][1] + delta_x] = "b"
            except IndexError:
                pass
          elif action.split()[1] == "wave":
            if people[player]["mana"] >= MANA_COSTS["wave"]:
              people[player]["mana"] -= MANA_COSTS["wave"]
              cast_wave(people[player]["coordinates"], delta_x, delta_y, source_name=player, infused=people[player]["buisness_card"]["infused"])
          elif action.split()[1] == "wind":
            if people[player]["mana"] >= MANA_COSTS["wind"]:
              people[player]["mana"] -= MANA_COSTS["wind"]
              cast_wind(people[player]["coordinates"], delta_x, delta_y, target, source_name=player)
          elif action.split()[1] == "lightning_bolt":
            if people[player]["mana"] >= MANA_COSTS["lightning_bolt"]:
              people[player]["mana"] -= MANA_COSTS["lightning_bolt"]
              cast_lightning(people[player]["coordinates"], delta_x, delta_y, target, source_name=player)
          elif action.split()[1] == "life_drain":
            if people[player]["mana"] >= MANA_COSTS["life_drain"]:
              people[player]["mana"] -= MANA_COSTS["life_drain"]
              cast_life_drain(people[player]["coordinates"], delta_x, delta_y, target, player, source_name=player)
          elif action.split()[1] == "shockwave":
            if people[player]["mana"] >= MANA_COSTS["shockwave"]:
                people[player]["mana"] -= MANA_COSTS["shockwave"]
                cast_shockwave(people[player]["coordinates"], delta_x, delta_y, source_name=player)
          elif action.split()[1] == "mana_blast":
            for remaining_player in reaction_times.copy():
              if remaining_player == player:
                continue
              furthest_axis = max(abs(people[remaining_player]["coordinates"][0]-people[player]["coordinates"][0]), abs(people[remaining_player]["coordinates"][1]-people[player]["coordinates"][1]))
              damage(remaining_player, INFUSION_MULTIPLIER * max(int((people[player]["mana"]/100 - furthest_axis + 1) * 10), 0), DEATH_MESSAGES["mana_blast"], source_name=player)
            people[player]["mana"] = 0
          elif action.split()[1] == "shield":
            original_max_shield = max_shield
            if people[player]["buisness_card"]["infused"]:
                max_shield *= 2
            if people[player]["shield"] < max_shield:
                MAX_AFFORDABLE = min(int(action.split()[2]), (max_shield - people[player]["shield"])*MANA_COSTS["per_shield_hp"], people[player]["mana"])
                people[player]["mana"] -= MAX_AFFORDABLE
                people[player]["shield"] += MAX_AFFORDABLE // MANA_COSTS["per_shield_hp"] + (1 if MAX_AFFORDABLE % MANA_COSTS["per_shield_hp"] and random.randint(0, MAX_AFFORDABLE % MANA_COSTS["per_shield_hp"]) else 0)
                if max_shield - people[player]["shield"] == 1:
                    people[player]["shield"] = max_shield
                people[player]["buisness_card"]["shield_sector"] = ["none", "weak", "moderate", "strong"][ceil((people[player]["shield"]*3) / (MAX_MANA // MANA_COSTS["per_shield_hp"]))]
            max_shield = original_max_shield
          elif action.split()[1] == "infusion":
            if people[player]["mana"] >= MANA_COSTS["infusion"]:
                people[player]["mana"] -= MANA_COSTS["infusion"]
                INFUSION_DAMAGE_TARGET = player if people[player]["hexed"] is None else people[people[player]["hexed"]["source"]]
                damage(INFUSION_DAMAGE_TARGET, INFUSION_HP_COST, DEATH_MESSAGES["infusion"], True)
                people[player]["buisness_card"]["infused"] = True
          elif action.split()[1] == "enhance":
            if people[player]["mana"] >= MANA_COSTS["enhance"]:
                people[player]["mana"] -= MANA_COSTS["enhance"]
                people[player]["buisness_card"]["enhancement"] += ENHANCEMENT_TIME
          elif action.split()[1] == "soul_search":
            if people[player]["mana"] >= MANA_COSTS["soul_search"]:
                people[player]["mana"] -= MANA_COSTS["soul_search"]
                INVERSE = not (len(action.split()) == 2 or not action.split()[2])
            CENTER_POINT = tuple(people[player]["coordinates"]) if len(action.split()) < 5 else (int(action.split()[3]), int(action.split()[4]))
            player_distances = {}
            for remaining_player in reaction_times.copy():
              if remaining_player == player:
                continue
              player_distances[remaining_player] = (abs(CENTER_POINT[0] - people[remaining_player]["coordinates"][0])**2 + abs(CENTER_POINT[1] - people[remaining_player]["coordinates"][1])**2)**(1/2)
            player_distances = dict(sorted(player_distances.items(), key=lambda item: item[1], reverse=INVERSE))
            if not people[player]["buisness_card"]["infused"]:
                SEARCHED_TARGET = list(player_distances.keys())[0]
                player_distances = {SEARCHED_TARGET: player_distances[SEARCHED_TARGET]}
            for remaining_player in player_distances:
                if remaining_player == player:
                    continue
                info_messages[player].append(["soul_search", people[remaining_player]])
                player_memory_maps[player][people[remaining_player]["coordinates"][0]][people[remaining_player]["coordinates"][1]] = [remaining_player[0], 0]
          elif action.split()[1] == "invisibility":
            if people[player]["mana"] >= MANA_COSTS["invisibility"]:
                people[player]["mana"] -= MANA_COSTS["invisibility"]
                people[player]["invisibility"] += INVISIBILITY_TIME # yes, +=. It stacks.
          elif action.split()[1] == "summon_elemental":
            if people[player]["mana"] >= MANA_COSTS["summon_elemental"] and action.split()[2] in ["fire", "water", "earth", "wind", "lightning", "darkness"]:
                try:
                    if people[player]["coordinates"][0] + delta_y < 0 or people[player]["coordinates"][1] + delta_x < 0:
                        raise IndexError
                    if board[people[player]["coordinates"][0] + delta_y][people[player]["coordinates"][1] + delta_x] == "_":
                        people[player]["mana"] -= MANA_COSTS["summon_elemental"]
                        board[people[player]["coordinates"][0] + delta_y][people[player]["coordinates"][1] + delta_x] = "e"
                        KEY = f"{people[player]['coordinates'][0]+delta_y} {people[player]['coordinates'][1]+delta_x}"
                        elementals[KEY] = deepcopy(ELEMENTAL)
                        elementals[KEY]["buisness_card"]["element"] = action.split()[2]
                        elementals[KEY]["buisness_card"]["allegiance"] = player
                        elementals[KEY]["buisness_card"]["orientation"] = people[player]["buisness_card"]["orientation"]
                        elementals[KEY]["buisness_card"]["remaining_spell_count"] = ELEMENTAL_STARTING_SPELL_COUNT * INFUSION_MULTIPLIER
                        elementals[KEY]["buisness_card"]["infused"] = people[player]["buisness_card"]["infused"]
                except IndexError:
                   pass
          elif action.split()[1] == "hex":
            if people[player]["mana"] >= MANA_COSTS["hex"]:
                people[player]["mana"] -= MANA_COSTS["hex"]
                if target["type"] == "bot":
                    people[target["name"]]["hexed"] = {"source": player, "time": HEX_TIME}
                    if people[target["name"]]["buisness_card"]["infused"]:
                        people[target["name"]]["hexed"]["time"] *= 2
                    else:
                        people[player]["buisness_card"]["stun"] = HEX_TIME
                elif target["type"] == "elemental":
                    KEY = f"{people['player']['coordinates'][0] + delta_y * target['distance']} {people['player']['coordinates'][1] + delta_x * target['distance']}"
                    ORIGINAL_ALLEGIANCE = target["allegiance"]
                    elementals[KEY]["buisness_card"]["allegiance"] = player
                    if people[player]["buisness_card"]["infused"]:
                        for elemental in elementals:
                            if elementals[elemental]["buisness_card"]["allegiance"] == ORIGINAL_ALLEGIANCE and elementals[elemental]["buisness_card"]["element"] == target["element"]:
                                elementals[elemental]["buisness_card"]["allegiance"] = player
                        elementals[KEY]["buisness_card"]["infused"] = True
                        elementals[KEY]["buisness_card"]["remaining_spell_count"] *= 2
          else:
            print(f"Error: Unknown spell. Player: {player}, action: {action}")
        elif action == "meditate": # because if action is meditate, the entire action is meditate
          if people[player]["buisness_card"]["is_meditating"]:
            people[player]["mana"] += 50
          else:
            people[player]["mana"] += 20
            people[player]["buisness_card"]["is_meditating"] = True
          people[player]["mana"] = min(people[player]["mana"], MAX_MANA)
        elif action == "hybernate":
            people[player]["buisness_card"]["hybernation"] = HYBERNATION_TIME
            people[player]["shield"] = 0
        elif action.split()[0] == "physical_attack":
          if action.split()[1] == "punch" and target["distance"] == 1:
            if target["type"] == "bot":
                damage(target["name"], ATTACK_DAMAGE["punch"]*ENHANCEMENT_MULTIPLIER, DEATH_MESSAGES["punch"], source_name=player)
            elif target["type"] == "elemental":
                KEY = f"{people[player]['coordinates'][0] + delta_y} {people[player]['coordinates'][1] + delta_x}"
                damage(KEY, ATTACK_DAMAGE["punch"]*ENHANCEMENT_MULTIPLIER, DEATH_MESSAGES["punch"])
          elif action.split()[1] == "slash":
            for x in range(-1, 2) if delta_y else [delta_x]:
                for y in [delta_y] if delta_y else range(-1, 2):
                    if people[player]["coordinates"][0] + y < 0 or people[player]["coordinates"][1] + x < 0:
                        continue
                    if people[player]["coordinates"][0] + y >= SIDE_LENGTH or people[player]["coordinates"][1] + x >= SIDE_LENGTH:
                        continue
                    if board[people[player]["coordinates"][0] + y][people[player]["coordinates"][1] + x].isupper(): # this returns false also when it's "_"
                       damage(letters[board[people[player]["coordinates"][0] + y][people[player]["coordinates"][1] + x]], ATTACK_DAMAGE["slash"]*ENHANCEMENT_MULTIPLIER, DEATH_MESSAGES["slash"], source_name=player)
                    KEY = f"{people[player]['coordinates'][0] + y} {people[player]['coordinates'][1] + x}"
                    if KEY in elementals:
                        damage(KEY, ATTACK_DAMAGE["slash"]*ENHANCEMENT_MULTIPLIER, DEATH_MESSAGES["slash"])
        else:
          print(f"ERROR: unknown action. Player: {player}, action: {action}")
        
        if action and action.split()[0] == "cast_spell" and action.split()[1] != "infusion":
            people[player]["buisness_card"]["infused"] = False

        if player not in reaction_times:
            continue
    
        if not people[player]["buisness_card"]["stun"]:
           people[player]["buisness_card"]["orientation"] = DESIGNATAED_ORIENTATION
        
        if people[player]["buisness_card"]["enhancement"]:
            people[player]["buisness_card"]["enhancement"] -= 1

        if people[player]["hexed"] is not None:
            people[player]["hexed"]["time"] -= 1
            if not people[player]["hexed"]["time"]:
                people[player]["hexed"] = None

        board[people[player]["coordinates"][0]][people[player]["coordinates"][1]] = people[player]["buisness_card"]["name"][0]
    
      for key, elemental in deepcopy(elementals).items():
        if elemental not in elementals.values():
            continue
        INFUSION_MULTIPLIER = (2 if elemental["buisness_card"]["infused"] else 1)
        COORDINATES = list(map(int, key.split()))
        delta_x, delta_y = deltas(elemental["buisness_card"]["orientation"])
        target = get_target(COORDINATES, delta_x, delta_y, respect_invisibility=True, is_player=False)
        #print("c", key) # debug
        #organize("e, target", target) # debug
        if elemental["buisness_card"]["stun"]:
            elementals[key]["buisness_card"]["stun"] -= 1
        elif (target["type"] == "bot" and target["name"] != elemental["buisness_card"]["allegiance"]) or (target["type"] == "elemental" and target["allegiance"] != elemental["buisness_card"]["allegiance"] and random.randint(0, 1)): # if it sees an enemy or enemy elemental and 50-50 chance
            SPELL = ELEMENT_TO_SPELL[elemental["buisness_card"]["element"]]
            if SPELL == "shockwave" and target["distance"] > 2:
                MOVEMENT_DIRECTION = elemental["buisness_card"]["orientation"]
                MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = deltas(MOVEMENT_DIRECTION)
                for _ in range(2):
                    INDEX_TOO_LOW = min(COORDINATES[0] + MOVEMENT_DELTA_Y, COORDINATES[1] + MOVEMENT_DELTA_X, 0) < 0
                    try:
                        SQUARE_EMPTY = board[COORDINATES[0] + MOVEMENT_DELTA_Y][COORDINATES[1]+MOVEMENT_DELTA_X] == "_"
                        INDEX_TOO_HIGH = False
                    except IndexError:
                        INDEX_TOO_HIGH = True
                    if not INDEX_TOO_HIGH and not INDEX_TOO_LOW and SQUARE_EMPTY:
                        board[COORDINATES[0]][COORDINATES[1]] = "_"
                        del elementals[key]
                        key = f"{COORDINATES[0] + MOVEMENT_DELTA_Y} {COORDINATES[1] + MOVEMENT_DELTA_X}"
                        elementals[key] = elemental
                        board[COORDINATES[0] + MOVEMENT_DELTA_Y][COORDINATES[1] + MOVEMENT_DELTA_X] = "e"
            else:
                SPELL_TO_FUNCTION[SPELL](COORDINATES, delta_x, delta_y, infused=elemental["buisness_card"]["infused"], target=target, name=key, source_name=None) # you can set source name to the allegiance if you want to buff them, but currently they're strong enough
                #input(f"d {SPELL} {key}") # debug
                elementals[key]["buisness_card"]["remaining_spell_count"] -= 1
            if not elementals[key]["buisness_card"]["remaining_spell_count"]:
                board[COORDINATES[0]][COORDINATES[1]] = "_"
                del elementals[key]
        else: # if being peaceful, moving about
            MOVEMENT_DIRECTION = random.choice(CARDINAL_DIRECTIONS)
            MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = deltas(MOVEMENT_DIRECTION)
            for _ in range(2 if elemental["buisness_card"]["orientation"] == MOVEMENT_DIRECTION else 1):
                INDEX_TOO_LOW = min(COORDINATES[0] + MOVEMENT_DELTA_Y, COORDINATES[1] + MOVEMENT_DELTA_X, 0) < 0
                try:
                    SQUARE_EMPTY = board[COORDINATES[0] + MOVEMENT_DELTA_Y][COORDINATES[1]+MOVEMENT_DELTA_X] == "_"
                    INDEX_TOO_HIGH = False
                except IndexError:
                    INDEX_TOO_HIGH = True
                if not INDEX_TOO_HIGH and not INDEX_TOO_LOW and SQUARE_EMPTY:
                    board[COORDINATES[0]][COORDINATES[1]] = "_"
                    del elementals[key]
                    key = f"{COORDINATES[0] + MOVEMENT_DELTA_Y} {COORDINATES[1] + MOVEMENT_DELTA_X}"
                    elementals[key] = elemental
                    board[COORDINATES[0] + MOVEMENT_DELTA_Y][COORDINATES[1] + MOVEMENT_DELTA_X] = "e"
            elementals[key]["buisness_card"]["orientation"] = random.choice(CARDINAL_DIRECTIONS)

      for player_to_be_moved in reaction_times.copy():
        if people[player_to_be_moved]["coordinates"][0] + 1 > SIDE_LENGTH-1 and people[player_to_be_moved]["velocity_y"] > 0 or people[player_to_be_moved]["coordinates"][0] - 1 < 0 and people[player_to_be_moved]["velocity_y"] < 0:
          damage(player_to_be_moved, ATTACK_DAMAGE["crash"] * abs(people[player_to_be_moved]["velocity_y"]), DEATH_MESSAGES["crash"]) 
          people[player_to_be_moved]["velocity_y"] = 0
        if people[player_to_be_moved]["coordinates"][1] + 1 > SIDE_LENGTH-1 and people[player_to_be_moved]["velocity_x"] > 0 or people[player_to_be_moved]["coordinates"][1] - 1 < 0 and people[player_to_be_moved]["velocity_x"] < 0:
          damage(player_to_be_moved, ATTACK_DAMAGE["crash"] * abs(people[player_to_be_moved]["velocity_x"]), DEATH_MESSAGES["crash"])
          people[player_to_be_moved]["velocity_x"] = 0
        if player_to_be_moved not in reaction_times:
          continue
        SGN_PLAYER_VELOCITY_X = 1 if people[player_to_be_moved]["velocity_x"] > 0 else (-1 if people[player_to_be_moved]["velocity_x"] else 0)
        SGN_PLAYER_VELOCITY_Y = 1 if people[player_to_be_moved]["velocity_y"] > 0 else (-1 if people[player_to_be_moved]["velocity_y"] else 0)
        if board[people[player_to_be_moved]["coordinates"][0] + SGN_PLAYER_VELOCITY_Y][people[player_to_be_moved]["coordinates"][1] + SGN_PLAYER_VELOCITY_X] == "b":
          damage(player_to_be_moved, ATTACK_DAMAGE["crash"] * (abs(people[player_to_be_moved]["velocity_x"])+abs(people[player_to_be_moved]["velocity_y"])), DEATH_MESSAGES["crash"])
        elif board[people[player_to_be_moved]["coordinates"][0] + SGN_PLAYER_VELOCITY_Y][people[player_to_be_moved]["coordinates"][1] + SGN_PLAYER_VELOCITY_X] == "_":
          board[people[player_to_be_moved]["coordinates"][0]][people[player_to_be_moved]["coordinates"][1]] = "_"
          player_memory_maps[player_to_be_moved][people[player_to_be_moved]["coordinates"][0]][people[player_to_be_moved]["coordinates"][1]] = ["_", 0]
          people[player_to_be_moved]["coordinates"] = (people[player_to_be_moved]["coordinates"][0] + SGN_PLAYER_VELOCITY_Y, people[player_to_be_moved]["coordinates"][1] + SGN_PLAYER_VELOCITY_X)
          board[people[player_to_be_moved]["coordinates"][0]][people[player_to_be_moved]["coordinates"][1]] = player_to_be_moved[0]
          player_memory_maps[player_to_be_moved][people[player_to_be_moved]["coordinates"][0]][people[player_to_be_moved]["coordinates"][1]] = [player_to_be_moved[0], 0]
          people[player_to_be_moved]["velocity_x"] -= SGN_PLAYER_VELOCITY_X
          people[player_to_be_moved]["velocity_y"] -= SGN_PLAYER_VELOCITY_Y
    
      class HitWall(Exception):
        pass
      for objects in [boulders, water, fireballs, elementals]:
        for key, value in objects.copy().items():
          try:
            objects[key]
          except KeyError:
            continue
          INFUSION_MULTIPLIER = 2 if value["buisness_card"]["infused"] else 1
          try:
            COORDINATES = tuple(map(int, key.split()))
            if (COORDINATES[0] + 1 > SIDE_LENGTH-1 and value["velocity_y"] > 0) or (COORDINATES[0] - 1 < 0 and value["velocity_y"] < 0):
              objects[key]["velocity_y"] = 0
              raise HitWall(f"Debug info: {key}, {objects[key]}")
            if (COORDINATES[1] + 1 > SIDE_LENGTH-1 and value["velocity_x"] > 0) or (COORDINATES[1] - 1 < 0 and value["velocity_x"] < 0):
              objects[key]["velocity_x"] = 0
              raise HitWall(f"Debug info: {key}, {objects[key]}")
          except HitWall:
            if (COORDINATES[1] + 1 > SIDE_LENGTH-1 and value["velocity_x"] > 0) or (COORDINATES[1] - 1 < 0 and value["velocity_x"] < 0): # still need to test just in case both
              objects[key]["velocity_x"] = 0
            if objects == water:
              board[COORDINATES[0]][COORDINATES[1]] = "_"
              del water[key]
              continue
            elif objects == fireballs:
              FIREBALL_Y, FIREBALL_X = COORDINATES
              fireball_explode(FIREBALL_Y, FIREBALL_X, source_name=None, infused=value["infused"])
              del fireballs[key]
              continue
            elif objects == elementals:
              damage(key, ATTACK_DAMAGE["crash"] * (abs(value["velocity_y"])+abs(value["velocity_x"])))
          SGN_NONPLAYER_VELOCITY_X = 1 if value["velocity_x"] > 0 else (-1 if value["velocity_x"] else 0)
          SGN_NONPLAYER_VELOCITY_Y = 1 if value["velocity_y"] > 0 else (-1 if value["velocity_y"] else 0)
          COORDINATES = tuple(map(int, key.split()))
          NEW_COORDINATES = (COORDINATES[0] + SGN_NONPLAYER_VELOCITY_Y, COORDINATES[1] + SGN_NONPLAYER_VELOCITY_X)
          
          if SGN_NONPLAYER_VELOCITY_Y or SGN_NONPLAYER_VELOCITY_X:
            NEXT_SQUARE = board[NEW_COORDINATES[0]][NEW_COORDINATES[1]]
            NEW_KEY = " ".join([str(COORDINATES[0]+SGN_NONPLAYER_VELOCITY_Y), str(COORDINATES[1]+SGN_NONPLAYER_VELOCITY_X)])
            if NEXT_SQUARE == "_":
                board[COORDINATES[0]][COORDINATES[1]] = "_"
                del objects[key]
                objects[NEW_KEY] = value
                board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] = "b" if objects == boulders else "w" if objects == water else "f" if objects == fireballs else "e"
            elif NEXT_SQUARE != NEXT_SQUARE.lower(): # to check if there is a player there
                if objects == boulders:
                    damage(letters[NEXT_SQUARE], INFUSION_MULTIPLIER * (ATTACK_DAMAGE["boulder"] * abs(SGN_NONPLAYER_VELOCITY_X) + ATTACK_DAMAGE["boulder"] * abs(SGN_NONPLAYER_VELOCITY_Y)), DEATH_MESSAGES["boulder"], False, "earth")
                    value["velocity_x"] = 0
                    value["velocity_y"] = 0
                elif objects == water:
                    damage(letters[NEXT_SQUARE], INFUSION_MULTIPLIER * (ATTACK_DAMAGE["wave"] * abs(SGN_NONPLAYER_VELOCITY_X) + ATTACK_DAMAGE["wave"] * abs(SGN_NONPLAYER_VELOCITY_Y)), DEATH_MESSAGES["wave"], False, "water")
                    if NEXT_SQUARE != "_":
                        people[letters[NEXT_SQUARE]]["velocity_x"] += SGN_NONPLAYER_VELOCITY_X * 3 * INFUSION_MULTIPLIER
                        people[letters[NEXT_SQUARE]]["velocity_y"] += SGN_NONPLAYER_VELOCITY_Y * 3 * INFUSION_MULTIPLIER
                    board[COORDINATES[0]][COORDINATES[1]] = "_"
                    del water[key]
                elif objects == fireballs:
                    FIREBALL_Y, FIREBALL_X = map(int, key.split())
                    fireball_explode(FIREBALL_Y+SGN_NONPLAYER_VELOCITY_Y, FIREBALL_X+SGN_NONPLAYER_VELOCITY_X, source_name=None, infused=value["infused"])
                    board[FIREBALL_Y][FIREBALL_X] = "_"
                    del fireballs[key]
            elif NEXT_SQUARE == "f":
                board[COORDINATES[0]][COORDINATES[1]] = "_"
                del objects[key]
                if objects == boulders:
                    fireball_explode(*map(int, NEW_KEY.split()), source_name=None, infused=fireballs[NEW_KEY]["infused"])
                if objects == fireballs:
                    fireball_explode(COORDINATES[0], COORDINATES[1], source_name=None, infused=value["infused"])
                    fireballs[NEW_KEY]["velocity_x"] += value["velocity_x"]
                    fireballs[NEW_KEY]["velocity_y"] += value["velocity_y"]
                else:
                    board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] = "_"
                    del fireballs[NEW_KEY]
                objects[NEW_KEY] = value
                board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] = "b" if objects == boulders else "w" if objects == water else "f" if objects == fireballs else "e"
            elif NEXT_SQUARE == "b":
                if objects == fireballs:
                    fireball_explode(COORDINATES[0], COORDINATES[1], source_name=None, infused=value["infused"])
                    board[COORDINATES[0]][COORDINATES[1]] = "_"
                    del fireballs[key]
                elif objects == elementals:
                    damage(key, (abs(objects[key]["velocity_y"]) + abs(objects[key]["velocity_x"])) * ATTACK_DAMAGE["crash"])
                else:
                    if objects == water:
                        board[COORDINATES[0]][COORDINATES[1]] = "_"
                        del objects[key]
                    boulders[NEW_KEY]["velocity_x"] += value["velocity_x"]
                    boulders[NEW_KEY]["velocity_y"] += value["velocity_y"]
                    if objects == boulders:
                        boulders[key]["velocity_x"] = boulders[key]["velocity_y"] = 0
            elif NEXT_SQUARE == "w":
                if objects == fireballs:
                    board[COORDINATES[0]][COORDINATES[1]] = "_"
                    del objects[key]
                else:
                    VECTOR_SUMS = [value[f"velocity_{axis}"] + water[NEW_KEY][f"velocity_{axis}"] for axis in ["y", "x"]]
                    for axis_index, axis in enumerate(["y", "x"]):
                        if not value[f"velocity_{axis}"]:
                            pass
                        elif value[f"velocity_{axis}"] * VECTOR_SUMS[axis_index] > 0: # if both negative or both positive
                            water[NEW_KEY][f"velocity_{axis}"] = VECTOR_SUMS[axis_index]
                            if objects == water and not value[f"velocity_{['y', 'x'][1-axis_index]}"]:
                                board[COORDINATES[0]][COORDINATES[1]] = "_"
                                del objects[key]
                        elif not VECTOR_SUMS[axis_index]: # if they are equal magnitude opposite directions
                            if not water[NEW_KEY][f"velocity_{['y', 'x'][1-axis_index]}"]:
                                board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] = "_"
                                del water[NEW_KEY]
                            else: # if it's moving in perpendicular axis
                                water[NEW_KEY][f"velocity_{axis}"] = 0
                            if objects == water and not value[f"velocity_{['y', 'x'][1-axis_index]}"]:
                                board[COORDINATES[0]][COORDINATES[1]] = "_"
                                del objects[key]
                            else: # if it's a boulder or moving in perpendicular axis
                                objects[key][f"velocity_{axis}"] = 0
                        elif value[f"velocity_{axis}"] * VECTOR_SUMS[axis_index] < 0: # if one negative and the other positive
                            objects[key][f"velocity_{axis}"] = VECTOR_SUMS[axis_index] + (1 if VECTOR_SUMS[axis_index] < 0 else -1) 
                            if not water[NEW_KEY][f"velocity_{['y', 'x'][1-axis_index]}"]:
                                del water[NEW_KEY]
                                board[COORDINATES[0]][COORDINATES[1]] = "_"
                                objects[NEW_KEY] = objects[key]
                                del objects[key]
                                board[NEW_COORDINATES[0]][NEW_COORDINATES[1]] = "b" if objects == boulders else "w" if objects == water else "f" if objects == fireballs else "e"
            value["velocity_x"] += 1 if value["velocity_x"] < 0 else (-1 if value["velocity_x"] else 0)
            value["velocity_y"] += 1 if value["velocity_y"] < 0 else (-1 if value["velocity_y"] else 0)
          elif objects == fireballs:
              fireball_explode(COORDINATES[0], COORDINATES[1], source_name=None, infused=value["infused"])
              board[COORDINATES[0]][COORDINATES[1]] = "_"
              del fireballs[key]
          elif objects == water:
              board[COORDINATES[0]][COORDINATES[1]] = "_"
              del water[key]

      if current_time >= AVALANCHE_STARTING_TIME and current_time % AVALANCHE_PERIODICITY == AVALANCHE_STARTING_TIME % AVALANCHE_PERIODICITY:
        AXIS = current_time // AVALANCHE_PERIODICITY % 2
        for direction in [0, 1]:
            for y in [avalanche_progress[AXIS] if direction else SIDE_LENGTH-1 - avalanche_progress[AXIS]] if AXIS else range(SIDE_LENGTH):
                for x in [avalanche_progress[1-AXIS] if direction else SIDE_LENGTH-1 - avalanche_progress[1-AXIS]] if 1-AXIS else range(SIDE_LENGTH):
                    if board[y][x] != board[y][x].lower(): # to check if there's a player, since "_" == "_".lower() is True
                        displace(y, x, AXIS, direction)
                    elif board[y][x] == "f":
                        fireball_explode(y, x)
                        del fireballs[f"{y} {x}"]
                    elif board[y][x] == "w":
                        del water[f"{y} {x}"]
                    elif board[y][x] == "b":
                        del boulders[f"{y} {x}"]
                    board[y][x] = "p"
        avalanche_progress[AXIS] += 1
      current_time += 1
      max_shield -= 1 if not random.randint(0, 4) and max_shield else 0
      if PAUSE_BETWEEN_TURNS and not ("Player" in reaction_times and people["Player"]["buisness_card"]["hybernation"]):
        input("\nPress enter to continue ")
      clear() # remove # when not debugging, add # when debugging
      if "Player" not in reaction_times:
          for death_message in death_message_queue:
            display_info_message(death_message)
    for moment in history:
      display_map(moment)
      print("")
    display_map(board)
    try:
        WINNER = list(reaction_times.keys())[0]
    except IndexError:
        REMAINING_PLAYERS = [death_message[0] for death_message in death_message_queue]
        fastest = {}
        for remaining_player in REMAINING_PLAYERS:
            if not fastest or final_reaction_times[remaining_player] < list(fastest.values())[0]:
               fastest = {remaining_player: final_reaction_times[remaining_player]}
        WINNER = list(fastest.keys())[0]
    print(f"The winner is {WINNER}")
    previous_winner = WINNER
    
    if win_counts_data is not None:
        win_counts[WINNER[0]] += 1
        # save win counts to file
        with open(file_path, "w") as file:
            file.write(",".join([f"{player[0]}{win_counts[player]}" for player in win_counts]))

        # display graph if asked for
        if PAUSE_BETWEEN_ROUNDS and input().lower() == "plt":
            plt.pie(win_counts.values(), labels=win_counts.keys(), autopct='%1.1f%%')
            plt.axis("equal")
            plt.show()
    else:
        # save win counts to file
        with open(file_path, "w") as file:
            file.write(",".join([f"{player[0]}0" for player in people]))
except KeyboardInterrupt:
    pass