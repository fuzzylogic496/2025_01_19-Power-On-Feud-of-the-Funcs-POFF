from config import *
import state

from copy import deepcopy 
import os
import random
import math
import itertools
from typing import Optional
import numpy as np

def get_input(prompt, options, names, entity_type="bot"):
    result = None
    while result is None:
        result = input(prompt)
        if result in ["help", "h", "0", ""]:
            if entity_type == "bot":
                print("Write your input as 2 to 4 numbers seperated by spaces.\nThe first represents the command, what you want to do\nIf you picked a command other than meditate or hybernate, then the second number represents the specifier for that action (for example what spell if the action was cast spell)\nThe second option if you picked meditate or hybernate and the third option otherwise is the orientation you wish to face after the turn is over\nThe potential final option is an optional degree specifier, see the list below for when that happens")
                for index, option in enumerate(options):
                    print(f"{index+1}. {COMMANDS[index].replace('_', ' ')}{' (optional: specify distance 1 or 2 if facing movement direction, otherwise max)' if COMMANDS[index] == 'move' else ''}")
                    if type(option[0]) == list:
                        for sub_index, sub_option in enumerate(names[index]):
                            print(f"\u2008{sub_index+1}. {sub_option}{' (manditory: specify element)' if COMMANDS[index] == 'cast_spell' and names[index][sub_index] == 'summon_elemental' else ''}{' (optional: specify amount of mana used, otherwise max)' if (COMMANDS[index] == 'cast_spell' and names[index][sub_index] == 'shield') else ''}{' (optional: specify charge time, otherwise 2 turns)' if (COMMANDS[index] == 'physical_attack' and names[index][sub_index] == 'charge') else ''}")
                            if COMMANDS[index] == 'cast_spell' and names[index][sub_index] == 'summon_elemental':
                                for sub_sub_index, sub_sub_option in enumerate(ELEMENT_TO_SPELL):
                                    print(f"\u2008\u2008{sub_sub_index+1}. {sub_sub_option}")
                print("For orientation:")
                for index, orientation in enumerate(CARDINAL_DIRECTIONS):
                    print(f"{index+1}. {orientation}")
            elif entity_type == "elemental":
                print("Write your input as 2 to 4 numbers seperated by spaces.\nThe first represents the command, what you want to do\nIf you used move, the second number represents the direction\nThe second number if you used cast spell and the third number if you moved is the orientation you wish to face after the turn is over\nThe potential final option is an optional distance specifier, which is how far you want to move. Default is as far as possible")
                
                print("For direction and orientation:")
                for index, orientation in enumerate(CARDINAL_DIRECTIONS):
                    print(f"{index+1}. {orientation}")
            else:
                raise Exception(f"Entity type {entity_type} not recognized")
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

def closest_and_furthest_axis(coords):
    y, x = tuple(coords)
    assert y >= 0
    assert x >= 0
    north_dist = y
    south_dist = SIDE_LENGTH - 1 - y
    west_dist = x
    east_dist = SIDE_LENGTH - 1 - x
    
    min_dist = min(north_dist, south_dist, west_dist, east_dist)
    
    if min_dist == north_dist:
        closest = "north"
        furthest_perpendicular = "east" if east_dist > west_dist else "west"
    elif min_dist == south_dist:
        closest = "south"
        furthest_perpendicular = "east" if east_dist > west_dist else "west"
    elif min_dist == west_dist:
        closest = "west"
        furthest_perpendicular = "north" if north_dist > south_dist else "south"
    else:
        closest = "east"
        furthest_perpendicular = "north" if north_dist > south_dist else "south"
    
    return closest, min_dist, furthest_perpendicular

def rotate(orientation, coordinates): 
    ORIENTATION_OPTIONS = set(get_viable_cardinal_directions(coordinates)) - {orientation}
    assert len(ORIENTATION_OPTIONS)
    new_orientation = orientation
    while new_orientation not in ORIENTATION_OPTIONS:
        new_orientation = CARDINAL_DIRECTIONS[CARDINAL_DIRECTIONS.index(new_orientation)-1]
    return new_orientation

def next_to_wall(coordinates):
    y, x = coordinates
    return y == state.avalanche_progress[1] or y == SIDE_LENGTH - 1 - state.avalanche_progress[1] or x == state.avalanche_progress[0] or x == SIDE_LENGTH - 1 - state.avalanche_progress[0]

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

def sgn(x):
    return x / abs(x) if x else 0

def set_map(SIDE_LENGTH):
  state.board = []
  for _ in range(SIDE_LENGTH): # y
    state.board.append([])
    for _ in range(SIDE_LENGTH): # x
      state.board[-1].append("_")
  return state.board

def decline(t, s, b=2): return (s * t + b * 255)/(t + b)

def rgb_text(r, g, b, text): return f"\033[38;2;{int(r)};{int(g)};{int(b)}m{text}\033[0m"

def set_brightness(value, text):
    return rgb_text(value, value, value, text)

def display_map(board, expected_character_count=1, lightness_map=deepcopy(PURE_WHITE_LIGHTNESS_MAP), red=False):
  for y in range(SIDE_LENGTH):
    row = ""
    for x in range(SIDE_LENGTH):
      if red:
        row += rgb_text(lightness_map[y][x], 0, 0, board[y][x])
      elif board[y][x].isupper() and state.bots[state.letters[board[y][x]]]["visible_stats"]["infused"] or (board[y][x] == "e" and f"{y} {x}" in state.elementals and state.elementals[f"{y} {x}"]["visible_stats"]["infused"]):
        row += rgb_text(lightness_map[y][x]/255 * 106, lightness_map[y][x]/255 * 13, lightness_map[y][x]/255 * 173, board[y][x])
      elif board[y][x].isupper() and state.bots[state.letters[board[y][x]]]["hexed"] is not None:
        row += rgb_text(lightness_map[y][x], 0, lightness_map[y][x], board[y][x])
      elif board[y][x].isupper() and state.bots[state.letters[board[y][x]]]["invisibility"]:
        row += rgb_text(0, 0, lightness_map[y][x], board[y][x])
      elif board[y][x].isupper() and state.bots[state.letters[board[y][x]]]["visible_stats"]["stun"]:
        row += rgb_text(lightness_map[y][x], lightness_map[y][x], 0, board[y][x])
      elif board[y][x].isupper() and state.bots[state.letters[board[y][x]]]["visible_stats"]["enhancement"]:
        row += rgb_text(lightness_map[y][x], 0, 0, board[y][x])
      elif board[y][x].isupper() and state.bots[state.letters[board[y][x]]]["visible_stats"]["crippled"]:
        REMAINING_CRIPPLE_TIME = state.bots[state.letters[board[y][x]]]["visible_stats"]["crippled"]
        row += rgb_text(lightness_map[y][x]/255 * decline(REMAINING_CRIPPLE_TIME, 97), lightness_map[y][x]/255 * decline(REMAINING_CRIPPLE_TIME, 58), lightness_map[y][x]/255 * decline(REMAINING_CRIPPLE_TIME, 34), board[y][x])
      elif board[y][x].isupper() and state.bots[state.letters[board[y][x]]]["visible_stats"]["slowness"]:
        row += rgb_text(lightness_map[y][x]/2, lightness_map[y][x]/2, lightness_map[y][x], board[y][x])
      else:
        row += set_brightness(lightness_map[y][x], board[y][x])
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

