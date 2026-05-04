from config import *
from utils import *
import state

import random
from copy import deepcopy
import numpy as np

def A_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = [stats["hp"]]
    orientation = stats["visible_stats"]["orientation"]
    if target["type"] == "bot" and is_hostile(stats, target):
        if target["hp_sector"] == "very high" or stats["mana"] < MANA_COSTS["lightning_bolt"]:
            if stats["hp"]+stats["shield"] <= ATTACK_DAMAGE["lightning_bolt"] and stats["mana"] >= MANA_COSTS["boulder"]:
                action = "cast_spell boulder"
            elif stats["invisibility"] <= 7 and target["orientation"] != opposite_orientation(stats["visible_stats"]["orientation"]) and stats["mana"] >= MANA_COSTS["invisibility"]:
                action = "cast_spell invisibility"
            else:
                options = ["fireball", "wave", "wind", "lightning_bolt", "boulder", "shockwave", "life_drain", "ice_spikes", "mana_blast", "cripple"]
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
                    if target["orientation"] == opposite_orientation(stats["visible_stats"]["orientation"]) and random.randint(0, 1):
                        action = "physical_attack parry"
                    else:
                        action = "physical_attack punch"
                else:
                    action = "move " + random.choice(CARDINAL_DIRECTIONS.copy()) + " 4"
        else:
            action = "cast_spell lightning_bolt"
    elif target["type"] == "elemental" and is_hostile(stats, target):
        if stats["mana"] >= MANA_COSTS["lightning_bolt"]:
            action = "cast_spell lightning_bolt"
        else:
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif target["type"] not in ["perimeter", "elemental"] and stats["mana"] >= MANA_COSTS["wind"] and target["distance"] * sum(get_deltas(stats["visible_stats"]["orientation"])) + stats["coordinates"][0 if get_deltas(stats["visible_stats"]["orientation"])[1] else 1] not in [0, SIDE_LENGTH - 1]:
        action = "cast_spell wind"
    elif target["type"] not in ["perimeter", "elemental"]:
        action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif target["distance"] == 1:
        orientation = opposite_orientation(stats["visible_stats"]["orientation"])
        action = f"move {orientation} 4"
    elif stats["hp"] < memory[-1]:
        DIRECTIONS = [d for d in CARDINAL_DIRECTIONS.copy() if d != orientation]
        action = "move " + random.choice(DIRECTIONS) + " 1"
    elif not stats["mana"]:
        action = "hybernate"
    elif stats["mana"] < MAX_MANA / 2:
        action = "meditate"
    elif random.randint(0, 1):
        orientation = random.choice(CARDINAL_DIRECTIONS.copy())
        action = "move " + orientation + " 4"
    elif random.randint(0, 1) and stats["mana"] >= MANA_COSTS["summon_elemental"] and target["distance"] != 1:
        action = f"cast_spell summon_elemental {random.choice(list(ELEMENT_TO_SPELL.keys()))}"
    elif not random.randint(0, 3) and stats["mana"] >= MANA_COSTS["infusion"] and stats["hp"] >= STARTING_HP:
        action = "cast_spell infusion" 
    elif stats["mana"] < MAX_MANA and not random.randint(0, 9) and stats["mana"] >= MANA_COSTS["invisibility"]:
        action = "cast_spell invisibility"
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    else:
        action = "cast_spell mana_blast"
    memory.append(stats["hp"])
    return action, orientation, memory

def A_bot_elemental_protocol(coordinates, stats, target, memory):
    delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
    orientation = random.choice(get_viable_cardinal_directions(coordinates))
    if not memory:
        memory = {"known_whereabouts": [], "scanning_direction": None, "scanning_orientation": None}
    for square_distance in range(target["distance"]+1):
        SQUARE_COORDINATES = deduce_coordinates(coordinates, square_distance, delta_x, delta_y)
        if -1 in SQUARE_COORDINATES or SIDE_LENGTH in SQUARE_COORDINATES:
            break
        for previous_target in deepcopy(memory["known_whereabouts"]):
            if previous_target["coordinates"] == SQUARE_COORDINATES:
                memory["known_whereabouts"].remove(previous_target)
                if not memory["known_whereabouts"]:
                    memory["scanning_direction"] = None
                    memory["scanning_orientation"] = None
    if target["type"] == "bot" and is_hostile(stats, target):
        orientation = stats["visible_stats"]["orientation"]
        memory["known_whereabouts"].append({"type": target["type"], "coordinates": deduce_coordinates(coordinates, target["distance"], delta_x, delta_y)})
        if stats["visible_stats"]["element"] == "earth" and target["distance"] > 2:
            action = f"move {orientation} 4"
        else:
            action = "cast_spell"
    elif target["type"] == "elemental" and is_hostile(stats, target) and stats["visible_stats"]["element"] in ["fire", "lightning", "state.state.water"]:
        memory["known_whereabouts"].append({"type": target["type"], "coordinates": deduce_coordinates(coordinates, target["distance"], delta_x, delta_y)})
        action = "cast_spell"
    elif memory["known_whereabouts"]:
        BOT_WHEREABOUTS = [previous_target for previous_target in memory["known_whereabouts"] if previous_target["type"] == "bot"]
        if len(BOT_WHEREABOUTS):
            HUNTING = BOT_WHEREABOUTS[0]
        else:
            HUNTING = memory["known_whereabouts"][0]
        RELATIVE_COORDINATES = [destination_coordinate - current_coordinate for destination_coordinate, current_coordinate in zip(HUNTING["coordinates"], coordinates)]
        for axis, relative_coordinate in enumerate(RELATIVE_COORDINATES):
            if relative_coordinate:
                action = "move "
                if relative_coordinate > 0:
                    if not axis:
                        MOVEMENT_DIRECTION = "south"
                    else:
                        MOVEMENT_DIRECTION = "east"
                else:
                    if not axis:
                        MOVEMENT_DIRECTION = "north"
                    else:
                        MOVEMENT_DIRECTION = "west"
                action += MOVEMENT_DIRECTION
                action += f" {abs(relative_coordinate)}"
                orientation = MOVEMENT_DIRECTION
                break
    else:
        # the following is an adapted version of H_bot's scanning code for the elemental
        if memory["scanning_direction"] is None or memory["scanning_orientation"] is None:
            SCAN_CURRENT = False

            # code for finding furthest direction
            furthest = [0, 0]
            furthest_directions_sgn = [0, 0]
            for axis in [0, 1]:
                if coordinates[axis] <= SIDE_LENGTH // 2:
                    furthest[axis] = SIDE_LENGTH - 1 - coordinates[axis]
                    furthest_directions_sgn[axis] = 1
                else:
                    furthest[axis] = coordinates[axis]
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
            CURRENT_MOVEMENT_DIRECTION = memory["scanning_direction"]
            orientation = memory["scanning_orientation"]
            MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = get_deltas(CURRENT_MOVEMENT_DIRECTION)
            if (
                (MOVEMENT_DELTA_X + MOVEMENT_DELTA_Y == -1 and coordinates[0 if MOVEMENT_DELTA_Y else 1] == state.avalanche_progress[0 if MOVEMENT_DELTA_Y else 1])
                or (MOVEMENT_DELTA_X + MOVEMENT_DELTA_Y == 1 and coordinates[0 if MOVEMENT_DELTA_Y else 1] == SIDE_LENGTH - 1 - state.avalanche_progress[0 if MOVEMENT_DELTA_Y else 1])
            ):
                SCAN_CURRENT = True
                MOVEMENT_DIRECTION = opposite_orientation(CURRENT_MOVEMENT_DIRECTION)
                if coordinates[0 if delta_y else 1] not in [state.avalanche_progress[0 if delta_y else 1], SIDE_LENGTH - 1 - state.avalanche_progress[0 if delta_y else 1]]:
                   orientation = opposite_orientation(orientation)
            else:
                SCAN_CURRENT = False
                MOVEMENT_DIRECTION = CURRENT_MOVEMENT_DIRECTION

        memory["scanning_direction"] = MOVEMENT_DIRECTION
        memory["scanning_orientation"] = orientation

        action = f"move {MOVEMENT_DIRECTION} 1" if not SCAN_CURRENT else "" # when scanning the final row, don't move
    return action, orientation, memory