def opposite_orientation(orientation: Optional[str]) -> Optional[str]:
    """
    Returns the opposite orientation of the given orientation.

    Args:
        orientation (str | None): The orientation to be reversed. If `None`, the
            function returns `None`. The function is case-insensitive.

    Returns:
        str | None: The opposite orientation, or `None` if `orientation` is `None`
        or not recognized.
    """
    if orientation is None:
        return None

    mapping = {
        "north": "south",
        "south": "north",
        "east": "west",
        "west": "east",
    }
    return mapping.get(orientation.lower())

def get_deltas(direction):
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

def retreat(current_orientation, coordinates, not_sideways=True):
    possible_directions = CARDINAL_DIRECTIONS.copy()

    if not_sideways:
        possible_directions = [direction for direction in possible_directions if direction in [current_orientation, opposite_orientation(current_orientation)]]

    random.shuffle(possible_directions)

    if possible_directions[0] == "north" and coordinates[0] == 0:
        possible_directions.remove("north")
    if possible_directions[0] == "south" and coordinates[0] == SIDE_LENGTH - 1:
        possible_directions.remove("south")
    if possible_directions[0] == "west" and coordinates[1] == 0:
        possible_directions.remove("west")
    if possible_directions[0] == "east" and coordinates[1] == SIDE_LENGTH - 1:
        possible_directions.remove("east")

    return "move " + possible_directions[0] + " 4"

def is_hostile(stats, target):
    if stats["visible_stats"]["type"] == "bot":
        if stats["hexed"] is None:
            SOURCE_NAME = stats["visible_stats"]["name"]
            if TEAM_MODE:
                SOURCE_TEAM_INDEX = stats["visible_stats"]["team"]
                SOURCE_TEAM_MEMBERS = TEAMS[stats["visible_stats"]["team"]]
        else:
            SOURCE_NAME = stats["hexed"]["source"]    
    else:
        SOURCE_NAME = stats["visible_stats"]["allegiance"]
    if TEAM_MODE and not ("SOURCE_TEAM_INDEX" in locals()):
        for team_index, team_members in enumerate(TEAMS):
            if SOURCE_NAME in team_members:
                SOURCE_TEAM_INDEX = team_index
                SOURCE_TEAM_MEMBERS = team_members
                break
    if target["type"] == "bot":
        return target["name"] != SOURCE_NAME and ((not TEAM_MODE) or (target["team"] != SOURCE_TEAM_INDEX))
    if target["type"] == "elemental":
        return target["allegiance"] != SOURCE_NAME and ((not TEAM_MODE) or target["allegiance"] not in SOURCE_TEAM_MEMBERS)
    return False

def enemies_spotted(stats, memory_map):
    """
    Identify all enemies on the map as well as their location and when they were last seen

    Args:
        stats (dict): The stats of the bot
        memory_map (list): The bot's memory map
    
    Returns:
        dict: A dictionary of enemies with their coordinates and time since last seen, sorted by least time since seen in ascending order
    """

    enemies = {}
    
    # go through each square and check for enemies
    for y in range(SIDE_LENGTH):
        for x in range(SIDE_LENGTH):
            if memory_map[y][x][0].isupper() and is_hostile(stats, state.bots[state.letters[memory_map[y][x][0]]]["visible_stats"]) \
            and (memory_map[y][x][1] < enemies.get(state.letters[memory_map[y][x][0]], {"time_since_seen": float("inf")})["time_since_seen"]):
                enemies[state.letters[memory_map[y][x][0]]] = {
                    "coordinates": (y, x),
                    "time_since_seen": memory_map[y][x][1]
                }

    # sort by least time since seen
    enemies = dict(sorted(enemies.items(), key=lambda item: item[1]["time_since_seen"]))

    return enemies