def B_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = [target]
    coordinates_centered = [stats["coordinates"][dimension] in [(SIDE_LENGTH - 1) // 2, (SIDE_LENGTH - 1) // 2 + 1] for dimension in [0, 1]]
    CUSTOM_CARDINAL_DIRECTIONS = ["north", "south", "west", "east"]
    orientation = random.choice(CARDINAL_DIRECTIONS.copy())

    if is_hostile(stats, target):
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
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        orientation = stats["visible_stats"]["orientation"]
    elif target["type"] != "perimeter":
        if target["distance"] < 5 and stats["mana"] >= MANA_COSTS["wave"]:
            action = "cast_spell wave"
        elif target["distance"] > 3 and stats["mana"] >= MANA_COSTS["wind"]:
           action = "cast_spell wind"
        else:
           action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif not stats["mana"] and not any(state.avalanche_progress) and not stats["shield"]:
        action = "hybernate"
    elif not all(coordinates_centered):
        action = "move "
        for axis in [0, 1]:
            if not coordinates_centered[axis]:
                if stats["coordinates"][axis] < (SIDE_LENGTH - 1) // 2:
                    action += CUSTOM_CARDINAL_DIRECTIONS[1 + 2 * axis]
                elif stats["coordinates"][axis] > (SIDE_LENGTH - 1) // 2 + 1:
                    action += CUSTOM_CARDINAL_DIRECTIONS[0 + 2 * axis]
                else:
                    raise Exception(f"Something is wrong with B_bot_func, {stats}, {coordinates_centered}")
                break
        action += " 4"
    elif random.randint(0, 1) and len(memory) >= 5 and all(memory[-i]["type"] != "bot" for i in range(1, 6)) and stats["shield"] < state.max_shield and stats["mana"] >= MANA_COSTS["per_shield_hp"] * (state.max_shield/4):
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
  orientation = stats["visible_stats"]["orientation"]
  if is_hostile(stats, target) and stats["mana"] >= MANA_COSTS["lightning_bolt"]:
    action = "cast_spell lightning_bolt"
  elif not stats["mana"] and not stats["shield"] and state.current_time > 2 and not any(state.avalanche_progress): # to prevent it from hybernating at start and end
    action = "hybernate"
  elif stats["mana"] < MAX_MANA:
    action = "meditate"
  elif memory[-1] == stats["coordinates"] and memory[-2] == "move":
    action = "cast_spell mana_blast"
    orientation = "west" if memory[0] == "south" else "east"
  elif (stats["coordinates"][0] < SIDE_LENGTH - 1 - state.avalanche_progress[0]) if memory[0] == "south" else (stats["coordinates"][0] > state.avalanche_progress[0]):
    action = f"move {memory[0]} 4"
    orientation = "west" if memory[0] == "south" else "east"
  elif stats["coordinates"][1] < SIDE_LENGTH - 1 - state.avalanche_progress[1] if memory[0] == "south" else (stats["coordinates"][1] > state.avalanche_progress[1]):
    action = f"move {'east' if memory[0] == 'south' else 'west'} 4"
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
  deltas = list(reversed(get_deltas(stats["visible_stats"]["orientation"])))
  if is_hostile(stats, target):
    lock_orientation = True
    if stats["mana"] >= MANA_COSTS["lightning_bolt"]:
        action = "cast_spell lightning_bolt"
    elif target["distance"] == 1:
        action = "physical_attack punch"
    elif target["orientation"] != opposite_orientation(stats["visible_stats"]["orientation"]):
        action = "meditate"
    else:
        action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
  elif target["type"] != "perimeter" and target["distance"] * sum(deltas) + stats["coordinates"][0 if deltas[0] else 1] not in [state.avalanche_progress[0 if deltas[0] else 1], SIDE_LENGTH - 1 - state.avalanche_progress[0 if deltas[0] else 1]]:
    if stats["mana"] >= MANA_COSTS["wind"]:
        action = "cast_spell wind"
    elif target["type"] == "boulder" and target["distance"] > 2:
        lock_orientation = True
        action = "meditate"
    else:
        action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
  elif stats["shield"] < memory[-1]:
    action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]), not_sideways=False)
  else:
    if stats["shield"] < state.max_shield and stats["mana"] >= MANA_COSTS["per_shield_hp"] and (random.randint(0, 1 if stats["mana"] < MAX_MANA / 4 else 2) or stats["mana"] > MAX_MANA / 2):
        action = "cast_spell shield"
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    elif random.randint(0, 1):
        action = "cast_spell mana_blast"
    elif random.randint(0, 1) and target["distance"] > 2:
        action = "cast_spell fireball"
    elif random.randint(0, 1) and target["distance"] > 1:
        action = "cast_spell wave"
    elif random.randint(0, 1) and target["distance"] > 1:
        action = f"cast_spell summon_elemental {random.choice(['lightning', 'darkness'])}"
    elif target["distance"] > 1:
        action = "cast_spell boulder"
    else:
        action = "cast_spell mana_blast"
  if lock_orientation:
    orientation = stats["visible_stats"]["orientation"]
  else:
     orientation = random.choice(CARDINAL_DIRECTIONS.copy())
  memory.append(stats["shield"])
  return action, orientation, memory 

def E_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = [random.choice(CARDINAL_DIRECTIONS.copy()), [stats, target, random.randint(0, 1)]]
    orientation = random.choice(CARDINAL_DIRECTIONS.copy())
    scan_direction = memory[-1][2]
    deltas = get_deltas(stats["visible_stats"]["orientation"])
    axis = get_axis(deltas, True)
    sign = deltas[0 if axis else 1]
    DIRECTION = memory[0]
    DIRECTION_DELTAS = get_deltas(DIRECTION)
    DIRECTION_AXIS = get_axis(DIRECTION_DELTAS, True)
    DIRECTION_SIGN = DIRECTION_DELTAS[0 if DIRECTION_AXIS else 1]
    SPARE_MANA = stats["mana"] - MANA_COSTS['lightning_bolt'] * 2
    if is_hostile(stats, target):
        if stats["mana"] >= MANA_COSTS["lightning_bolt"]:
           action = "cast_spell lightning_bolt"
        elif stats["mana"] >= MANA_COSTS["wave"]:
           action = "cast_spell wave"
        elif target["distance"] == 1:
           action = "physical_attack punch"
        else:
           action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        orientation = stats["visible_stats"]["orientation"]
    elif target["type"] != "perimeter":
        if target["type"] == "boulder" and target["distance"] * sign + stats["coordinates"][axis] == state.avalanche_progress[axis] if sign == -1 else SIDE_LENGTH - 1 - state.avalanche_progress[axis]:
            if stats["mana"] < MAX_MANA:
               action = "meditate"
            elif stats["shield"] < state.max_shield:
               action = "cast_spell shield"
            else:
               action = "cast_spell mana_blast"
        elif stats["mana"] >= MANA_COSTS["wind"]:
            action = "cast_spell wind"
        else:
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif stats["mana"] < MANA_COSTS["lightning_bolt"]:
        action = "meditate"
    elif memory[-1][1]["type"] == "bot" and is_hostile(stats, memory[-1][1]) and stats["mana"] >= MANA_COSTS["wave"]:
        action = "cast_spell wave"
    elif stats["coordinates"][DIRECTION_AXIS] != (state.avalanche_progress[DIRECTION_AXIS] if DIRECTION_SIGN == -1 else SIDE_LENGTH - 1 - state.avalanche_progress[DIRECTION_AXIS]):
        action = f"move {DIRECTION} 4"
        orientation = DIRECTION
    elif memory[-1][0]["hp"] < stats["hp"] or memory[-1][0]["shield"] < stats["shield"] or (all("move" in previous_action for previous_action in [memory[-1][0]["visible_stats"]["previous_action"], stats["visible_stats"]["previous_action"]]) and len(memory) > 2 and all(stats["coordinates"] == previous_coordinates for previous_coordinates in [memory[-1][0]["coordinates"], memory[-2][0]["coordinates"]])):
        action = f"move {opposite_orientation(DIRECTION)} 4"
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
    elif random.randint(0, 1) and SPARE_MANA >= MANA_COSTS["per_shield_hp"] and stats["shield"] < state.max_shield:
        action = f"cast_spell shield {SPARE_MANA}"
    elif random.randint(0, 1) and stats["mana"] >= MANA_COSTS["fireball"]:
        action = "cast_spell fireball"
    elif random.randint(0, 1) and stats["mana"] >= MANA_COSTS["wave"]:
        action = "cast_spell wave"
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    elif stats["shield"] < state.max_shield:
        action = "cast_spell shield"
    else:
        action = "cast_spell mana_blast"
    memory.append([stats, target, scan_direction])
    return action, orientation, memory

def F_bot_get_orientation(stats, memory, default_orientation):
    if memory[-1] is not None:
        TARGET_COORDINATES = memory[-1][0]
        if stats["coordinates"] == TARGET_COORDINATES:
            if stats["visible_stats"]["orientation"] not in memory[-1][1]:
                memory[-1][1].append(stats["visible_stats"]["orientation"])
            if set(memory[-1][1]) == set(CARDINAL_DIRECTIONS):
                memory.append(None)
            else:
                remaining_orientations = set(CARDINAL_DIRECTIONS) - set(memory[-1][1])
                return random.choice(list(remaining_orientations)), memory
    return default_orientation, memory

def F_bot_func(stats, target, memory, info_messages):
    if stats["hexed"] is not None:
        orientation = opposite_orientation(stats["visible_stats"]["orientation"])
        if stats["hexed"]["time"] > 1:
            if target["type"] == "bot" and target["name"] != stats["hexed"]["source"] and stats["mana"] >= MANA_COSTS["lightning_bolt"]:
                action = "cast_spell lightning_bolt"
            else:
                action = "cast_spell soul_search"
        else:
            action = "cast_spell mana_blast"
        return action, orientation, memory
    CUSTOM_CARDINAL_DIRECTIONS = ["north", "south", "west", "east"]
    orientation = random.choice(CARDINAL_DIRECTIONS)
    TRIO_COST = MANA_COSTS["soul_search"]+MANA_COSTS["invisibility"]+MANA_COSTS["enhance"]
    if not memory:
        memory = [0, 0, deepcopy(stats), "", None] # soul search type, time until moving back, last stats, last action, target info
    delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])

    if target["type"] == "bot" and is_hostile(stats, target):
        delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
        TARGET_COORDINATES = (stats["coordinates"][0] + delta_y * target["distance"], stats["coordinates"][1] + delta_x * target["distance"])
        if memory[-1] is None or memory[-1][0] != TARGET_COORDINATES:
            memory.append([TARGET_COORDINATES, [], target["name"]])
        if target["hp_sector"] != "very high" and stats["mana"] >= MANA_COSTS["lightning_bolt"]:
            action = "cast_spell lightning_bolt"
        elif stats["invisibility"] <= 1 and stats["mana"] >= MANA_COSTS["invisibility"] and target["orientation"] != opposite_orientation(stats["visible_stats"]["orientation"]):
            action = "cast_spell invisibility"
        elif target["distance"] >= 5 and stats["mana"] >= MANA_COSTS["enhance"]:
            action = "cast_spell enhance"
        elif stats["mana"] >= MANA_COSTS["fireball"] and not random.randint(0, 3):
            action = "cast_spell fireball"
        elif stats["mana"] // 100 >= target["distance"]:
            action = "cast_spell mana_blast"
        elif stats["mana"] >= MANA_COSTS["wave"] and not random.randint(0, 3):
            action = "cast_spell wave"
        elif target["distance"] == 1:
            action = "physical_attack punch"
        elif target["distance"] > 4 and deduce_coordinates(stats["coordinates"], target["distance"], delta_x, delta_y)[delta_x] in range(4, SIDE_LENGTH - 4):
            action = f"physical_attack charge {target['distance'] // (4 if stats['visible_stats']['enhancement'] else 2)+1}"
        else:
            action = f"move {stats['visible_stats']['orientation']} 4"
        orientation = stats["visible_stats"]["orientation"]
    elif "soul_search" in [info_message[0] for info_message in info_messages]:
        SEARCH_INFO = [info_message[1] for info_message in info_messages if info_message[0] == "soul_search"][0]
        if TEAM_MODE and SEARCH_INFO["visible_stats"]["team"] == stats["visible_stats"]["team"]:
            memory[-5] = 1 - memory[-5] # toggle between 0 and 1
        else:
            TARGET_COORDINATES = SEARCH_INFO["coordinates"]
            memory[-1] = [TARGET_COORDINATES, [], SEARCH_INFO]
        if stats["mana"] >= MANA_COSTS["enhance"]:
            action = "cast_spell enhance"
        else:
            action = "meditate"
    elif target["type"] == "elemental" and is_hostile(stats, target) and stats["mana"] >= MANA_COSTS["hex"]:
        action = "cast_spell hex"
    elif target["distance"] < 3 and target["type"] not in ["ice_spike", "perimeter", "elemental", "bot"]:
        if stats["mana"] >= MANA_COSTS["wave"] and random.randint(0, 1):
            action = "cast_spell wave"
        else:
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
            memory[-4] = 2
        orientation, memory = F_bot_get_orientation(stats, memory, orientation)
    elif memory[-1] is not None:
        TARGET_COORDINATES = memory[-1][0]
        if memory[-1][2] and memory[-1][2] in [info_message[0] for info_message in info_messages]:
            memory[-1][2] = ""
            action = "meditate"
        elif memory[-1][2] and TARGET_COORDINATES == (stats["coordinates"][0]+delta_y, stats["coordinates"][1]+delta_x):
            if stats["mana"] >= min(MANA_COSTS["wave"], MANA_COSTS["shockwave"]):
                options = ["wave", "shockwave"]
                for option in options.copy():
                    if stats["mana"] < MANA_COSTS[option]:
                        options.remove(option)
                action = "cast_spell " + random.choice(options)
            else:   
                action = "physical_attack slash"
        elif tuple(stats["coordinates"]) == tuple(TARGET_COORDINATES):
            if stats["mana"] > MANA_COSTS["soul_search"] and stats["shield"] < state.max_shield and stats["mana"] > MANA_COSTS["per_shield_hp"] and not random.randint(0, 3):
                action = "cast_spell shield"
            elif stats["mana"] < MANA_COSTS["soul_search"] or (stats["mana"] < MAX_MANA and stats["shield"] >= state.max_shield):
                action = "meditate"
            else:
                action = "cast_spell "
                if stats["shield"] < state.max_shield and (random.randint(0, 1) or stats["mana"] % 100 != 0):
                    action += "shield"
                else:
                    action += "mana_blast"
        elif memory[-2].split()[0] == "move" and memory[-3]["coordinates"] == stats["coordinates"]:
            if stats["mana"] >= 100:
                action = "cast_spell mana_blast"
            elif stats["mana"] >= MANA_COSTS["per_shield_hp"] and stats["shield"] < state.max_shield:
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
            orientation = stats["visible_stats"]["orientation"]
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
                    action += " " + str(DISTANCE) # we don't need to limit to 4 because that happens automatically
                    break
            try:
                DISTANCE
            except NameError:
                input(f"z. coords: {stats['coordinates']}, target_coords: {TARGET_COORDINATES}") # debug
            if DISTANCE < 3:
                orientation = CARDINAL_DIRECTIONS[(CARDINAL_DIRECTIONS.index(action.split()[1])+1) % 4]
            else:
                orientation = DIRECTION
        orientation, memory = F_bot_get_orientation(stats, memory, orientation)
    elif (spotted_enemies := enemies_spotted(stats, state.bot_memory_maps[stats["visible_stats"]["name"]])):
        TARGET_COORDINATES = next(iter(spotted_enemies.values()))["coordinates"]
        memory.append([TARGET_COORDINATES, [], next(iter(spotted_enemies.keys()))])
        if stats["mana"] >= MANA_COSTS["enhance"]:
            action = "cast_spell enhance"
        else:
            action = "meditate"
        print("spotted:", TARGET_COORDINATES) # debug
    elif stats["mana"] == MAX_MANA:
        if stats["shield"] < state.max_shield:
            action = "cast_spell shield"
        else:
            action = "cast_spell mana_blast"
    elif stats["mana"] >= (TRIO_COST if TRIO_COST <= MAX_MANA else MANA_COSTS["soul_search"]) and random.randint(0, 1):
        action = f"cast_spell soul_search {memory[-5]}"
    elif target["distance"] == 1 and target["type"] == "bot" and not is_hostile(stats, target):
        memory[-1] = None
        orientation = opposite_orientation(stats["visible_stats"]["orientation"])
        action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    else:
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
                            LOCATION_VALUE = state.bot_memory_maps[stats["visible_stats"]["name"]][coordinates[0]+stats["coordinates"][0]][coordinates[1]+stats["coordinates"][1]][1]
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
    while len(memory) > 5:
        memory.pop(0)
    #print(memory) # debug
    return action, orientation, memory

def G_bot_func(stats, target, memory, info_messages):
    if not memory:
        y, x=stats["coordinates"]
        return "cast_spell shield 700", "north" if y<5 and y!=0 else ("south" if y>4 and y!=9 else ("west" if x<5 and x!=0 else "east")), {"time": 0, "objective": "flight", "hp": stats["hp"], "shield": stats["shield"]}
    VALUES={"init_shield": 700, "map": (SIDE_LENGTH - max(state.avalanche_progress)) // 2, "boulder": False} # edit: 5 -> (SIDE_LENGTH - max(state.avalanche_progress)) // 2. Sto originalt 5, men det tar verken hensyn til map størrelse eller skredet. 
    memory["time"]+=1
    coords=stats["coordinates"]

    if target["type"]=="bot" and is_hostile(stats, target): # edit: la til is_hostile(stats, target) slik at den ikke angriper allierte i team modus.
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
        if target["type"]=="bot" and is_hostile(stats, target): # edit: la til is_hostile(stats, target) slik at den ikke angriper allierte i team modus.
            action="cast_spell fireball" if target["distance"] <=2 else "cast_spell wave"

        elif target["distance"]==1:
            action="cast_spell wind"
        elif target["distance"]<6 and target["type"]!="wave":
            action="cast_spell wind"
        else:
            if stats["mana"]>(state.max_shield-stats["shield"])*10 and stats["shield"]<state.max_shield:
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
 
        orientation=list([["south", "north"][int(coords[0]/(SIDE_LENGTH-1))], ["east", "west"][int(coords[1]/(SIDE_LENGTH-1))]]) # edit: 9 -> (SIDE_LENGTH-1). 2 steder. Sto originalt 9 to steder, men det tok ikke hensyn til map størrelse og kunne gi IndexError
        if stats["visible_stats"]["orientation"] in orientation:
            orientation.remove(stats["visible_stats"]["orientation"])
        orientation=orientation[0]
    elif memory["objective"]=="flight":
        
        moves=list(["north", "west"][i] if stats["coordinates"][i]<VALUES["map"] else ["south", "east"][i] for i in [0, 1] if not stats["coordinates"][i] in (0, VALUES["map"]*2-1))
        #print(moves)

        
        if target["type"]=="perimeter":
            action=f"move {stats['visible_stats']['orientation']} 2"
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

def H_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = [None, stats["coordinates"], stats["hp"]+stats["shield"]]

    VIABLE_CARDINAL_DIRECTIONS = get_viable_cardinal_directions(stats["coordinates"])
    orientation = random.choice(VIABLE_CARDINAL_DIRECTIONS)
    
    keep_first_memory = True

    DELTA_X, DELTA_Y = get_deltas(stats["visible_stats"]["orientation"])
    DELTA = DELTA_X + DELTA_Y

    if target["type"] == "perimeter":
        TARGET_NEXT_TO_WALL = False
    elif target["distance"] * DELTA + stats["coordinates"][0 if DELTA_Y else 1] in [state.avalanche_progress[0 if DELTA_Y else 1], SIDE_LENGTH - 1 - state.avalanche_progress[0 if DELTA_Y else 1]]:
        TARGET_NEXT_TO_WALL = True
    else:
        TARGET_NEXT_TO_WALL = False
    
    if is_hostile(stats, target):
        orientation = stats["visible_stats"]["orientation"]
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
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif target["type"] != "perimeter" and not (TARGET_NEXT_TO_WALL and target["type"] == "boulder") and target["type"] != "bot":
        if stats["mana"] >= MANA_COSTS["wind"] and not TARGET_NEXT_TO_WALL and target["type"] != "fireball":
            action = "cast_spell wind"
            orientation = stats["visible_stats"]["orientation"]
        else:
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
            keep_first_memory = False
    elif target["type"] == "boulder" and TARGET_NEXT_TO_WALL and target["distance"] == 1 and stats["mana"] >= MANA_COSTS["shockwave"]:
        action = "cast_spell shockwave"
    elif memory[-1] - (stats["hp"]+stats["shield"]) > 0 and (memory[-1] - (stats["hp"]+stats["shield"])) % 10:
        action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]), not_sideways=False)
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    elif stats["shield"] < state.max_shield:
        action = "cast_spell shield"
    elif stats["visible_stats"]["previous_action"].split()[0] == "move" and memory[-1] == stats["coordinates"]: # if tried to move but didn't (implies thing in the way)
        if stats["mana"] >= 10:
            action = "cast_spell mana_blast"
        else:
            action = "meditate"
        orientation = stats["visible_stats"]["previous_action"].split()[1]
    else: # code for hunting state.bots
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
            MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = get_deltas(CURRENT_MOVEMENT_DIRECTION)
            if (
                (MOVEMENT_DELTA_X + MOVEMENT_DELTA_Y == -1 and stats["coordinates"][0 if MOVEMENT_DELTA_Y else 1] == state.avalanche_progress[0 if MOVEMENT_DELTA_Y else 1])
                or (MOVEMENT_DELTA_X + MOVEMENT_DELTA_Y == 1 and stats["coordinates"][0 if MOVEMENT_DELTA_Y else 1] == SIDE_LENGTH - 1 - state.avalanche_progress[0 if MOVEMENT_DELTA_Y else 1])
            ):
                SCAN_CURRENT = True
                MOVEMENT_DIRECTION = opposite_orientation(CURRENT_MOVEMENT_DIRECTION)
                if stats["coordinates"][0 if DELTA_Y else 1] not in [state.avalanche_progress[0 if DELTA_Y else 1], SIDE_LENGTH - 1 - state.avalanche_progress[0 if DELTA_Y else 1]]:
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

    return action, orientation, memory