def displace(y, x, axis, direction):
    if not (state.board[y][x].isupper() or state.board[y][x] == "e"):
        raise Exception(f"Invalid target: {state.board[y][x]}")
    target_name = state.letters[state.board[y][x]] if state.board[y][x].isupper() else f"{y} {x}"
    new_key = target_name
    damage(target_name, ATTACK_DAMAGE["avalanche"], DEATH_MESSAGES["avalanche"])
    if (target_name[0].isupper() and target_name in state.reaction_times) or (not target_name[0].isupper() and target_name in state.elementals):
        new_coordinates = [y + (2*direction-1 if   axis else 0),
                           x - (2*direction-1 if 1-axis else 0)]
        # (2*direction - 1) and <
        """print(f"Displacing {target_name} to {new_coordinates}") # debug
        print(f"Currently it's {state.board[new_coordinates[0]][new_coordinates[1]]}") # debug
        print(f"new x would = {x + ((2*direction - 1)*(-1 if x < SIDE_LENGTH // 2 else 1) if 1-axis else 0)} because x = {x}, direction = {direction}, axis = {axis}")""" # debug
        if state.board[new_coordinates[0]][new_coordinates[1]] == "_":
            pass
        elif state.board[new_coordinates[0]][new_coordinates[1]].isupper():
            displace(new_coordinates[0], new_coordinates[1], axis, direction)
            print(f"Displacing {target_name} to {new_coordinates}") # debug
        elif state.board[new_coordinates[0]][new_coordinates[1]] == "f":
            fireball_explode(new_coordinates[0], new_coordinates[1], source_name=None, infused=state.fireballs[f"{new_coordinates[0]} {new_coordinates[1]}"]["infused"])
        elif state.board[new_coordinates[0]][new_coordinates[1]] == "w":
            new_key = f"{new_coordinates[0]} {new_coordinates[1]}"
            del state.water[new_key]
            damage(target_name, ATTACK_DAMAGE["wave"], DEATH_MESSAGES["wave"], False, "water")
            if (target_name[0].isupper() and state.bots[target_name]["hp"] <= 0) or (not target_name[0].isupper() and target_name not in state.elementals):
                state.board[new_coordinates[0]][new_coordinates[1]] = "_"
        elif state.board[new_coordinates[0]][new_coordinates[1]] in ["b", "p", "i"]:
            if target_name[0].isupper():
                TOTAL_TARGET_HP = state.bots[target_name]["hp"] + state.bots[target_name]["shield"]
            else:
                try:
                    TOTAL_TARGET_HP = state.elementals[target_name]["hp"]
                except KeyError:
                    display_map(state.board)
                    raise Exception(f"target_name: {target_name}, target_name[0].isupper(): {target_name[0].isupper()}, state.board[y][x]: {state.board[y][x]}, state.board[new_coordinates[0]][new_coordinates[1]]: {state.board[new_coordinates[0]][new_coordinates[1]]}, y: {y}, x: {x}, new_coordinates: {new_coordinates}, direction: {direction}, axis: {axis}, new_coordinates[axis]: {new_coordinates[axis]}") # debug
            damage(target_name, TOTAL_TARGET_HP, DEATH_MESSAGES["avalanche"])
        elif state.board[new_coordinates[0]][new_coordinates[1]] == "e":
            target_name = displace(new_coordinates[0], new_coordinates[1], axis, direction)
        
        if target_name[0].isupper() and state.bots[target_name]["hp"] > 0:
            state.board[new_coordinates[0]][new_coordinates[1]] = state.board[y][x]
            state.bots[target_name]["coordinates"] = new_coordinates
        elif not target_name[0].isupper() and new_key in state.elementals:
            new_key = move(target_name, 1, new_coordinates[1] - x, new_coordinates[0] - y)
    return new_key

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