def I_bot_func(stats, target, memory, info_messages):
    VIABLE_CARDINAL_DIRECTIONS = get_viable_cardinal_directions(stats["coordinates"])
    delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
    orientation = random.choice(VIABLE_CARDINAL_DIRECTIONS)
    if target["type"] == "bot" and is_hostile(stats, target):
        orientation = stats["visible_stats"]["orientation"]
        if target["distance"] == 1:
            if stats["mana"] >= MANA_COSTS["shockwave"]:
                action = "cast_spell shockwave"
            else:
                action = "physical_attack punch"
        else:
            if stats["mana"] >= MANA_COSTS["summon_elemental"]:
                viable_elements = list(ELEMENT_TO_SPELL.keys())
                if not target["distance"] * (delta_x+delta_y) + stats["coordinates"][0 if delta_y else 1] in [state.avalanche_progress[0], SIDE_LENGTH - 1 - state.avalanche_progress[0]]:
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
            elif stats["mana"] >= MANA_COSTS["invisibility"] and target["orientation"] != opposite_orientation(stats["visible_stats"]["orientation"]):
                action = "cast_spell invisibility"
            elif stats["mana"] >= MANA_COSTS["fireball"] and target["distance"] < 5:
                action = "cast_spell fireball"
            elif stats["mana"] >= MANA_COSTS["life_drain"]:
                action = "cast_spell life_drain"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif target["type"] == "elemental" and is_hostile(stats, target):
        orientation = stats["visible_stats"]["orientation"]
        if stats["mana"] >= MANA_COSTS["lightning_bolt"] and target["element"] != "lightning":
            action = "cast_spell lightning_bolt"
        elif stats["mana"] >= MANA_COSTS["wave"] and target["element"] != "state.state.water":
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
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif target["type"] == "perimeter" and target["distance"] == 1:
        orientation = opposite_orientation(stats["visible_stats"]["orientation"])
        action = f"move {orientation} 1"
    elif target["type"] in ["boulder", "fireball", "state.state.water", "ice_spike"] and target["distance"] == 1:
        orientation = stats["visible_stats"]["orientation"]
        if stats["mana"] >= MANA_COSTS["wave"] and target["type"] != "ice_spike":
            action = "cast_spell wave"
        else:
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif not stats["mana"]:
        action = "hybernate"
    elif stats["mana"] == MAX_MANA and stats["shield"] >= state.max_shield:
        if target["distance"] == 1:
            if not is_hostile(stats, target):
                action = f"move {random.choice(list(set(VIABLE_CARDINAL_DIRECTIONS) - set(stats['visible_stats']['orientation'])))} 1"
            else:
                action = "cast_spell lightning_bolt"
        else:
            action = f"cast_spell summon_elemental {random.choice(['lightning', 'darkness'])}"
    elif stats["mana"] // MANA_COSTS["per_shield_hp"] + stats["shield"] >= state.max_shield and stats["shield"] < state.max_shield:
        action = "cast_spell shield"
    else:
        action = "meditate"
    return action, orientation, memory

def J_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = {
            "hunting": None,
            "time_since_hex": float("inf"),
            "hexer_coordinates": None
        }
    if stats["hexed"] is not None:
        memory["time_since_hex"] = 0

        # Difference: dx for horizontal, dy for vertical
        dx = memory["hexer_coordinates"][1] - stats["coordinates"][1]
        dy = memory["hexer_coordinates"][0] - stats["coordinates"][0]
        
        if not dx * dy:
            if dx:
                FORBIDDEN_ORIENTATION = "east" if dx > 0 else "west"
            else:
                FORBIDDEN_ORIENTATION = "south" if dy > 0 else "north"
        else:
            FORBIDDEN_ORIENTATION = None

        VIABLE_CARDINAL_DIRECTIONS = list(set(CARDINAL_DIRECTIONS) - {FORBIDDEN_ORIENTATION} - {opposite_orientation(FORBIDDEN_ORIENTATION)})
        try:
            orientation = VIABLE_CARDINAL_DIRECTIONS[VIABLE_CARDINAL_DIRECTIONS.index(stats["visible_stats"]["orientation"])-1]
        except ValueError:
            orientation = random.choice(VIABLE_CARDINAL_DIRECTIONS)
        if is_hostile(stats, target):
            if stats["mana"] >= MANA_COSTS["lightning_bolt"]:
                action = "cast_spell lightning_bolt"
            elif target["distance"] == 1:
                action = "physical_attack punch"
            elif stats["mana"] >= MANA_COSTS["wind"]:
                action = "cast_spell wind"
            else:
                action = f"move {stats['visible_stats']['orientation']} 4"
                orientation = stats["visible_stats"]["orientation"]
        elif target["type"] == "bot" and target["name"] == stats["hexed"]["source"] and stats["mana"] >= MANA_COSTS["boulder"] and target["distance"] > 1:
            action = "cast_spell boulder"
        elif stats["mana"] >= MANA_COSTS["boulder"] and stats["mana"] < MANA_COSTS["fireball"] and target["distance"] > 1:
            action = "cast_spell boulder"
        elif target["type"] in ["perimeter", "boulder"] and target["distance"] == 1 and stats["mana"] >= MANA_COSTS["fireball"]:
            orientation = stats["visible_stats"]["orientation"]
            action = "cast_spell fireball"
        elif target["type"] in ["perimeter", "boulder"] and target["distance"] in range(2, 4 * (2 if stats["visible_stats"]["enhancement"] else 1)) and stats["mana"] >= MANA_COSTS["fireball"] and stats["hexed"]["time"] > 1:
            orientation = stats["visible_stats"]["orientation"]
            action = f"move {stats['visible_stats']['orientation']} 4"
        elif stats["mana"] >= MANA_COSTS["fireball"] + MANA_COSTS["boulder"] and target["distance"] > 1:
            action = "cast_spell boulder"
            orientation = stats["visible_stats"]["orientation"]
        elif target["distance"] == 1 and stats["mana"] + 20 >= MANA_COSTS["fireball"] and stats["hexed"]["time"] > 1:
            action = "meditate"
        elif stats["mana"] >= MANA_COSTS["soul_search"] and stats["hexed"]["time"] > 1:
            action = "cast_spell soul_search"
        elif target["type"] == "perimeter" and stats["mana"] >= MANA_COSTS["wind"] and stats["hexed"]["time"] > 1:
            action = "cast_spell wind"
        elif stats["hexed"]["time"] == 1:
            action = "cast_spell mana_blast"
            if FORBIDDEN_ORIENTATION:
                orientation = opposite_orientation(FORBIDDEN_ORIENTATION)
        elif target["type"] == "bot" and target["name"] == stats["hexed"]["source"] and target["distance"] == 1:
            action = f"move {opposite_orientation(stats['visible_stats']['orientation'])} 2"
        else:
            action = "physical_attack punch"
    else:
        VIABLE_CARDINAL_DIRECTIONS = get_viable_cardinal_directions(stats["coordinates"])
        CUSTOM_CARDINAL_DIRECTIONS = ["north", "south", "west", "east"]
        orientation = random.choice(VIABLE_CARDINAL_DIRECTIONS)
        memory["hexer_coordinates"] = stats["coordinates"]
        delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
        WALL_DISTANCE = min(stats["coordinates"][0]-state.avalanche_progress[0], stats["coordinates"][1]-state.avalanche_progress[1], SIDE_LENGTH - 1 - stats["coordinates"][0] - state.avalanche_progress[0], SIDE_LENGTH - 1 - stats["coordinates"][1] - state.avalanche_progress[1])
        if is_hostile(stats, target):
            orientation = stats["visible_stats"]["orientation"]
            if target["type"] == "bot" and math.ceil(target["charge_destination"] / (4 if target["enhancement"] else 2)) >= target["distance"] and target["orientation"] == opposite_orientation(stats["visible_stats"]["orientation"]) and stats["mana"] >= MANA_COSTS["boulder"]:
                action = "cast_spell boulder"
            elif stats["mana"] >= MANA_COSTS["hex"] and not (target["type"] == "bot" and target["hybernation"]) and memory["time_since_hex"] >= 3:
                action = "cast_spell hex"
            elif stats["mana"] >= MANA_COSTS["life_drain"]:
                action = "cast_spell life_drain"
            elif target["distance"] == 1:
                action = "physical_attack punch"
            elif target["type"] == "bot" and target["hybernation"] and deduce_coordinates(stats["coordinates"], target["distance"], delta_x, delta_y)[delta_y] in range(state.avalanche_progress[delta_y] + (4 if stats["visible_stats"]["enhancement"] else 2), SIDE_LENGTH - state.avalanche_progress[delta_y] - (4 if stats["visible_stats"]["enhancement"] else 2)):
                action = f"physical_attack charge {math.ceil(target['distance'] / (4 if stats['visible_stats']['enhancement'] else 2))}"
            elif target["type"] == "bot" and target["hybernation"] > 1:
                action = "meditate"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        elif not stats["mana"]:
            action = "hybernate"
        elif "soul_search" in [info_message[0] for info_message in info_messages]:
            SEARCH_INFO = [info_message[1] for info_message in info_messages if info_message[0] == "soul_search"][0]
            memory["hunting"] = SEARCH_INFO
            action = "meditate"
        elif target["type"] == "boulder" and target["distance"] * (delta_x+delta_y) + stats["coordinates"][0 if delta_x else 1] not in [state.avalanche_progress[0 if delta_x else 1], SIDE_LENGTH - 1 - state.avalanche_progress[0 if delta_x else 1]]:
            if stats["mana"] >= MANA_COSTS["wave"]:
                action = "cast_spell wave"
            elif stats["mana"] >= MANA_COSTS["wind"]:
                action = "cast_spell wind"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        elif target["type"] == "state.state.water" and target["distance"] == 1 and stats["mana"] >= MANA_COSTS["wave"]:
            action = "cast_spell wave"
            orientation = stats["visible_stats"]["orientation"]
        elif stats["mana"] >= MANA_COSTS["soul_search"]+MANA_COSTS["hex"] and memory["hunting"] is None:
            action = "cast_spell soul_search"
        elif stats["mana"] >= MANA_COSTS["infusion"] and stats["hp"] > STARTING_HP + INFUSION_HP_COST and random.randint(0, 1) and not stats["visible_stats"]["infused"]:
            action = "cast_spell infusion"
        elif stats["mana"] < MANA_COSTS["hex"] and stats["mana"] >= MANA_COSTS["invisibility"]:
            action = "cast_spell invisibility"
        elif stats["mana"] < MANA_COSTS["hex"] and stats["mana"] >= MANA_COSTS["enhance"]:
            action = "cast_spell enhance"
        elif stats["mana"] < MANA_COSTS["hex"]:
            action = "hybernate"
        elif memory["hunting"] is not None:
            if stats["coordinates"] == memory["hunting"]["coordinates"]:
                memory["hunting"] = None
                action = "meditate"
            else:
                travel_vector = [memory["hunting"]["coordinates"][0] - stats["coordinates"][0], memory["hunting"]["coordinates"][1] - stats["coordinates"][1]]
                delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
                axis = 0 if delta_y else 1
                if travel_vector[axis] == 0:
                    direction = CARDINAL_DIRECTIONS[(CARDINAL_DIRECTIONS.index(stats["visible_stats"]["orientation"])-1) % len(CARDINAL_DIRECTIONS)]
                    potential_deltas = list(get_deltas(direction))
                    if not (potential_deltas[0] * travel_vector[0] > 0 or potential_deltas[1] * travel_vector[1] > 0):
                        direction = opposite_orientation(direction)
                    DISTANCE = abs(travel_vector[0 if list(get_deltas(direction))[1] else 1])
                    action = f"move {direction} {DISTANCE}"
                else:
                    if (delta_y+delta_x) * travel_vector[axis] >= 0:
                        direction = stats["visible_stats"]["orientation"]
                    else:
                        direction = opposite_orientation(stats["visible_stats"]["orientation"])
                    DISTANCE = abs(travel_vector[axis])
                    action = f"move {direction} {DISTANCE}"
                travel_vector[axis] -= min(DISTANCE, (4 if stats["visible_stats"]["enhancement"] else 2)) * (get_deltas(direction)[0] + get_deltas(direction)[1])
                if DISTANCE <= (4 if stats["visible_stats"]["enhancement"] else 2): # TODO: find the proper orientation based on the axis not traveled on the travel vector
                    for axis in [0, 1]:
                        if travel_vector[axis] != 0:
                            if travel_vector[axis] > 0:
                                orientation = CUSTOM_CARDINAL_DIRECTIONS[1 + 2 * axis]
                            else:
                                orientation = CUSTOM_CARDINAL_DIRECTIONS[0 + 2 * axis]
                            break
                    #orientation = CARDINAL_DIRECTIONS[(CARDINAL_DIRECTIONS.index(stats["visible_stats"]["orientation"])-1) % len(CARDINAL_DIRECTIONS)] 
                else: 
                    orientation = direction
        elif WALL_DISTANCE == 1:
            action = f"move {stats['visible_stats']['orientation']} 4"
        else:
            action = "meditate"  
        memory["time_since_hex"] += 1
    return action, orientation, memory
    