def get_target(coordinates, delta_x, delta_y, respect_invisibility=True, is_bot=True):
    ELEMENTAL_KEY = f"{coordinates[0]} {coordinates[1]}"
    if not is_bot:
        ELEMENTAL_INFUSED = state.elementals[ELEMENTAL_KEY]["visible_stats"]["infused"]
    if is_bot:
        bot_name = state.letters[state.board[coordinates[0]][coordinates[1]]]
        if bot_name == "perimeter":
            for xdim in [-1, 0, 1]:
                for ydim in [-1, 0, 1]:
                    letter = state.board[coordinates[0]+xdim][coordinates[1]+ydim]
                    print(letter) # debug
                    if letter.isupper():
                        print(state.bots[state.letters[letter]]) # debug
            raise Exception(f"bot_name: {bot_name}, coordinates: {coordinates}, delta_x: {delta_x}, delta_y: {delta_y}, respect_invisibility: {respect_invisibility}, is_bot: {is_bot}")
        state.bot_memory_maps[bot_name if not state.bots[bot_name]["hexed"] else state.bots[bot_name]["hexed"]["source"]][coordinates[0]][coordinates[1]] = [bot_name[0], 0]
    elif ELEMENTAL_INFUSED:
        state.bot_memory_maps[state.elementals[ELEMENTAL_KEY]["visible_stats"]["allegiance"]][coordinates[0]][coordinates[1]] = ["e", 0]
    target_letter = "p"
    
    for square in range(coordinates[delta_x]+(delta_x+delta_y), SIDE_LENGTH if delta_x+delta_y == 1 else -1, (delta_x+delta_y)):
        target_letter = state.board[square if delta_y else coordinates[0]][square if delta_x else coordinates[1]]
        if is_bot:
            state.bot_memory_maps[bot_name if not state.bots[bot_name]["hexed"] else state.bots[bot_name]["hexed"]["source"]][square if delta_y else coordinates[0]][square if delta_x else coordinates[1]] = [target_letter, 0]
        elif ELEMENTAL_INFUSED:
            state.bot_memory_maps[state.elementals[ELEMENTAL_KEY]["visible_stats"]["allegiance"]][square if delta_y else coordinates[0]][square if delta_x else coordinates[1]] = [target_letter, 0]

        if target_letter != "_":
            if target_letter.isupper():  # to check if there's a bot_name there
                if respect_invisibility and state.bots[state.letters[target_letter]]["invisibility"]:  # if said bot_name is invisible
                    # pretends like there's nothing there
                    if is_bot:
                        state.bot_memory_maps[bot_name if not state.bots[bot_name]["hexed"] else state.bots[bot_name]["hexed"]["source"]][square if delta_y else coordinates[0]][square if delta_x else coordinates[1]] = ["_", 0]
                    elif ELEMENTAL_INFUSED:
                        state.bot_memory_maps[state.elementals[ELEMENTAL_KEY]["visible_stats"]["allegiance"]][square if delta_y else coordinates[0]][square if delta_x else coordinates[1]] = ["_", 0]
                    continue
            break
        else:
            target_letter = "p"

    if target_letter in ["b", "w", "f", "e", "i"]:
        KEY = f"{square if delta_y else coordinates[0]} {square if delta_x else coordinates[1]}"
        try:
            target = deepcopy((state.boulders if target_letter == "b" else state.water if target_letter == "w" else state.fireballs if target_letter == "f" else state.elementals if target_letter == "e" else state.ice_spikes)[KEY]["visible_stats"])
            target["distance"] = abs(coordinates[abs(delta_x)]-square)
            if target_letter == "e":
                target["hp_sector"] = ["very low", "low", "high", "very high"][min(state.elementals[KEY]["hp"] // (ELEMENTAL_STARTING_HP // 4), 3)]
        except KeyError:
            KEY_SPLITTED = list(map(int, KEY.split()))
            state.board[KEY_SPLITTED[0]][KEY_SPLITTED[1]] = "_"
            target_letter = "p"
    
    if target_letter == "p":
        square = -1+state.avalanche_progress[abs(delta_y)] if delta_x+delta_y == -1 else SIDE_LENGTH - state.avalanche_progress[abs(delta_y)]
        target = PERIMETER.copy()  # use deepcopy() if neccesary, although rn it isn't
        target["distance"] = abs(coordinates[delta_x]-square)
    elif target_letter not in ["b", "w", "f", "e", "i"]:
        if state.bots[state.letters[target_letter]]["hp"] > 0:
            target = deepcopy(state.bots[state.letters[target_letter]]["visible_stats"])
            target["distance"] = abs(coordinates[delta_x]-square)
            target["hp_sector"] = ["very low", "low", "high", "very high"][min(state.bots[state.letters[target_letter]]["hp"] // (STARTING_HP // 4), 3)]
        else:
            raise Exception(f"target: {state.bots[state.letters[target_letter]]['visible_stats']}, coordinates: {coordinates}, delta_x: {delta_x}, delta_y: {delta_y}, respect_invisibility: {respect_invisibility}, is_bot: {is_bot}")
    return target

def get_viable_cardinal_directions(coordinates):
    viable_cardinal_directions = CARDINAL_DIRECTIONS.copy()
    if coordinates[0] == state.avalanche_progress[0]:
       viable_cardinal_directions.remove("north")
    if coordinates[0] == SIDE_LENGTH - 1 - state.avalanche_progress[0]:
       viable_cardinal_directions.remove("south")
    if coordinates[1] == state.avalanche_progress[1]:
       viable_cardinal_directions.remove("west")
    if coordinates[1] == SIDE_LENGTH - 1 - state.avalanche_progress[1]:
       viable_cardinal_directions.remove("east")
    return viable_cardinal_directions

def deduce_coordinates(observer_coordinates, distance, delta_x, delta_y):
    return [observer_coordinates[0] + delta_y * distance, observer_coordinates[1] + delta_x * distance]

def damage(target_name, amount, potential_death_message="died", pierce=False, damage_element=None, source_name=None):
  if target_name[0].isupper(): # if the target is a bot
    # in case the target doesn't exist
    if target_name not in state.reaction_times:
        return
    
    # if the target is the bot_name and there is any damage
    if amount > 0 and target_name == "Player" and potential_death_message != DEATH_MESSAGES["infusion"]:
        state.player_just_took_damage = True

    # attack power is doubled if the target is hybernating
    if state.bots[target_name]["visible_stats"]["hybernation"]:
        amount *= 2

    if source_name == "elemental":
        amount *= ELEMENTAL_DAMAGE_MULTIPLIER

    amount = int(amount)

    excess_amount = 0
    defense = state.bots[target_name]["hp"] + (state.bots[target_name]["shield"] if not pierce else 0)
    if amount > defense:
        excess_amount = amount - defense

    
    if target_name == AI_NAME: # punishment for taking damage
        _add_reward_to_last_steps(state.memories[AI_NAME], -0.08 * (amount - excess_amount) * (2 if source_name == AI_NAME else 1), last_n=3)
    elif source_name == AI_NAME and "cast_spell mana_blast" not in state.bots[AI_NAME]["visible_stats"]["previous_action"]: # reward for damage dealt
        _add_reward_to_last_steps(state.memories[AI_NAME], +0.3 * (amount - excess_amount), last_n=(5 if damage_element in ["water", "fire"] else 2))
    

    # for shield damage
    if not pierce:
        state.bots[target_name]["shield"] -= amount
        if state.bots[target_name]["shield"] < 0:
            amount = -state.bots[target_name]["shield"]
            state.bots[target_name]["shield"] = 0
        else:
            amount = 0
        state.bots[target_name]["visible_stats"]["shield_sector"] = ["none", "weak", "moderate", "strong"][math.ceil((state.bots[target_name]["shield"]*3) / (MAX_MANA / MANA_COSTS["per_shield_hp"]))]
  
    # for any remaining damage to the target
    state.bots[target_name]["hp"] -= amount

    # if the attack kills the target
    if state.bots[target_name]["hp"] <= 0:
        # on R_bot death:
        if target_name == AI_NAME:
            _add_reward_to_last_steps(state.memories[AI_NAME], -50.0, last_n=2)
            state.time_r_bot_survived = state.current_time
        elif source_name == AI_NAME: # when R_bot kills an enemy:
            _add_reward_to_last_steps(state.memories[AI_NAME], +20.0, last_n=1)
        if CONFIRM_KILLS:
            state.death_message_queue.append([target_name, potential_death_message])
            for bot_name in state.reaction_times.copy():
                if state.bots[bot_name]["visible_stats"]["hybernation"]:
                    continue
                state.info_messages[bot_name].append(state.death_message_queue[-1])
        state.board[state.bots[target_name]["coordinates"][0]][state.bots[target_name]["coordinates"][1]] = "_"
        state.final_reaction_times[target_name] = state.reaction_times[target_name]
        del state.reaction_times[target_name]

        if source_name == "elemental":
            return

        # if the target was hexed, kill credit goes to the hexer
        if source_name == target_name and state.bots[target_name]["hexed"] is not None:
            source_name = state.bots[target_name]["hexed"]["source"]
            
        # rewards for the killer
        if source_name is not None and source_name in state.reaction_times:
            EXTRA = state.bots[source_name]["hp"] // 4 if state.bots[source_name]["hp"] <= STARTING_HP else (state.bots[source_name]["hp"] - STARTING_HP) // 4
            assert EXTRA >= 0
            if DEBUG_MODE:
                input(f"Source: {source_name}, Target: {target_name}") # debug
            state.bots[source_name]["hp"] = max(STARTING_HP, state.bots[source_name]["hp"])
            state.bots[source_name]["hp"] += int(EXTRA * (MANA_FROM_MANA_BLAST_KILL_MULTIPLIER if potential_death_message == DEATH_MESSAGES["mana_blast"] else 1)) # using the same multiplier as for mana. Can change if needed
            state.bots[source_name]["mana"] = min(MAX_MANA, state.bots[source_name]["mana"] + int(MANA_FROM_KILL * (MANA_FROM_MANA_BLAST_KILL_MULTIPLIER if potential_death_message == DEATH_MESSAGES["mana_blast"] else 1)))
  elif damage_element != state.elementals[target_name]["visible_stats"]["element"]: # if the target is an elemental and it's not their element
    amount = int(amount)
    state.elementals[target_name]["hp"] -= amount
    if state.elementals[target_name]["hp"] <= 0:
        COORDINATES = list(map(int, target_name.split()))
        state.board[COORDINATES[0]][COORDINATES[1]] = "_"
        if state.elementals[target_name]["visible_stats"]["element"] == "earth":
            state.board[COORDINATES[0]][COORDINATES[1]] = "b"
            state.boulders[f"{COORDINATES[0]} {COORDINATES[1]}"] = deepcopy(BOULDER)
            state.boulders[f"{COORDINATES[0]} {COORDINATES[1]}"]["visible_stats"]["infused"] = state.elementals[target_name]["visible_stats"]["infused"]
            state.boulders[f"{COORDINATES[0]} {COORDINATES[1]}"]["visible_stats"]["crippled"] = state.elementals[target_name]["visible_stats"]["crippled"]
        elif state.elementals[target_name]["visible_stats"]["element"] == "fire":
            fireball_explode(COORDINATES[0], COORDINATES[1], source_name=None, infused=state.elementals[target_name]["visible_stats"]["infused"], crippled=state.elementals[target_name]["visible_stats"]["crippled"])
        del state.elemental_memories[state.elementals[target_name]["visible_stats"]["allegiance"]][target_name]
        del state.elementals[target_name]

        if source_name == "elemental":
            return

        # if the target was hexed, kill credit goes to the hexer
        if source_name == target_name and state.bots[target_name]["hexed"] is not None:
            source_name = state.bots[target_name]["hexed"]["source"]

        # reward for the killer
        if source_name is not None and source_name in state.reaction_times:
            state.bots[source_name]["mana"] = min(MAX_MANA, state.bots[source_name]["mana"] + int(MANA_FROM_ELEMENTAL_KILL * (MANA_FROM_MANA_BLAST_KILL_MULTIPLIER if potential_death_message == DEATH_MESSAGES["mana_blast"] else 1)))

def fireball_explode(fireball_y, fireball_x, source_name, infused=False, crippled=0):
  INFUSION_MULTIPLIER = 2 if infused else 1
  CRIPPLE_MULTIPLIER = calculate_cripple_effect(crippled)
  if state.board[fireball_y][fireball_x] == "f":
    state.board[fireball_y][fireball_x] = "_"
  for relative_x in range(-2, 3):
    for relative_y in range(-2, 3):
        if fireball_y + relative_y < 0 or fireball_y + relative_y >= SIDE_LENGTH or fireball_x + relative_x < 0 or fireball_x + relative_x >= SIDE_LENGTH:
          continue
        target = state.board[fireball_y+relative_y][fireball_x+relative_x]
        distance = max(abs(relative_x), abs(relative_y))
        POTENTIAL_DEATH_MESSAGE = DEATH_MESSAGES["fireball"] if distance == 0 else DEATH_MESSAGES["explosion_1"] if distance == 1 else DEATH_MESSAGES["explosion_2"]
        if target.isupper() or target == "e":
            if target.isupper():
                TARGET_NAME = state.letters[target]
            else:
                TARGET_NAME = f"{fireball_y+relative_y} {fireball_x+relative_x}"
            damage(TARGET_NAME, CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * (ATTACK_DAMAGE["fireball"] if distance == 0 else ATTACK_DAMAGE["explosion_1"] if distance == 1 else ATTACK_DAMAGE["explosion_2"]), POTENTIAL_DEATH_MESSAGE, False, "fire", source_name)
        elif target == "f":
            fireball_explode(fireball_y+relative_y, fireball_x+relative_x, source_name, infused=state.fireballs[f"{fireball_y+relative_y} {fireball_x+relative_x}"]["infused"], crippled=state.fireballs[f"{fireball_y+relative_y} {fireball_x+relative_x}"]["visible_stats"]["crippled"])

def add_bot(name, func, elemental_protocol=None):
    state.bots[name] = deepcopy(BOT)
    state.bots[name]["visible_stats"]["name"] = name
    state.reaction_times[name] = random.random()
    state.player_funcs[name] = func
    if state.memories.get(name) is None:
        state.memories[name] = []
    state.elemental_memories[name] = dict()
    state.bots[name]["elemental_protocol"] = elemental_protocol
    state.letters[name[0]] = name
    state.info_messages[name] = []
    if TEAM_MODE:
        for index, team in enumerate(TEAMS):
            if name in team:
                break
        state.bots[name]["visible_stats"]["team"] = index
        state.bot_memory_maps[name] = state.team_memory_maps[state.bots[name]["visible_stats"]["team"]]
    else:
        state.bot_memory_maps[name] = deepcopy(BLANK_MEMORY_MAP)

def delete_self_func(stats, target, memory, info_messages):
    raise KeyboardInterrupt

def move(name, distance, delta_x, delta_y):
    IS_PLAYER = name[0].isupper()
    if IS_PLAYER:
        coordinates = state.bots[name]["coordinates"]
        IS_SLOWED = state.bots[name]["visible_stats"]["slowness"]
    else:
        coordinates = list(map(int, name.split()))
        IS_SLOWED = state.elementals[name]["visible_stats"]["slowness"]
    current_key = name
    if IS_SLOWED:
        distance = 1
    for _ in range(distance):
        INDEX_TOO_LOW = min(coordinates[0] + delta_y, coordinates[1] + delta_x, 0) < 0
        try:
            SQUARE_EMPTY = state.board[coordinates[0] + delta_y][coordinates[1] + delta_x] == "_"
            INDEX_TOO_HIGH = False
        except IndexError:
            INDEX_TOO_HIGH = True
        if not INDEX_TOO_HIGH and not INDEX_TOO_LOW:
            if SQUARE_EMPTY:
                state.board[coordinates[0]][coordinates[1]] = "_"
                if IS_PLAYER:
                    state.bot_memory_maps[name][coordinates[0]][coordinates[1]] = ["_", 0]
                    coordinates = [coordinates[0] + delta_y, coordinates[1] + delta_x]
                    state.bots[name]["coordinates"] = (coordinates[0], coordinates[1])
                    state.board[coordinates[0]][coordinates[1]] = name[0]
                    state.bot_memory_maps[name][coordinates[0]][coordinates[1]] = [name[0], 0]
                else: # if it's an elemental
                    if state.elementals[current_key]["visible_stats"]["infused"]:
                        state.bot_memory_maps[state.elementals[current_key]["visible_stats"]["allegiance"]][coordinates[0]][coordinates[1]] = ["_", 0]
                    coordinates = [coordinates[0] + delta_y, coordinates[1] + delta_x]
                    new_key = f"{coordinates[0]} {coordinates[1]}"
                    state.elementals[new_key] = state.elementals[current_key]
                    try:
                        state.elemental_memories[state.elementals[new_key]["visible_stats"]["allegiance"]][current_key] # debug
                    except KeyError:
                        raise Exception(f"Elemental memory for {current_key} not found when moving to {new_key}. Elemental stats: {state.elementals[current_key]}")
                    state.elemental_memories[state.elementals[new_key]["visible_stats"]["allegiance"]][new_key] = state.elemental_memories[state.elementals[new_key]["visible_stats"]["allegiance"]][current_key]
                    del state.elemental_memories[state.elementals[new_key]["visible_stats"]["allegiance"]][current_key]
                    del state.elementals[current_key]
                    state.board[coordinates[0]][coordinates[1]] = "e"
                    current_key = new_key
    return current_key # there is no return usually for the move function, so this will be ignored except the one place it's used

def charge(bot_name, delta_x, delta_y):
    PRE_DISTANCE = get_target(state.bots[bot_name]["coordinates"], delta_x, delta_y, False)["distance"]
    ENHANCEMENT_MULTIPLIER = 2 if state.bots[bot_name]["visible_stats"]["enhancement"] else 1
    CRIPPLE_MULTIPLIER = calculate_cripple_effect(state.bots[bot_name]["visible_stats"]["crippled"])
    target = get_target(state.bots[bot_name]["coordinates"], delta_x, delta_y, False)
    if PRE_DISTANCE <= 2 * ENHANCEMENT_MULTIPLIER:
        if target["type"] == "bot":
            TARGET_NAME = target["name"]
        elif target["type"] == "elemental":
            TARGET_NAME = f"{state.bots[bot_name]['coordinates'][0]+delta_y*PRE_DISTANCE} {state.bots[bot_name]['coordinates'][1]+delta_x*PRE_DISTANCE}"
        else:
            TARGET_NAME = bot_name # crashing into things makes you hurt yourself
        if target["type"] == "bot" and state.bots[TARGET_NAME]["visible_stats"]["is_parrying"]:
            damage(TARGET_NAME, ENHANCEMENT_MULTIPLIER * CRIPPLE_MULTIPLIER * ATTACK_DAMAGE["charge"] * (ENHANCEMENT_MULTIPLIER*state.bots[bot_name]["visible_stats"]["charge_progress"]+PRE_DISTANCE/2)**2, DEATH_MESSAGES["parry"]("ram", TARGET_NAME), False, source_name=TARGET_NAME)
            state.bots[TARGET_NAME]["visible_stats"]["is_parrying"] = False
        elif target["type"] == "water":
            damage(TARGET_NAME, ENHANCEMENT_MULTIPLIER * CRIPPLE_MULTIPLIER * ATTACK_DAMAGE["charge"] * (ENHANCEMENT_MULTIPLIER*state.bots[bot_name]["visible_stats"]["charge_progress"]+PRE_DISTANCE/2)**2 * CHARGE_INTO_WATER_MULTIPLIER, DEATH_MESSAGES["charge"], False, source_name=bot_name)
        else:
            damage(TARGET_NAME, ENHANCEMENT_MULTIPLIER * CRIPPLE_MULTIPLIER * ATTACK_DAMAGE["charge"] * (ENHANCEMENT_MULTIPLIER*state.bots[bot_name]["visible_stats"]["charge_progress"]+PRE_DISTANCE/2)**2, DEATH_MESSAGES["charge"], False, source_name=bot_name)
        if bot_name not in state.reaction_times:
            return
    state.bots[bot_name]["visible_stats"]["charge_progress"] += 1
    move(bot_name, ENHANCEMENT_MULTIPLIER * 2, delta_x, delta_y)
    if state.bots[bot_name]["visible_stats"]["charge_progress"] == state.bots[bot_name]["visible_stats"]["charge_destination"]:
        state.bots[bot_name]["visible_stats"]["charge_destination"] = state.bots[bot_name]["visible_stats"]["charge_progress"] = 0

def cast_fireball(coordinates, delta_x, delta_y, source_name, infused=False, crippled=0, **kwargs):
    try:
        state.board[coordinates[0] + delta_y][coordinates[1] + delta_x]
    except IndexError:
        pass
    else:
        if state.board[coordinates[0] + delta_y][coordinates[1] + delta_x] == "_":
            state.board[coordinates[0] + delta_y][coordinates[1] + delta_x] = "f"
            KEY = f"{coordinates[0] + delta_y} {coordinates[1] + delta_x}"
            state.fireballs[KEY] = deepcopy(FIREBALL)
            state.fireballs[KEY]["velocity_x"] = delta_x * FIREBALL_START_VELOCITY
            state.fireballs[KEY]["velocity_y"] = delta_y * FIREBALL_START_VELOCITY
            state.fireballs[KEY]["infused"] = infused
            state.fireballs[KEY]["source_name"] = source_name
        else:
            fireball_explode(coordinates[0] + delta_y, coordinates[1] + delta_x, source_name, infused)

def cast_wave(coordinates, delta_x, delta_y, source_name, infused=False, crippled=0, **kwargs):
    INFUSION_MULTIPLIER = 2 if infused else 1
    CRIPPLE_MULTIPLIER = calculate_cripple_effect(crippled)
    for x in range(-1, 2) if delta_y else [delta_x]:
        for y in [delta_y] if delta_y else range(-1, 2):
            try:
                if coordinates[0] + y < 0 or coordinates[1] + x < 0:
                    raise IndexError
                SQUARE = state.board[coordinates[0] + y][coordinates[1] + x]
                KEY = f"{coordinates[0] + y} {coordinates[1] + x}"
                if SQUARE in ["_", "i"]:
                    if SQUARE == "i":
                        del state.ice_spikes[KEY]
                    state.board[coordinates[0] + y][coordinates[1] + x] = "w"
                    KEY = f"{coordinates[0] + y} {coordinates[1] + x}"
                    state.water[KEY] = deepcopy(WATER)
                    state.water[KEY]["velocity_x"] = delta_x * WAVE_START_VELOCITY 
                    state.water[KEY]["velocity_y"] = delta_y * WAVE_START_VELOCITY
                    state.water[KEY]["infused"] = infused
                    state.water[KEY]["crippled"] = crippled
                    state.water[KEY]["source_name"] = source_name
                elif SQUARE.isupper() or SQUARE == "e":
                    damage(state.letters[SQUARE] if SQUARE.isupper() else KEY, CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["wave"], DEATH_MESSAGES["wave"], False, "water", source_name) # should we be multiplying the damage ...?
                    if SQUARE.isupper():
                        try:
                            # should we be multiplying the velocity ...?
                            state.bots[state.letters[SQUARE]]["velocity_x"] += delta_x * INFUSION_MULTIPLIER
                            state.bots[state.letters[SQUARE]]["velocity_y"] += delta_y * INFUSION_MULTIPLIER
                        except KeyError:
                            pass
                    elif KEY in state.elementals: # if elemental and still alive
                        state.elementals[KEY]["velocity_y"] += delta_y * INFUSION_MULTIPLIER
                        state.elementals[KEY]["velocity_x"] += delta_x * INFUSION_MULTIPLIER
                elif SQUARE in ["b", "w", "f"]:
                    objects = state.boulders if SQUARE == "b" else state.water if SQUARE == "w" else state.fireballs
                    objects[KEY]["velocity_y"] += delta_y * INFUSION_MULTIPLIER
                    objects[KEY]["velocity_x"] += delta_x * INFUSION_MULTIPLIER
                else:
                    assert SQUARE == "p"
            except IndexError:
                pass

def cast_wind(coordinates, delta_x, delta_y, target, source_name, infused=False, crippled=0, **kwargs):
    # calculates infusion and cripple multipliers, which influence the velocity given by the wind in addition to damage
    INFUSION_MULTIPLIER = 2 if infused else 1
    CRIPPLE_MULTIPLIER = calculate_cripple_effect(crippled)

    if target["type"] in ["boulder", "fireball", "water", "elemental"]: # if the target is an object
        # identifies the target
        KEY = f"{coordinates[0]+target['distance']*delta_y} {coordinates[1]+target['distance']*delta_x}"
        target_nonplayer = (state.boulders if target["type"] == "boulder" else state.water if target["type"] == "water" else state.fireballs if target["type"] == "fireball" else state.elementals)[KEY]

        # if the wind changes direction in at least one axis, the kill credit for the object goes to the wind caster
        if any([sgn(target_nonplayer[f"velocity_{axis}"]) != sgn(WIND_KNOCKBACK * (delta_y if axis == "y" else delta_x) * CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER) for axis in ["x", "y"]]):
            target_nonplayer["source_name"] = source_name
            if DEBUG_MODE:
                input(f"Source: {source_name}, Target: {KEY}") # debug
        
        # applies velocity to the target object
        target_nonplayer["velocity_y"] += int(WIND_KNOCKBACK * delta_y * CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER)
        target_nonplayer["velocity_x"] += int(WIND_KNOCKBACK * delta_x * CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER)

        # if the target is an elemental, it takes damage
        if target["type"] == "elemental": 
            damage(KEY, CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["wind"], DEATH_MESSAGES["wind"], False, "wind", source_name)
    elif target["type"] == "bot": # if the target is a bot
        # applies velocity to the target
        state.bots[target["name"]]["velocity_y"] += int(WIND_KNOCKBACK * delta_y * CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER)
        state.bots[target["name"]]["velocity_x"] += int(WIND_KNOCKBACK * delta_x * CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER)

        # damages the target
        damage(target["name"], CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["wind"], DEATH_MESSAGES["wind"], False, "wind", source_name)

def cast_lightning(coordinates, delta_x, delta_y, target, source_name, infused=False, crippled=0, **kwargs):
    INFUSION_MULTIPLIER = 2 if infused else 1
    CRIPPLE_MULTIPLIER = calculate_cripple_effect(crippled)
    if target["type"] == "bot":
        damage(target["name"], CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["lightning_bolt"], DEATH_MESSAGES["lightning_bolt"], False, "lightning", source_name)
    elif target["type"] == "elemental":
        KEY = f"{coordinates[0] + delta_y * target['distance']} {coordinates[1] + delta_x * target['distance']}"
        damage(KEY, CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["lightning_bolt"], DEATH_MESSAGES["lightning_bolt"], False, "lightning")
    elif target["type"] == "ice_spike":
        KEY = f"{coordinates[0] + delta_y * target['distance']} {coordinates[1] + delta_x * target['distance']}"
        del state.ice_spikes[KEY]
        state.board[int(KEY.split()[0])][int(KEY.split()[1])] = "_"

def cast_shockwave(coordinates, delta_x, delta_y, source_name, infused=False, crippled=0, **kwargs):
    INFUSION_MULTIPLIER = 2 if infused else 1
    CRIPPLE_MULTIPLIER = calculate_cripple_effect(crippled)
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
            SQUARE = state.board[y][x]
            if SQUARE != "_":
                if SQUARE in ["b", "w", "f", "e"]:
                    KEY = f"{y} {x}"
                    objects = state.boulders if SQUARE == "b" else state.water if SQUARE == "w" else state.fireballs if SQUARE == "f" else state.elementals
                    if SQUARE == "f":
                        fireball_explode(y, x, None)
                        del state.fireballs[KEY]
                    elif SQUARE == "b" and IS_CRIT:
                        state.board[y][x] = "_"
                        del state.boulders[KEY]
                    else:
                        objects[KEY]["velocity_x"] += delta_x * INFUSION_MULTIPLIER
                        objects[KEY]["velocity_y"] += delta_y * INFUSION_MULTIPLIER
                        if SQUARE == "e":
                            DAMAGE_LEVEL = 1 if max(abs(y - coordinates[0]), abs(x - coordinates[1])) == 1 else 2
                            if bool(random.randint(0, 2)) ^ (not IS_CRIT):
                                state.elementals[KEY]["visible_stats"]["stun"] = 1
                            damage(KEY, CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE[f"shockwave_{DAMAGE_LEVEL}{'_crit' if IS_CRIT else ''}"], DEATH_MESSAGES["shockwave"], False, "earth")
                elif SQUARE == "i":
                    del state.ice_spikes[f"{y} {x}"]
                    state.board[y][x] = "_"
                elif SQUARE != "p":
                    state.bots[state.letters[SQUARE]]["velocity_x"] += delta_x
                    state.bots[state.letters[SQUARE]]["velocity_y"] += delta_y
                    DAMAGE_LEVEL = 1 if max(abs(y - coordinates[0]), abs(x - coordinates[1])) == 1 else 2
                    damage(state.letters[SQUARE], CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE[f"shockwave_{DAMAGE_LEVEL}{'_crit' if IS_CRIT else ''}"], DEATH_MESSAGES["shockwave"], False, "earth", source_name)
                    if bool(random.randint(0, 2)) ^ (not IS_CRIT):
                        state.bots[state.letters[SQUARE]]["visible_stats"]["stun"] = 1
        except IndexError:
            continue

def cast_life_drain(coordinates, delta_x, delta_y, target, name, source_name, infused=False, crippled=0, **kwargs):
    INFUSION_MULTIPLIER = 2 if infused else 1
    CRIPPLE_MULTIPLIER = calculate_cripple_effect(crippled)
    SOURCE_IS_PLAYER = name[0].isupper()
    if target["type"] == "bot":
        damage(target["name"], CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["life_drain"], DEATH_MESSAGES["life_drain"], True, "darkness", source_name)

        # they only get to heal if it's attacking another bot, not elemental
        HEAL_AMOUNT = int((CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["life_drain"]) / 2)
        if SOURCE_IS_PLAYER:
            state.bots[name]["hp"] += HEAL_AMOUNT
        else:
            state.bots[state.elementals[name]["visible_stats"]["allegiance"]]["hp"] += HEAL_AMOUNT
    elif target["type"] == "elemental":
        KEY = f"{coordinates[0] + delta_y * target['distance']} {coordinates[1] + delta_x * target['distance']}"
        damage(KEY, CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["life_drain"], DEATH_MESSAGES["life_drain"], True, "darkness")
        # the bot_name also heals if it's attacking an elemental and the attacker is infused. This is because then the elemental's leader also gets damaged
        if (SOURCE_IS_PLAYER and state.bots[name]["visible_stats"]["infused"]) or (not SOURCE_IS_PLAYER and state.elementals[name]["visible_stats"]["infused"]): 
            damage(state.elementals[KEY]["visible_stats"]["allegiance"], CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["life_drain"], DEATH_MESSAGES["life_drain"], pierce=True, damage_element="darkness")
            HEAL_AMOUNT = (CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * ATTACK_DAMAGE["life_drain"]) // 2
            if SOURCE_IS_PLAYER:
                state.bots[name]["hp"] += HEAL_AMOUNT
            else:
                state.bots[state.elementals[name]["visible_stats"]["allegiance"]]["hp"] += HEAL_AMOUNT

def cast_ice_spikes(coordinates, delta_x, delta_y, source_name, infused=False, crippled=0, **kwargs):
    if any([coordinate < 0 for coordinate in coordinates]):
        raise Exception(coordinates)
    for square in range(coordinates[delta_x]+(delta_x+delta_y), SIDE_LENGTH if delta_x+delta_y == 1 else -1, (delta_x+delta_y)):
        state.future_ice_spikes.append(
            {
                "coordinates": [coordinates[0]*abs(delta_x) + abs(delta_y) * square, coordinates[1]*abs(delta_y) + abs(delta_x) * square], 
                "time_until_emergence": abs(square - coordinates[delta_x]) - 1, 
                "source_name": source_name, 
                "infused": infused, 
                "crippled": crippled
            }
        )

def calculate_cripple_effect(time_remaining):
    return 1 if not time_remaining else CRIPPLE_EFFECT_ASYMPTOTE + (1 - CRIPPLE_EFFECT_ASYMPTOTE) * math.exp(-math.log(3) * time_remaining / CRIPPLE_TIME_FOR_HALF_DAMAGE) # conditional not required, but saves a lot of time since time_remaining is often 0

def softmax(x):
    e = np.exp(x - np.max(x))
    return e / e.sum()

def _add_reward_to_last_steps(memory, reward, last_n=1):
    print(f"reward: {reward}. last_n: {last_n}") # debug
    traj = memory.get("rbot_traj_current")
    if not traj:
        return
    for i in range(1, min(last_n, len(traj)) + 1):
        traj[-i]["reward"] += float(reward)

def finalize_episode_and_store(memory):
    memory.setdefault("rbot_trajs", [])
    traj = memory.pop("rbot_traj_current", None)
    if traj:
        memory["rbot_trajs"].append(traj)
    memory.setdefault("train_stats", {})
    memory["train_stats"]["episodes"] = memory["train_stats"].get("episodes", 0) + 1

FEATURES = {
    "is_hostile": lambda c: is_hostile(c["stats"], c["target"]),
    "hp_ratio": lambda c: c["stats"]["hp"] / STARTING_HP,
    "facing_center": lambda c: 1.0 if (c["stats"]["coordinates"][0] - SIDE_LENGTH / 2) * (c["delta_x"] + c["delta_y"]) < 0 else 0.0,
    "shield_ratio": lambda c: c["stats"]["shield"] / STARTING_MAX_SHIELD,
    "max_shield_ratio": lambda c: state.max_shield / STARTING_MAX_SHIELD,
    "y_ratio": lambda c: c["y"] / SIDE_LENGTH,
    "x_ratio": lambda c: c["x"] / SIDE_LENGTH,
    "distance_ratio": lambda c: c["target"]["distance"] / SIDE_LENGTH,
    "mana_ratio": lambda c: c["stats"]["mana"] / MAX_MANA,
    "current_time_ratio": lambda c: state.current_time / MAX_TIME
}

def get_input_dict(stats=None, target=None, delta_x=None, delta_y=None, x=None, y=None):
    out = {}
    for action in ACTIONS:
        out["recommended_action_" + action] = None
  
    for orientation in CARDINAL_DIRECTIONS:
        out["recommended_orientation_" + orientation] = None

    for name in FEATURES:
        out[name] = None

    if stats is None:
        return out

    for action in ACTIONS:
        out["recommended_action_" + action] = float(state.recommended_action == action) * state.guide_relevance

    for orientation in CARDINAL_DIRECTIONS:
        out["recommended_orientation_" + orientation] = float(state.recommended_orientation == orientation) * state.guide_relevance
    
    ctx = {
        "stats": stats,
        "target": target,
        "delta_x": delta_x,
        "delta_y": delta_y,
        "x": x,
        "y": y,
    }

    for name in FEATURES:
        out[name] = float(FEATURES[name](ctx))

    return out

SPELL_TO_FUNCTION = {
    "fireball": cast_fireball,
    "shockwave": cast_shockwave,
    "wave": cast_wave,
    "wind": cast_wind,
    "lightning_bolt": cast_lightning,
    "life_drain": cast_life_drain,
    "ice_spike": cast_ice_spikes
}