def K_bot_func(stats, target, memory, info_messages):
    VIABLE_CARDINAL_DIRECTIONS = get_viable_cardinal_directions(stats["coordinates"])
    orientation = random.choice(VIABLE_CARDINAL_DIRECTIONS)
    if (stats["mana"] >= MANA_COSTS["enhance"] or stats["mana"] >= MANA_COSTS["invisibility"]) and target["distance"] != 1:
        options = []
        for spell in ["enhance", "invisibility"]:
            if stats["mana"] >= MANA_COSTS[spell]:
                options.append(spell)
        if options:
            action = f"cast_spell {random.choice(options)}"
        else:
            raise Exception("Something is wrong with K_bot_func, no options for enhance/invisibility")
    elif target["type"] == "perimeter" or is_hostile(stats, target):
        if target["distance"] == 1:
            if target["type"] == "perimeter":
                orientation = random.choice(VIABLE_CARDINAL_DIRECTIONS)
                action = f"move {random.choice(VIABLE_CARDINAL_DIRECTIONS)} 2"
            else:
                action = "physical_attack punch"
                orientation = stats["visible_stats"]["orientation"]
        else:
            distance = (math.floor if target["type"] == "perimeter" else math.ceil)(target["distance"] / ((4 if stats["visible_stats"]["enhancement"] else 2) * (2 if target["type"] == "perimeter" and state.time_until_avalanche < SIDE_LENGTH/2 else 1)))
            if distance * (4 if stats["visible_stats"]["enhancement"] else 2) >= target["distance"] and target["type"] == "perimeter":
                distance -= 1
            if distance:
                action = f"physical_attack charge {distance}"
            else:
                action = f"move {random.choice(VIABLE_CARDINAL_DIRECTIONS)} 2"
    else:
        action = f"move {random.choice(VIABLE_CARDINAL_DIRECTIONS)} 2"
    return action, orientation, memory

def L_bot_func(stats, target, memory, info_messages):
    delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
    orientation = random.choice(get_viable_cardinal_directions(stats["coordinates"]))
    ENHANCEMENT_MULTIPLIER = 2 if stats["visible_stats"]["enhancement"] else 1
    if not memory:
        memory = {"hunting": None}
    if stats["hexed"] is not None:
        if target["distance"] != 1 and stats["mana"] >= MANA_COSTS["boulder"]:
            action = "cast_spell boulder"
        else:
            action = "cast_spell soul_search"
        orientation = rotate(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif target["type"] == "bot" and is_hostile(stats, target):
        orientation = stats["visible_stats"]["orientation"]
        if stats["coordinates"][delta_x] + target["distance"] in range(SIDE_LENGTH // 3, 2 * SIDE_LENGTH // 3) and target["distance"] != 1:
            CHARGE_DESTINATION = math.ceil(target["distance"] / (4 if stats["visible_stats"]["enhancement"] else 2))
            action = f"physical_attack charge {CHARGE_DESTINATION}"
        elif stats["mana"] >= MANA_COSTS["lightning_bolt"]:
            action = "cast_spell lightning_bolt"
        elif target["distance"] <= 2 and stats["mana"] >= MANA_COSTS["fireball"]:
            action = "cast_spell fireball"
        elif target["distance"] == 1:
            action = "physical_attack punch"
        elif stats["mana"] >= MANA_COSTS["life_drain"]:
            action = "cast_spell life_drain"
        else:
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif target["type"] == "elemental" and is_hostile(stats, target):
        if stats["mana"] >= MANA_COSTS["hex"]:
            action = "cast_spell hex"
        else:
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif "soul_search" in [info_message[0] for info_message in info_messages]:
        SEARCH_INFO = [info_message[1] for info_message in info_messages if info_message[0] == "soul_search"][0]
        TARGET_COORDINATES = SEARCH_INFO["coordinates"]
        memory["hunting"] = [TARGET_COORDINATES, SEARCH_INFO]
        if stats["mana"] >= MANA_COSTS["enhance"]:
            action = "cast_spell enhance"
        else:
            action = "meditate"
    elif target["type"] not in ["perimeter", "elemental", "bot"] and target["distance"] * (delta_x+delta_y) + stats["coordinates"][delta_x] not in [0, SIDE_LENGTH - 1]:
        orientation = stats["visible_stats"]["orientation"]
        if stats["mana"] >= MANA_COSTS["wave"]:
            action = "cast_spell wave"
            orientation = opposite_orientation(stats["visible_stats"]["orientation"])
        elif stats["mana"] >= MANA_COSTS["wind"] and random.randint(0, 1):
            action = "cast_spell wind"
        else:
            action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    elif stats["mana"] <= MANA_COSTS["soul_search"]:
        action = "hybernate"
    elif stats["visible_stats"]["enhancement"] <= 10 and stats["mana"] >= MANA_COSTS["enhance"]:
        action = "cast_spell enhance"
    elif memory["hunting"] is not None:
        # if the target coordinates is in the line of sight
        can_see = False
        if any([stats["coordinates"][axis] == memory["hunting"][0][axis] for axis in range(2)]):
            if stats["visible_stats"]["orientation"] == "north" and memory["hunting"][0][0] < stats["coordinates"][0]:
                can_see = True
            elif stats["visible_stats"]["orientation"] == "south" and memory["hunting"][0][0] > stats["coordinates"][0]:
                can_see = True
            elif stats["visible_stats"]["orientation"] == "east" and memory["hunting"][0][1] > stats["coordinates"][1]:
                can_see = True
            elif stats["visible_stats"]["orientation"] == "west" and memory["hunting"][0][1] < stats["coordinates"][1]:
                can_see = True
        if can_see:
            memory["hunting"] = None
            if stats["mana"] >= MANA_COSTS["enhance"]:
                action = "cast_spell enhance"
            else:
                action = "meditate"
        else:
            # go to the closest line of sight with the target
            DIFFERENCE_Y = memory["hunting"][0][0] - stats["coordinates"][0]
            DIFFERENCE_X = memory["hunting"][0][1] - stats["coordinates"][1]
            if abs(DIFFERENCE_Y) > abs(DIFFERENCE_X):
                direction = "east" if DIFFERENCE_X > 0 else "west"
            else:
                direction = "north" if DIFFERENCE_Y < 0 else "south"

            DISTANCE = min(abs(DIFFERENCE_Y), abs(DIFFERENCE_X))
            if DISTANCE:
                action = f"move {direction} {DISTANCE}"
            else:
                action = "meditate"

            NEW_DIFFERENCE_Y = memory["hunting"][0][0] - stats["coordinates"][0]
            NEW_DIFFERENCE_X = memory["hunting"][0][1] - stats["coordinates"][1]
            if (abs(NEW_DIFFERENCE_Y) > abs(NEW_DIFFERENCE_X)) ^ (DISTANCE <= 2 * ENHANCEMENT_MULTIPLIER):
                orientation = "east" if NEW_DIFFERENCE_X > 0 else "west"
            else:
                orientation = "south" if NEW_DIFFERENCE_Y > 0 else "north"
                
    else: # in this case the mana must be greater than necessary to soul search and memory["hunting"] must be None
        action = "cast_spell soul_search"
    return action, orientation, memory

def M_bot_func(stats, target, memory, info_messages):
    delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
    ENHANCEMENT_MULTIPLIER = 2 if stats["visible_stats"]["enhancement"] else 1
    if stats["hexed"] is None: # if not hexed
        if not memory:
            memory = {"hunting": None} 
        elif memory["hunting"] is not None:
            if target["type"] == "bot" and target["name"] == memory["hunting"][1]["visible_stats"]["name"]:
                memory["hunting"] = None
            else:
                TARGET_COORDINATES = memory["hunting"][0]
                for square in range(stats["coordinates"][delta_x], (target["distance"]+1) * (delta_x+delta_y) + stats["coordinates"][delta_x], delta_x+delta_y):
                    if square == TARGET_COORDINATES[delta_x] and stats["coordinates"][delta_y] == TARGET_COORDINATES[delta_y]:
                        if memory["hunting"][1]["invisibility"] >= state.current_time - memory["hunting"][2]:
                            if stats["mana"] >= MANA_COSTS["invisibility"]:
                                action = "cast_spell invisibility"
                            else:
                                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
                            orientation = stats["visible_stats"]["orientation"]
                            return action, orientation, memory
                        memory["hunting"] = None
                        break
        if "soul_search" in [info_message[0] for info_message in info_messages]:
            SEARCH_INFO = [info_message[1] for info_message in info_messages if info_message[0] == "soul_search"][0]
            TARGET_COORDINATES = SEARCH_INFO["coordinates"]
            memory["hunting"] = [TARGET_COORDINATES, SEARCH_INFO, state.current_time]
        orientation = random.choice(get_viable_cardinal_directions(stats["coordinates"]))
        RELEVANT_COORDINATE = deduce_coordinates(stats["coordinates"], target["distance"], delta_x, delta_y)[0 if delta_y else 1]
        if target["type"] == "bot" and is_hostile(stats, target):
            orientation = stats["visible_stats"]["orientation"]
            MAXIMUM_HP = (["very low", "low", "high", "very high"].index(target["hp_sector"]) + 1) * (25 if target["type"] == "bot" else 13)
            MAXIMUM_SHIELD = 0 if target["type"] == "elemental" else ["none", "weak", "moderate", "strong"].index(target["shield_sector"]) * 33 + (1 if target["shield_sector"] == "strong" else 0) # I could use 100/3 but I don't trust the decimal imprecicion
            REQUIRED_DAMAGE = MAXIMUM_HP + MAXIMUM_SHIELD
            if stats["mana"] >= MANA_COSTS["lightning_bolt"] and REQUIRED_DAMAGE <= ATTACK_DAMAGE["lightning_bolt"]:
                action = "cast_spell lightning_bolt"
            elif target["distance"] >= 8 / ENHANCEMENT_MULTIPLIER and RELEVANT_COORDINATE in range(2 * ENHANCEMENT_MULTIPLIER + 1, SIDE_LENGTH - 1 - 2 * ENHANCEMENT_MULTIPLIER):
                action = f"physical_attack charge {math.ceil(target['distance']/(2*ENHANCEMENT_MULTIPLIER))}"
            elif target["hybernation"] and stats["mana"] >= MANA_COSTS["life_drain"] + MANA_COSTS["lightning_bolt"]:
                action = "cast_spell life_drain"
            elif RELEVANT_COORDINATE not in range(2, SIDE_LENGTH - 2) and target["distance"] <= 3 and stats["mana"] >= MANA_COSTS["wave"]:
                action = "cast_spell wave"
            elif stats["mana"] >= MANA_COSTS["lightning_bolt"]:
                action = "cast_spell lightning_bolt"
            elif RELEVANT_COORDINATE in [0, SIDE_LENGTH - 1] and stats["mana"] >= MANA_COSTS["wind"]:
                action = "cast_spell wind"
            elif stats["mana"] >= MANA_COSTS["life_drain"]:
                action = "cast_spell life_drain"
            elif target["distance"] == 1:
                action = "physical_attack punch"
            elif RELEVANT_COORDINATE in range(2 * ENHANCEMENT_MULTIPLIER + 1, SIDE_LENGTH - 1 - 2 * ENHANCEMENT_MULTIPLIER):
                action = f"physical_attack charge {math.ceil(target['distance']/(2*ENHANCEMENT_MULTIPLIER))}"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        elif target["type"] == "elemental" and is_hostile(stats, target):
            if stats["mana"] >= MANA_COSTS["hex"]:
                action = "cast_spell hex"
            elif stats["mana"] >= MANA_COSTS["lightning_bolt"]:
                action = "cast_spell lightning_bolt"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        elif target["type"] in ["boulder", "state.state.water", "fireball"] and RELEVANT_COORDINATE not in [0, SIDE_LENGTH - 1]:
            if stats["mana"] >= MANA_COSTS["wave"]:
                action = "cast_spell wave"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        elif any([coordinate in [state.avalanche_progress[axis], SIDE_LENGTH - 1 - state.avalanche_progress[axis]] for axis, coordinate in enumerate(stats["coordinates"])]):
            if stats["coordinates"][0] == max(state.avalanche_progress):
                action = "move south 1"
            elif stats["coordinates"][0] == SIDE_LENGTH - 1 - max(state.avalanche_progress):
                action = "move north 1"
            elif stats["coordinates"][1] == max(state.avalanche_progress):
                action = "move east 1"
            elif stats["coordinates"][1] == SIDE_LENGTH - 1 - max(state.avalanche_progress):
                action = "move west 1"
            else:
                raise Exception(f"state.avalanche_progress: {state.avalanche_progress}, stats['coordinates']: {stats['coordinates']}")
        elif memory["hunting"] is not None:
            TARGET_COORDINATES = memory["hunting"][0]
            RELATIVE_COORDINATES = [coordinate - stats["coordinates"][axis] for axis, coordinate in enumerate(TARGET_COORDINATES)]
            CLOSEST_COORDINATE = min([abs(coordinate) for coordinate in RELATIVE_COORDINATES])
            CLOSEST_COORDINATE_AXIS = [axis for axis, coordinate in enumerate(TARGET_COORDINATES) if abs(stats["coordinates"][axis] - coordinate) == CLOSEST_COORDINATE][0]
            if max([abs(coordinate) for coordinate in RELATIVE_COORDINATES]) < 8 and stats["mana"] < MANA_COSTS["enhance"]:
                action = "hybernate"
            else:
                if CLOSEST_COORDINATE_AXIS == 0:
                    if RELATIVE_COORDINATES[0] > 0:
                        DIRECTION = "south"
                    else:
                        DIRECTION = "north"
                    orientation = ["west", "east"][int((RELATIVE_COORDINATES[1] / abs(RELATIVE_COORDINATES[1]) + 1) / 2)]
                elif CLOSEST_COORDINATE_AXIS == 1:
                    if RELATIVE_COORDINATES[1] > 0:
                        DIRECTION = "east"
                    else:
                        DIRECTION = "west"
                    orientation = ["north", "south"][int((RELATIVE_COORDINATES[0] / abs(RELATIVE_COORDINATES[0]) + 1) / 2)]
                else:
                    raise Exception(f"TARGET_COORDINATES: {TARGET_COORDINATES}, stats['coordinates']: {stats['coordinates']}, RELATIVE_COORDINATES: {RELATIVE_COORDINATES}, CLOSEST_COORDINATE_AXIS: {CLOSEST_COORDINATE_AXIS}")
                action = f"move {DIRECTION} {CLOSEST_COORDINATE}"
                if CLOSEST_COORDINATE <= 4 and not stats["visible_stats"]["enhancement"] and stats["mana"] >= MANA_COSTS["enhance"]:
                    action = "cast_spell enhance"
                elif CLOSEST_COORDINATE <= 2 * ENHANCEMENT_MULTIPLIER and stats["mana"] >= MANA_COSTS["invisibility"] and not stats["invisibility"] and memory["hunting"][2] > state.current_time - 2:
                    action = "cast_spell invisibility"
                elif CLOSEST_COORDINATE > 2 * ENHANCEMENT_MULTIPLIER:
                    orientation = DIRECTION
        elif stats["mana"] >= MANA_COSTS["summon_elemental"] and stats["mana"] < MANA_COSTS["summon_elemental"] + MANA_COSTS["enhance"]:
            action = "cast_spell summon_elemental darkness"
        elif stats["mana"] >= MANA_COSTS["soul_search"]:
            action = "cast_spell soul_search"
        elif stats["mana"] >= MANA_COSTS["enhance"] and stats["visible_stats"]["enhancement"] <= 10:
            action = "cast_spell enhance"
        elif stats["mana"] < MANA_COSTS["enhance"] and stats["visible_stats"]["enhancement"] <= 3:
            action = "hybernate"
        else:
            action = "meditate"
    else: # if hexed
        if target["type"] == "bot" and target["name"] == stats["hexed"]["source"] and (stats["mana"] // 10) - target["distance"] * 10 <= (0 if stats["hexed"]["time"] > 1 else 30):
            action = "cast_spell mana_blast"
        elif target["distance"] != 1 and stats["mana"] >= MANA_COSTS["boulder"]:
            action = "cast_spell boulder"
        elif target["type"] == "bot" and is_hostile(stats, target):    
            if stats["mana"] >= MANA_COSTS["fireball"] and target["distance"] < 5:
                action = "cast_spell fireball"
            elif stats["mana"] >= MANA_COSTS["lightning_bolt"]:
                action = "cast_spell lightning_bolt"
            elif target["distance"] == 1:
                action = "physical_attack punch"
            elif stats["mana"] >= MANA_COSTS["wind"]:
                action = "cast_spell wind"
            else:
                action = "cast_spell mana_blast"
        else:
            action = "cast_spell soul_search"
        orientation = rotate(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    if action.split()[0] == "move" and action.split()[2] == "0":
        action = "meditate"
    return action, orientation, memory

def N_bot_func(stats, target, memory, info_messages):
    if not memory:
        memory = {
            "scanning": False,
            "scan_movement": None,
            "scan_orientation": None
        }
    delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
    if stats["hexed"] is None:
        orientation = stats["visible_stats"]["orientation"]
        if target["type"] == "perimeter" and target["distance"] == 1:
            orientation = opposite_orientation(orientation)
        TIME_REQUIRED = int(stats["mana"]*2/MANA_COSTS["ice_spikes"]) + math.ceil(SIDE_LENGTH/2)
        RELEVANT_COORDINATE = deduce_coordinates(stats["coordinates"], target["distance"], delta_x, delta_y)[delta_x]
        ENHANCEMENT_MULTIPLIER = 2 if stats["visible_stats"]["enhancement"] else 1
        CHARGE_TIME = math.ceil(target["distance"]/(2 * ENHANCEMENT_MULTIPLIER))
        direction, distance, furthest_perpendicular = closest_and_furthest_axis(stats['coordinates'])
        keep_scanning = False
        
        if not distance and target["type"] == "perimeter" and not memory["scanning"]:
            memory["scanning"] = True
            memory["scan_movement"] = furthest_perpendicular
            memory["scan_orientation"] = opposite_orientation(direction) #list(set(get_viable_cardinal_directions(stats["coordinates"])) - {furthest_perpendicular, opposite_orientation(furthest_perpendicular)})[0]
        
        if target["type"] == "bot" and is_hostile(stats, target):
            if stats["mana"] >= MANA_COSTS["ice_spikes"]:
                action = "cast_spell ice_spikes" 
                if target["distance"] != 1:
                    orientation = rotate(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
            elif stats["mana"] >= MANA_COSTS["invisibility"]:
                action = "cast_spell invisibility"
            elif stats["mana"] >= MANA_COSTS["life_drain"]:
                action = "cast_spell life_drain"
            elif target["distance"] <= 2 and stats["mana"] >= MANA_COSTS["shockwave"]:
                action = "cast_spell shockwave"
            elif target["distance"] == 1:
                action = "physical_attack punch"
            elif RELEVANT_COORDINATE in range(2 * ENHANCEMENT_MULTIPLIER + 1, SIDE_LENGTH - 1 - 2 * ENHANCEMENT_MULTIPLIER) and CHARGE_TIME * 2 * ENHANCEMENT_MULTIPLIER + stats["coordinates"][delta_x] < SIDE_LENGTH:
                action = f"physical_attack charge {CHARGE_TIME}"
            elif stats["mana"] >= MANA_COSTS["enhance"]:
                action = "enhance"
            elif stats["invisibility"]:
                action = "meditate"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        elif target["type"] == "elemental" and is_hostile(stats, target):
            if stats["mana"] >= MANA_COSTS["hex"]:
                action = "cast_spell hex"
            elif stats["mana"] >= MANA_COSTS["lightning_bolt"] and target["element"] != "lightning":
                action = "cast_spell lightning_bolt"
            elif stats["mana"] >= MANA_COSTS["ice_spikes"] and target["element"] != "ice":
                action = "cast_spell ice_spikes" 
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        elif target["type"] not in ["perimeter", "ice_spike", "elemental", "bot"] and target["distance"] == 1:
            if stats["mana"] >= MANA_COSTS["wave"]:
                action = "cast_spell wave"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        elif state.time_until_avalanche > TIME_REQUIRED and stats["mana"] == MAX_MANA and distance:
            action = f"move {direction} {distance}"
            ACTUAL_MOVEMENT = min((2 if (direction == stats["visible_stats"]["orientation"]) else 1) * ENHANCEMENT_MULTIPLIER, distance)
            distance -= ACTUAL_MOVEMENT
            if not distance:
                keep_scanning = True
                memory["scanning"] = True
                memory["scan_movement"] = furthest_perpendicular
                memory["scan_orientation"] = opposite_orientation(direction)
            elif distance > ENHANCEMENT_MULTIPLIER:
                orientation = direction
        elif state.time_until_avalanche < 3 and next_to_wall(stats["coordinates"]):
            action = f"move {opposite_orientation(direction)} {2}"
            #input(f"direction: {direction}, opposite_orientation(direction): {opposite_orientation(direction)}, state.time_until_avalanche: {state.time_until_avalanche}, memory['scan_orientation']: {memory['scan_orientation']}") # debug
        elif memory["scanning"]:
            keep_scanning = True
            if stats["mana"] < MANA_COSTS["ice_spikes"]:
                if not stats["mana"] and state.time_until_avalanche > HYBERNATION_TIME:
                    action = "hybernate"
                else:
                    action = "meditate"
            else:
                if stats["visible_stats"]["orientation"] == memory["scan_orientation"] and (state.time_until_avalanche > ICE_SPIKE_STARTING_TIME + 2 or not next_to_wall(stats["coordinates"])):
                    action = "cast_spell ice_spikes" 
                    orientation = memory["scan_movement"]
                elif stats["visible_stats"]["orientation"] == memory["scan_orientation"]:
                    action = f"move {memory['scan_orientation']} 1"
                    orientation = memory["scan_orientation"]
                else:#if stats["visible_stats"]["orientation"] == memory["scan_movement"]: # or if just a mistake / chaos such that it's a random other orientation 
                    if target["distance"] == 1 and stats["visible_stats"]["orientation"] == memory["scan_movement"]:
                        memory["scan_movement"] = opposite_orientation(memory["scan_movement"])
                    action = f"move {memory['scan_movement']} 1"
                    orientation = memory["scan_orientation"]
        elif stats["mana"] >= MANA_COSTS["summon_elemental"] and target["distance"] != 1:
            action = "cast_spell summon_elemental ice"
        elif stats["mana"] >= MANA_COSTS["invisibility"]:
            action = "cast_spell invisibility"
        elif stats["mana"] >= MANA_COSTS["enhance"]:
            action = "cast_spell enhance"
        elif state.time_until_avalanche < HYBERNATION_TIME:
            action = "meditate"
        else:
            action = "hybernate"
        
        if not keep_scanning and memory["scanning"]:
            memory["scanning"] = False
    else: # if hexed
        if is_hostile(stats, target):
            if stats["mana"] >= MANA_COSTS["lightning_bolt"]:
                action = "cast_spell lightning_bolt"
            elif target["distance"] <= 2 and stats["mana"] >= MANA_COSTS["shockwave"]:
                action = "cast_spell shockwave"
            elif target["distance"] == 1:
                action = "physical_attack punch"
            else:
                action = f"move {stats['visible_stats']['orientation']} 4"
        elif target["distance"] != 1 and stats["mana"] >= MANA_COSTS["boulder"]:
            action = "cast_spell boulder"
        else:
            action = "cast_spell soul_search"
        orientation = rotate(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
    return action, orientation, memory

def O_bot_func(stats, target, memory, info_messages):
    delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
    ENHANCEMENT_MULTIPLIER = 2 if stats["visible_stats"]["enhancement"] else 1
    DISTANCES = {
        "north": stats["coordinates"][0]-state.avalanche_progress[0], 
        "west": stats["coordinates"][1]-state.avalanche_progress[1], 
        "south": SIDE_LENGTH - 1 - stats["coordinates"][0] - state.avalanche_progress[0], 
        "east": SIDE_LENGTH - 1 - stats["coordinates"][1] - state.avalanche_progress[1]
    }
    WALL_DISTANCE = min(DISTANCES.values())
    try:
        orientation = random.choices(list(DISTANCES.keys()), weights=list(DISTANCES.values()), k=1)[0]
    except ValueError: # if all distances are zero
        orientation = "north"
    if stats["hexed"] is None: # if not hexed
        if target["type"] == "bot" and is_hostile(stats, target):
            if (not target["crippled"] or random.randint(0, 2)) and stats["mana"] >= MANA_COSTS["cripple"] and not target["hybernation"]:
                action = "cast_spell cripple"
            elif stats["mana"] >= MANA_COSTS["lightning_bolt"] and target["hp_sector"] != "very high" and target["shield_sector"] == "none" and not target["hybernation"]:
                action = "cast_spell lightning_bolt"
            elif stats["mana"] >= MANA_COSTS["life_drain"]:
                action = "cast_spell life_drain"
            elif stats["mana"] >= MANA_COSTS["wind"]:
                action = "cast_spell wind"
            elif target["distance"] == 1:
                action = "physical_attack punch"
            elif deduce_coordinates(stats["coordinates"], target["distance"], delta_x, delta_y)[delta_x] in range(4, SIDE_LENGTH - 4):
                action = f"physical_attack charge {math.ceil(target['distance'] / (2*ENHANCEMENT_MULTIPLIER))}"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
            orientation = stats["visible_stats"]["orientation"]
        elif target["type"] == "elemental" and is_hostile(stats, target):
            if (not target["crippled"] or target["infused"]) and stats["mana"] >= MANA_COSTS["hex"] and random.randint(0, 1):
                action = "cast_spell hex"
            elif stats["mana"] >= MANA_COSTS["cripple"] and random.randint(0, 1):
                action = "cast_spell cripple"
            elif stats["mana"] >= MANA_COSTS["lightning_bolt"] and target["element"] != "lightning":
                action = "cast_spell lightning_bolt"
            elif stats["mana"] >= MANA_COSTS["ice_spikes"] and target["element"] != "ice":
                action = "cast_spell ice_spikes" 
            elif stats["mana"] >= MANA_COSTS["cripple"]:
                action = "cast_spell cripple"
            else:
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
        elif not (not is_hostile(stats, target) or target["type"] == "perimeter" or deduce_coordinates(stats["coordinates"], target["distance"], delta_x, delta_y)[delta_x] in [0, SIDE_LENGTH - 1]):
            if target["distance"] == 1 and stats["mana"] >= MANA_COSTS["wave"] and target["type"] != "ice_spike":
                action = "cast_spell wave"
            elif not random.randint(0, 9):
                action = retreat(stats["visible_stats"]["orientation"], list(stats["coordinates"]))
            else:
                action = "meditate"
            if not random.randint(0, 4):
                orientation = stats["visible_stats"]["orientation"]
        elif WALL_DISTANCE <= 2 and state.time_until_avalanche <= HYBERNATION_TIME:
            action = f"move {max(DISTANCES, key=DISTANCES.get)} 4"
        elif stats["mana"] < MANA_COSTS["life_drain"] and not stats["shield"]:
            action = "hybernate"
        elif not stats["shield"] and stats["mana"] >= MANA_COSTS["summon_elemental"]:
            action = f"cast_spell summon_elemental {'darkness' if stats['hp'] <= STARTING_HP else 'lightning'}"
        elif stats["hp"] > STARTING_HP+INFUSION_HP_COST and stats["mana"] >= MANA_COSTS["infusion"] + MANA_COSTS["life_drain"] and not stats["visible_stats"]["infused"] and random.randint(0, 1):
            action = "cast_spell infusion"
        elif stats["mana"] < MAX_MANA:
            action = "meditate"
        else:
            action = f"cast_spell summon_elemental {'darkness' if stats['hp'] <= STARTING_HP else 'lightning'}"
    else: # if hexed
        if is_hostile(stats, target):
            if stats["mana"] >= MANA_COSTS["cripple"]:
                action = "cast_spell cripple"
            elif stats["mana"] >= MANA_COSTS["lightning_bolt"] and not (target["type"] == "elemental" and target["element"] == "lightning"):
                action = "cast_spell lightning_bolt"
            elif stats["mana"] >= MANA_COSTS["ice_spikes"] and not (target["type"] == "elemental" and target["element"] == "ice"):
                action = "cast_spell ice_spikes" 
            elif stats["mana"] >= MANA_COSTS["wind"] and not (target["type"] == "elemental" and target["element"] == "wind"):
                action = "cast_spell wind"
            elif target["distance"] == 1:
                action = "physical_attack punch"
            else:
                action = f"move {stats['visible_stats']['orientation']} 4"
        elif target["type"] in ["perimeter", "boulder", "bot", "elemental"] and target["distance"] in range(1, 3) and stats["mana"] >= MANA_COSTS["fireball"]:
            action = "cast_spell fireball"
        elif target["distance"] > 1 and stats["mana"] >= MANA_COSTS["boulder"]:
            action = "cast_spell boulder"
        elif stats["mana"] >= MANA_COSTS["fireball"]:
            action = f"move {min(DISTANCES, key=DISTANCES.get)} 4"
        elif stats["mana"] >= MANA_COSTS["soul_search"]:
            action = "cast_spell soul_search"
        elif stats["mana"] >= MANA_COSTS["wind"]:
            action = "cast_spell wind"
        else:
            action = "cast_spell mana_blast"
    return action, orientation, memory

def Q_bot_func(stats, target, memory, info_messages):
    delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])
    TARGET_NEXT_TO_WALL = next_to_wall(deduce_coordinates(stats["coordinates"], target["distance"], delta_x, delta_y))
    orientation = random.choice(get_viable_cardinal_directions(stats["coordinates"]))
    if target["type"] == "perimeter":
        if target["distance"] > 1 and stats["mana"] >= MANA_COSTS["summon_elemental"] and random.randint(0, 1):
            action = f"cast_spell summon_elemental {random.choice(['earth', 'wind'])}"
        elif stats["mana"] >= MANA_COSTS["boulder"] and target["distance"] > 1:
            action = "cast_spell boulder"
        elif not stats["mana"]:
            action = "hybernate"
        elif stats["mana"] == MAX_MANA:
            action = "cast_spell mana_blast"
        else:
            action = "meditate"
    elif next_to_wall(stats["coordinates"]):
        if target["distance"] == 1 and stats["mana"] >= MANA_COSTS["wind"]:
            action = "cast_spell wind"
        elif target["distance"] == 1:
            action = "meditate"
        else:
            WALL_DIRECTION = closest_and_furthest_axis(stats["coordinates"])[0] # identify the wall direction
            orientation = opposite_orientation(WALL_DIRECTION)
            action = f"move {orientation} 2" # move away from the wall
    elif stats["mana"] >= MANA_COSTS["boulder"] and target["distance"] > 1:
        action = "cast_spell boulder"
    elif target["distance"] == 1 and stats["mana"] >= MANA_COSTS["wave"] and not TARGET_NEXT_TO_WALL:
        action = "cast_spell wave"
    elif target["distance"] == 1 and stats["mana"] >= MANA_COSTS["shockwave"]:
        action = "cast_spell shockwave"
    elif target["distance"] <= 3 and stats["mana"] >= MANA_COSTS["wind"] and not TARGET_NEXT_TO_WALL:
        action = "cast_spell wind"
    elif not stats["mana"]:
        action = "hybernate"
    else:
        action = "meditate"
    return action, orientation, memory

def R_bot_func(stats, target, memory, info_messages):
    """
    Neural network based bot using PyTorch (matches trainer architecture).
    """
    import torch
    import torch.nn as nn
    
    # Define the network class (must match trainer)
    class PolicyValueNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(INPUT_SIZE, HIDDEN_SIZE)
            self.fc_action = nn.Linear(HIDDEN_SIZE, NUM_ACTIONS)
            self.fc_orient = nn.Linear(HIDDEN_SIZE, NUM_ORIENT)
            self.fc_value = nn.Linear(HIDDEN_SIZE, 1)

        def forward(self, x):
            x = torch.relu(self.fc1(x))
            return self.fc_action(x), self.fc_orient(x), self.fc_value(x).squeeze(-1)

    # Ensure memory is a dict
    if not memory:
        print(memory) # debug
        memory = {}

    # Initialize network parameters if not already in memory
    if "nn_params" not in memory:
        model = PolicyValueNet()
        # Initialize with small random weights
        for param in model.parameters():
            nn.init.uniform_(param, -0.1, 0.1)
        input("Reset brain to random weights.") # debug
        
        # Save initialized params to memory in numpy format
        memory["nn_params"] = {
            "W1": model.fc1.weight.detach().cpu().numpy().T.copy(),
            "b1": model.fc1.bias.detach().cpu().numpy().copy(),
            "W2": torch.cat([model.fc_action.weight, model.fc_orient.weight], dim=0).T.detach().cpu().numpy().copy(),
            "b2": torch.cat([model.fc_action.bias, model.fc_orient.bias], dim=0).detach().cpu().numpy().copy(),
            "value_W": model.fc_value.weight.detach().cpu().numpy().T.copy(),
            "value_b": model.fc_value.bias.detach().cpu().numpy().copy()
        }

    # Load model from memory
    model = PolicyValueNet()
    model.eval()  # Set to evaluation mode
    
    # Load parameters from memory (use the same loading function as trainer)
    from rbot_min_trainer import _load_params_into_model
    _load_params_into_model(model, memory["nn_params"])

    # Prepare input vector (normalized)
    y, x = stats["coordinates"][0], stats["coordinates"][1]
    delta_x, delta_y = get_deltas(stats["visible_stats"]["orientation"])

    input_vector = np.array(list(get_input_dict(stats=stats, target=target, delta_x=delta_x, delta_y=delta_y, x=x, y=y).values()), dtype=np.float32)

    # Forward pass with PyTorch
    with torch.no_grad():
        state_tensor = torch.from_numpy(input_vector).float()
        action_logits, orient_logits, value = model(state_tensor)
        
        action_probs = torch.softmax(action_logits, dim=0).numpy()
        orient_probs = torch.softmax(orient_logits, dim=0).numpy()
        
        action_index = np.random.choice(len(ACTIONS), p=action_probs)
        orientation_index = np.random.choice(len(CARDINAL_DIRECTIONS), p=orient_probs)
    """
    # show action logits
    print(f"Action logits: {action_logits.numpy()}")
    print(f"Orientation logits: {orient_logits.numpy()}")
    """
    # show probabilities
    print(f"Action probabilities: {action_probs}")
    print(f"Orientation probabilities: {orient_probs}")

    chosen_orientation = CARDINAL_DIRECTIONS[orientation_index]

    # Store trajectory for training
    memory.setdefault("rbot_traj_current", []).append({
        "state": input_vector,
        "action": int(action_index),
        "orient": int(orientation_index),
        "reward": 0.0
    })

    # Action mapping 
    chosen_action = ACTIONS[action_index]

    if chosen_action == "move":
        action = f"move {chosen_orientation} 4"
    elif chosen_action == "cast_spell":
        #if stats["mana"] >= MANA_COSTS["fireball"] and target["distance"] <= 5:
        #    action = "cast_spell fireball"
        #if stats["mana"] >= MANA_COSTS["wave"] and target["distance"] <= 3:
        #    action = "cast_spell wave"
        if target["distance"] <= 2 and stats["mana"] >= MANA_COSTS["shockwave"]:
            action = "cast_spell shockwave"
        elif stats["mana"] >= MANA_COSTS["lightning_bolt"]:
            action = "cast_spell lightning_bolt"
        elif stats["mana"] >= MANA_COSTS["life_drain"]:
            action = "cast_spell life_drain"
        elif stats["mana"] >= MANA_COSTS["wind"]:
            action = "cast_spell wind"
        else:
            action = "cast_spell mana_blast"
    elif chosen_action == "physical_attack":
        if target["distance"] == 1:
            if is_hostile(stats, target) and target["type"] == "bot" and target["orientation"] == opposite_orientation(chosen_orientation) and not target["hybernation"] and random.randint(0, 1):
                action = "physical_attack parry"
            else:
                action = "physical_attack punch"
        elif random.randint(0, 1):
            action = "physical_attack slash"
        else:
            action = "physical_attack parry"
    elif chosen_action in ["mana_blast", "shield"]:
        action = f"cast_spell {chosen_action} {stats['mana']}"
    else: # meditate and hybernate
        action = chosen_action

    return action, chosen_orientation, memory

def S_bot_func(stats, target, memory, info_messages):
    """
    An intentionally bad bot to serve as 'cannon-fodder', so to speak.
    """
    orientation = random.choice(get_viable_cardinal_directions(stats["coordinates"]))
    if random.random() < 0.95:
        action = ""
    elif not stats["mana"]:
        action = "hybernate"
    elif is_hostile(stats, target):
        if stats["mana"] >= MANA_COSTS["lightning_bolt"]:
            action = "cast_spell lightning_bolt"
        elif stats["mana"] >= MANA_COSTS["life_drain"]:
            action = "cast_spell life_drain"
        elif target["distance"] == 1:
            action = "physical_attack punch"
        elif stats["mana"] >= MANA_COSTS["wind"]:
            action = "cast_spell wind"
        else:
            action = "meditate"
    elif stats["mana"] < MAX_MANA:
        action = "meditate"
    elif stats["shield"] < state.max_shield and stats["mana"] >= MANA_COSTS["per_shield_hp"]:
        action = "cast_spell shield"
    elif random.randint(0, 4):
        action = f"move {orientation} 4"
    elif random.randint(0, 4):
        action = "cast_spell enhance"
    else:
        action = "cast_spell mana_blast"
    return action, orientation, memory

def Player_func(stats, target, memory, info_messages):
    for info_message in info_messages:
        display_info_message(info_message)
    print("mental map:")
    LIGHTNESS_MAP = [[(255-18) * 1.1**(-square[1]) + 18 for square in row] for row in state.bot_memory_maps[stats["visible_stats"]["name"]]]
    display_map([[square[0] for square in row] for row in state.bot_memory_maps[stats["visible_stats"]["name"]]], 1, LIGHTNESS_MAP)
    if state.player_just_took_damage:
        # make all following text red
        print("\033[31m")
        state.player_just_took_damage = False

    print(f"max shield: {state.max_shield}")
    print(f"current time: {state.current_time}")
    print(f"avalanche progress: y: {state.avalanche_progress[0]}, x: {state.avalanche_progress[1]}")
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
    
    NAMES = [CARDINAL_DIRECTIONS.copy(), SPELLS.copy(), [], [], PHYSICAL_ATTACKS.copy()]
    
    success = False
    while not success:
        success = True
        command = get_input("action ", options, NAMES)

        parts = command.split()
        for i, _ in enumerate(parts):
            parts[i] = int(parts[i])
        action = COMMANDS.copy()[parts[0] - 1]
        if action not in ["meditate", "hybernate"]:
            action += " " + NAMES[parts[0] - 1][parts[1] - 1]
            if (action == "cast_spell shield" or action.split()[0] == "move" or action == "physical_attack charge") and len(parts) >= 4:
                action += " " + str(parts[3])
            elif action == "cast_spell shield":
                action += " " + str(state.max_shield * MANA_COSTS["per_shield_hp"])
            elif action.split()[0] == "move":
                action += " 4"
            elif action == "cast_spell soul_search" and len(parts) >= 4:
                action += " " + str(parts[3])
                if len(parts) >= 6:
                    action += " " + str(parts[4]) + " " + str(parts[5])
            elif action.split()[1] == "summon_elemental":
                action += " " + list(ELEMENT_TO_SPELL.keys())[parts[2] - 1]
            elif action == "physical_attack charge":
                action += " 1"
            elif len(parts) >= 4:
                success = False # user error
    orientation = CARDINAL_DIRECTIONS.copy()[parts[1 if action in ["meditate", "hybernate"] else (3 if action.split()[1] == "summon_elemental" else 2)] - 1]
    
    # make all following text white again
    print("\033[0m")

    return action, orientation, memory

def Player_elemental_protocol(coordinates, stats, target, memory):
    LIGHTNESS_MAP = [[(255-18) * 1.1**(-square[1]) + 18 for square in row] for row in state.bot_memory_maps[stats["visible_stats"]["allegiance"]]]
    display_map([[square[0] for square in row] for row in state.bot_memory_maps[stats["visible_stats"]["allegiance"]]], 1, LIGHTNESS_MAP)
    organize("your stats", stats, 1)
    organize("target", target, 2)
    if memory:
       print(f"memory: {memory}")

    DIRECTION_INPUTS = [str(i) for i in range(1, 5)]
    options = [deepcopy(DIRECTION_INPUTS) for _ in range(2)]
    options[0] = [deepcopy(DIRECTION_INPUTS) for _ in CARDINAL_DIRECTIONS] # move
    # cast_spell is unaltered

    NAMES = [CARDINAL_DIRECTIONS.copy(), []]

    command = get_input("action ", options, NAMES, entity_type="elemental")
    parts = list(map(int, command.split()))

    action = ["move", "cast_spell"][parts[0] - 1]
    if action == "move":
        action += " " + CARDINAL_DIRECTIONS[parts[1] - 1]
        if len(parts) >= 4:
            action += " " + str(parts[3])
        else:
            action += " 4"
    
    # For move: orientation is parts[2], for cast_spell: orientation is parts[1]
    orientation = CARDINAL_DIRECTIONS[parts[2 if action == "move" else 1] - 1]

    return action, orientation, memory
