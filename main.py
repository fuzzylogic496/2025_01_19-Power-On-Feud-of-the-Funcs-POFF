# TODO: fix hunting algorithms for team mode. 
# TODO: an elemental protocol for O_bot
# TODO: fix how infused elementals cannot move and look in different directions
# TODO: replays
# TODO: cast_spell mana_trap (direction) that places a mana trap that explodes when stepped on, stealing 50 percent of mana and dealing damage based on how much mana was taken

from config import *
from bot_functions import *
from utils import *
import state
from rbot_min_trainer import train_after_episode
from rbot_pickle_store import load_memory_pickle, save_memory_pickle

from utils import _add_reward_to_last_steps

import random
import math
from copy import deepcopy
from time import perf_counter
import matplotlib.pyplot as plt
from collections import Counter

state.memories[AI_NAME] = load_memory_pickle("rbot_memory.pkl")

if not PLAYER_ONLINE and not DEBUG_MODE:
    Player_func = delete_self_func

try:
  while True: # continuously runs the game over and over
    state.max_shield = STARTING_MAX_SHIELD
    
    # set state.board to an empty 2d list of size SIDE_LENGTH
    state.board = set_map(SIDE_LENGTH)
    
    state.death_message_queue = []
    
    state.bots = {}
    state.reaction_times = {}
    state.player_funcs = {}
    state.memories = {}
    state.memories[AI_NAME] = load_memory_pickle("rbot_memory.pkl")
    #input(state.memories) # debug
    state.elemental_memories = {}
    if TEAM_MODE:
        state.team_memory_maps = [deepcopy(BLANK_MEMORY_MAP) for _ in TEAMS]
    state.bot_memory_maps = {}
    state.info_messages = {}
    state.final_reaction_times = {}

    state.letters = {
      "b": "boulder",
      "f": "fireball",
      "w": "water",
      "i": "ice_spike",
      "p": "perimeter",
      "e": "elemental"
    }
    
    # adding bots and assigning them with their functions
    if DEBUG_MODE:
        add_bot("A_player", Player_func, elemental_protocol=Player_elemental_protocol)
        add_bot("B_player", Player_func, elemental_protocol=Player_elemental_protocol)
    elif EASY_MODE:
        add_bot("A_bot", S_bot_func)
        add_bot("B_bot", S_bot_func)
        add_bot("C_bot", S_bot_func)
        add_bot("D_bot", S_bot_func)
        add_bot("E_bot", S_bot_func)
        add_bot("F_bot", S_bot_func)
        add_bot("G_bot", S_bot_func)
        add_bot("H_bot", S_bot_func)
        add_bot("I_bot", S_bot_func)
        add_bot("J_bot", S_bot_func)
        add_bot("K_bot", S_bot_func)
        add_bot("L_bot", S_bot_func)
        add_bot("M_bot", S_bot_func)
        add_bot("N_bot", S_bot_func)
        add_bot("O_bot", S_bot_func)
        add_bot("Q_bot", S_bot_func)
        add_bot("R_bot", R_bot_func)
        add_bot("Player", Player_func, elemental_protocol=Player_elemental_protocol)
    elif EMPTY_MODE:
        add_bot("R_bot", R_bot_func)
    else:
        add_bot("A_bot", A_bot_func, elemental_protocol=A_bot_elemental_protocol)
        add_bot("B_bot", B_bot_func)
        add_bot("C_bot", C_bot_func)
        add_bot("D_bot", D_bot_func)
        add_bot("E_bot", E_bot_func)
        add_bot("F_bot", F_bot_func)
        add_bot("G_bot", G_bot_func)
        add_bot("H_bot", H_bot_func)
        add_bot("I_bot", I_bot_func)
        add_bot("J_bot", J_bot_func)
        add_bot("K_bot", K_bot_func)
        add_bot("L_bot", L_bot_func)
        add_bot("M_bot", M_bot_func)
        add_bot("N_bot", N_bot_func)
        add_bot("O_bot", O_bot_func)
        add_bot("Q_bot", Q_bot_func)
        add_bot("Player", Player_func, elemental_protocol=Player_elemental_protocol)
    
    state.boulders = {}
    state.water = {}
    state.fireballs = {}
    state.elementals = {}
    state.ice_spikes = {}
    state.future_ice_spikes = []

    state.avalanche_progress = [0, 0]
    
    # setting starting locations
    numbers = list(range(SIDE_LENGTH))
    random.shuffle(numbers)
    
    numbers_even = [numbers[i] for i in range(0, SIDE_LENGTH, 2)]
    numbers_odd = [numbers[i] for i in range(1, SIDE_LENGTH, 2)]
    random.shuffle(numbers_even)
    random.shuffle(numbers_odd)
    
    for index, person in enumerate(state.bots):
        if index <= SIDE_LENGTH//2 - 1:
           state.bots[person]["coordinates"] = (numbers[index*2], numbers[index*2+1])
        elif index <= (SIDE_LENGTH//2 - 1) * 2:
           state.bots[person]["coordinates"] = (numbers_odd[index-SIDE_LENGTH//2], numbers_even[index-SIDE_LENGTH//2])
        else:
           raise Exception("work something out, too many state.bots, find out what to do")
        
    for bot_name in state.bots:
        state.board[state.bots[bot_name]["coordinates"][0]][state.bots[bot_name]["coordinates"][1]] = state.bots[bot_name]["visible_stats"]["name"][0]
        state.bots[bot_name]["visible_stats"]["orientation"] = random.choice(CARDINAL_DIRECTIONS.copy())
    
    state.current_time = 0
    state.player_just_took_damage = False

    # main game loop
    while len(state.reaction_times) > 1 and not (EASY_MODE and AI_NAME not in state.reaction_times) or (EMPTY_MODE and state.avalanche_progress[0] + 1 < SIDE_LENGTH / 2 and state.reaction_times):
      state.death_message_queue.clear()
      state.final_reaction_times = dict()
      
      if state.previous_winner:
        print(f" {state.previous_winner}")

      # display state.board map
      if MAP_DISPLAYED and ("Player" not in state.reaction_times or DEBUG_MODE):
          if not DEBUG_MODE:
            LIGHTNESS_MAP = [[(255-18) * 1.1**(-square[1]) + 18 for square in row] for row in state.bot_memory_maps[state.observing]]
            RED_MAP = (not TEAM_MODE and state.observing not in state.reaction_times) or (TEAM_MODE and not set(TEAMS[state.bots[state.observing]["visible_stats"]["team"]]) & set(state.reaction_times.keys()))
            display_map([[square[0] for square in row] for row in state.bot_memory_maps[state.observing]], 1, LIGHTNESS_MAP, RED_MAP)
          display_map(state.board)
          print(f"Max shield: {state.max_shield}")
          print(f"current time: {state.current_time}")
      
      # decide recommended action for R_bot. This is a kind of guide that can be made stricter for more controlled behavior and looser for more independent actions.
      # to adjust how much it follows the guide, edit the reward/penalty it's given for following/disobeying  
      if AI_NAME in state.reaction_times:
        if not state.current_time:
            state.recommended_action = "hybernate"
        elif random.random() < 0.5:
            #state.guide_relevance = 0.5
            coordinates_centered = [state.bots[AI_NAME]["coordinates"][dimension] in [int((SIDE_LENGTH - 1) / 2), int((SIDE_LENGTH - 1) / 2) + 1] for dimension in [0, 1]]
            if not all(coordinates_centered):
                state.recommended_action = "move"
                for axis in [0, 1]:
                    if not coordinates_centered[axis]:
                        if state.bots[AI_NAME]["coordinates"][axis] < (SIDE_LENGTH - 1) // 2:
                            state.recommended_orientation = CUSTOM_CARDINAL_DIRECTIONS[1 + 2 * axis]
                        elif state.bots[AI_NAME]["coordinates"][axis] > (SIDE_LENGTH - 1) // 2 + 1:
                            state.recommended_orientation = CUSTOM_CARDINAL_DIRECTIONS[0 + 2 * axis]
                        else:
                            raise Exception(f"Something is wrong with deciding orientation, {state.bots['R_bot']}, {coordinates_centered}")
                        break
            else:
                state.recommended_orientation = random.choice(CARDINAL_DIRECTIONS)
                target = get_target(state.bots[AI_NAME]["coordinates"], *get_deltas(state.bots[AI_NAME]["visible_stats"]["orientation"]))
                if is_hostile(state.bots[AI_NAME], target): 
                    #state.guide_relevance = 0.9
                    state.recommended_orientation = state.bots[AI_NAME]["visible_stats"]["orientation"]
                    if state.bots[AI_NAME]["mana"] >= MANA_COSTS["wind"]:
                        state.recommended_action = "cast_spell"
                    elif target["distance"] == 1:
                        state.recommended_action = "physical_attack"
                    else:
                        state.recommended_action = "move"
                elif state.bots[AI_NAME]["mana"] == MAX_MANA:
                    if state.bots[AI_NAME]["shield"] < state.max_shield and random.randint(0, 1):
                        state.recommended_action = "shield"
                    elif random.randint(0, 9) and state.bots[AI_NAME]["hp"] > STARTING_HP and state.bots[AI_NAME]["shield"]:
                        state.recommended_action = "mana_blast"
                    else:
                        state.recommended_action = "cast_spell"
                else:
                    state.recommended_action = "meditate"
        else:
            #state.guide_relevance = 0.1
            state.recommended_action = random.choice(["move", "cast_spell", "meditate", "physical_attack"])
            state.recommended_orientation = random.choice(CARDINAL_DIRECTIONS)
        
        #if state.recommended_action == "meditate": # debug
           #state.guide_relevance = 2
        
        print(state.bots[AI_NAME]["coordinates"])
        print(state.recommended_action, state.recommended_orientation, state.guide_relevance)

      # get bot inputs
      bot_actions = {}
      for bot_name in deepcopy(state.reaction_times):
        if bot_name not in state.reaction_times or state.bots[bot_name]["visible_stats"]["hybernation"]:
          continue
        delta_x, delta_y = get_deltas(state.bots[bot_name]["visible_stats"]["orientation"])
        for row in state.bot_memory_maps[bot_name]:
          for square in row:
            square[1] += 1

        state.bot_memory_maps[bot_name if not state.bots[bot_name]["hexed"] else state.bots[bot_name]["hexed"]["source"]][state.bots[bot_name]["coordinates"][0]][state.bots[bot_name]["coordinates"][1]] = [bot_name[0], 0]
        try:
            target = get_target(state.bots[bot_name]["coordinates"], delta_x, delta_y, respect_invisibility=True)
        except Exception as e:
            print(state.bots[bot_name]) # debug
            raise Exception(e)

        if "Player" not in state.reaction_times or DEBUG_MODE:
            if EMPTY_MODE: # print coordinates
               print(state.bots[bot_name]['coordinates'])
            print(f"{bot_name} hp: {state.bots[bot_name]['hp']}, mana: {state.bots[bot_name]['mana']}, shield: {state.bots[bot_name]['shield']}, time: {(state.reaction_times[bot_name]*10**6):.2f} μs{', stunned' if state.bots[bot_name]['visible_stats']['stun'] else ''}{', crippled: '+str(state.bots[bot_name]['visible_stats']['crippled'])+' -> '+str(int(100*calculate_cripple_effect(state.bots[bot_name]['visible_stats']['crippled'])))+'%' if state.bots[bot_name]['visible_stats']['crippled'] else ''}")
            
        try:
          if state.bots[bot_name]["visible_stats"]["stun"]:
              action, designated_orientation, state.reaction_times[bot_name] = "", state.bots[bot_name]["visible_stats"]["orientation"], 0
          else:
            start_time = perf_counter()
            action, designated_orientation, state.memories[bot_name if state.bots[bot_name]["hexed"] is None else state.bots[bot_name]["hexed"]["source"]] = state.player_funcs[bot_name if state.bots[bot_name]["hexed"] is None else state.bots[bot_name]["hexed"]["source"]](deepcopy(state.bots[bot_name]), deepcopy(target), deepcopy(state.memories[bot_name if state.bots[bot_name]["hexed"] is None else state.bots[bot_name]["hexed"]["source"]]), state.info_messages[bot_name])
            end_time = perf_counter()
            if ("Player" not in state.reaction_times and not DEBUG_MODE) and (bot_name == state.observing or (state.bots[bot_name]["hexed"] is not None and state.bots[bot_name]["hexed"]["source"] == state.observing)):
                print(f"action: {action}, orientation: {designated_orientation}")
            state.reaction_times[bot_name] = end_time-start_time
          state.info_messages[bot_name] = []
          if designated_orientation not in CARDINAL_DIRECTIONS:
            raise Exception("Invalid orientation")
          if action and action.split()[0] == "move":
            int(action.split()[2])
            if action.split()[1] not in CARDINAL_DIRECTIONS:
              raise Exception("Invalid direction")
          if action and action.split()[:2] == ["cast_spell", "shield"]:
            try:
                int(action.split()[2])
            except Exception:
                action = f"cast_spell shield {state.bots[bot_name]['mana']}"
          bot_actions[bot_name] = [action, designated_orientation]
        except KeyboardInterrupt: # for some reason this needs to be done seperately
            state.death_message_queue.append([bot_name, DEATH_MESSAGES["error"]('KeyboardInterrupt')])
            del state.reaction_times[bot_name]
            state.board[state.bots[bot_name]["coordinates"][0]][state.bots[bot_name]["coordinates"][1]] = "_"
            continue
        """except Exception as error_message:
            state.death_message_queue.append([bot_name, DEATH_MESSAGES['error'](error_message)])
            del state.reaction_times[bot_name]
            state.board[state.bots[bot_name]["coordinates"][0]][state.bots[bot_name]["coordinates"][1]] = "_"
            continue"""
    
      # sort the players by speed of input
      sorted_reaction_times = dict(sorted(state.reaction_times.items(), key=lambda item: item[1]))
    
      # do bot turns based on speed of input
      for bot_name in sorted_reaction_times:
        if bot_name not in state.reaction_times:
           continue
        if state.bots[bot_name]["invisibility"]:
           state.bots[bot_name]["invisibility"] -= 1
        if state.bots[bot_name]["visible_stats"]["hybernation"]:
            state.bots[bot_name]["visible_stats"]["hybernation"] -= 1
            if not state.bots[bot_name]["visible_stats"]["hybernation"]:
                state.bots[bot_name]["shield"] = state.max_shield
                state.bots[bot_name]["mana"] = MAX_MANA
                if bot_name == AI_NAME:
                    _add_reward_to_last_steps(state.memories[AI_NAME], +0.8 * state.max_shield, last_n=1)
            continue
        if state.bots[bot_name]["visible_stats"]["is_parrying"]:
            state.bots[bot_name]["visible_stats"]["is_parrying"] = False

        action, designated_orientation = bot_actions[bot_name]
        delta_x, delta_y = get_deltas(state.bots[bot_name]["visible_stats"]["orientation"])
        target = get_target(state.bots[bot_name]["coordinates"], delta_x, delta_y, False)
        state.bots[bot_name]["visible_stats"]["previous_action"] = action

        # decreases meditation efficiency when meditation is paused
        if action != "meditate" or state.bots[bot_name]["visible_stats"]["stun"] or state.bots[bot_name]["visible_stats"]["hybernation"]:
          state.bots[bot_name]["visible_stats"]["is_meditating"] = False

        # different types of damage gets multiplied based on if the bot is infused, enhanced or crippled
        INFUSION_MULTIPLIER = (2 if state.bots[bot_name]["visible_stats"]["infused"] else 1)
        ENHANCEMENT_MULTIPLIER = (2 if state.bots[bot_name]["visible_stats"]["enhancement"] else 1)
        CRIPPLE_MULTIPLIER = calculate_cripple_effect(state.bots[bot_name]["visible_stats"]["crippled"])
        
        # before bot actions
        for y in range(SIDE_LENGTH): # debug
            for x in range(SIDE_LENGTH):
                key = f"{y} {x}"
                if state.board[y][x] == "e" and key not in state.elementals:
                    input(f"WARNING: Board has 'e' at {key} but state.elementals dict is missing it!")
                if state.board[y][x] != "e" and key in state.elementals:
                    input(f"WARNING: Elementals dict has {key} but state.board is '{state.board[y][x]}'!")
                if state.board[y][x] == "e" and not any([key in state.elemental_memories[bot_name] for bot_name in state.elemental_memories]):
                    input(f"WARNING: Elemental memories missing {key}!")

        PREVIOUS_MANA = state.bots[bot_name]["mana"]

        # the bot's turn to do their action
        if state.bots[bot_name]["visible_stats"]["stun"]:
          state.bots[bot_name]["visible_stats"]["stun"] -= 1
        elif state.bots[bot_name]["visible_stats"]["charge_destination"]:
            designated_orientation = state.bots[bot_name]["visible_stats"]["orientation"]
            charge(bot_name, delta_x, delta_y)
        elif not action:
           pass
        elif action.split()[0] == "move": # example: action = "move north 2"
          MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = get_deltas(action.split()[1])
          move(bot_name, min(int(action.split()[2]), ENHANCEMENT_MULTIPLIER * (2 if state.bots[bot_name]["visible_stats"]["orientation"] == action.split()[1] else 1)), MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y)
        elif action.split()[0] == "cast_spell":
          if action.split()[1] == "fireball":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["fireball"]:
                state.bots[bot_name]["mana"] -= MANA_COSTS["fireball"]
                cast_fireball(state.bots[bot_name]["coordinates"], delta_x, delta_y, source_name=bot_name, infused=state.bots[bot_name]["visible_stats"]["infused"])
          elif action.split()[1] == "boulder":
            try:
                if state.bots[bot_name]["coordinates"][0] + delta_y < 0 or state.bots[bot_name]["coordinates"][1] + delta_x < 0:
                    raise IndexError
                if state.bots[bot_name]["mana"] >= MANA_COSTS["boulder"] and state.board[state.bots[bot_name]["coordinates"][0] + delta_y][state.bots[bot_name]["coordinates"][1] + delta_x] == "_":
                    state.bots[bot_name]["mana"] -= MANA_COSTS["boulder"]
                    KEY = f"{state.bots[bot_name]['coordinates'][0] + delta_y} {state.bots[bot_name]['coordinates'][1] + delta_x}"
                    state.boulders[KEY] = BOULDER.copy()
                    state.boulders[KEY]["visible_stats"]["infused"] = state.bots[bot_name]["visible_stats"]["infused"]
                    state.boulders[KEY]["visible_stats"]["crippled"] = state.bots[bot_name]["visible_stats"]["crippled"]
                    state.boulders[KEY]["source_name"] = bot_name if not state.bots[bot_name]["hexed"] else state.bots[bot_name]["hexed"]["source"]
                    state.board[state.bots[bot_name]["coordinates"][0] + delta_y][state.bots[bot_name]["coordinates"][1] + delta_x] = "b"
            except IndexError:
                pass
          elif action.split()[1] == "wave":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["wave"]:
              state.bots[bot_name]["mana"] -= MANA_COSTS["wave"]
              cast_wave(state.bots[bot_name]["coordinates"], delta_x, delta_y, source_name=bot_name, infused=state.bots[bot_name]["visible_stats"]["infused"], crippled=state.bots[bot_name]["visible_stats"]["crippled"])
          elif action.split()[1] == "wind":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["wind"]:
              state.bots[bot_name]["mana"] -= MANA_COSTS["wind"]
              cast_wind(state.bots[bot_name]["coordinates"], delta_x, delta_y, target, source_name=bot_name, infused=state.bots[bot_name]["visible_stats"]["infused"], crippled=state.bots[bot_name]["visible_stats"]["crippled"])
          elif action.split()[1] == "lightning_bolt":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["lightning_bolt"]:
              state.bots[bot_name]["mana"] -= MANA_COSTS["lightning_bolt"]
              cast_lightning(state.bots[bot_name]["coordinates"], delta_x, delta_y, target, source_name=bot_name, infused=state.bots[bot_name]["visible_stats"]["infused"], crippled=state.bots[bot_name]["visible_stats"]["crippled"])
          elif action.split()[1] == "shockwave":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["shockwave"]:
                state.bots[bot_name]["mana"] -= MANA_COSTS["shockwave"]
                cast_shockwave(state.bots[bot_name]["coordinates"], delta_x, delta_y, source_name=bot_name, infused=state.bots[bot_name]["visible_stats"]["infused"], crippled=state.bots[bot_name]["visible_stats"]["crippled"])
          elif action.split()[1] == "life_drain":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["life_drain"]:
              state.bots[bot_name]["mana"] -= MANA_COSTS["life_drain"]
              cast_life_drain(state.bots[bot_name]["coordinates"], delta_x, delta_y, target, bot_name, source_name=bot_name, infused=state.bots[bot_name]["visible_stats"]["infused"], crippled=state.bots[bot_name]["visible_stats"]["crippled"])
          elif action.split()[1] == "ice_spikes":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["ice_spikes"]:
              state.bots[bot_name]["mana"] -= MANA_COSTS["ice_spikes"]
              cast_ice_spikes(state.bots[bot_name]["coordinates"], delta_x, delta_y, source_name=bot_name, infused=state.bots[bot_name]["visible_stats"]["infused"], crippled=state.bots[bot_name]["visible_stats"]["crippled"])
          elif action.split()[1] == "mana_blast":
            #if bot_name == AI_NAME and not state.bots[bot_name]["mana"]:
            #    _add_reward_to_last_steps(state.memories[AI_NAME], -5.0, last_n=1)
            state.bots[bot_name]["mana"] = 0
            if not EASY_MODE or AI_NAME not in state.reaction_times:
                for remaining_player in state.reaction_times.copy():
                    if remaining_player == bot_name:
                        continue
                    FURTHEST_AXIS = max(abs(state.bots[remaining_player]["coordinates"][0]-state.bots[bot_name]["coordinates"][0]), abs(state.bots[remaining_player]["coordinates"][1]-state.bots[bot_name]["coordinates"][1]))
                    damage(remaining_player, CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * max(int((PREVIOUS_MANA/100 - FURTHEST_AXIS + 1) * 10), 0), DEATH_MESSAGES["mana_blast"], source_name=bot_name)
                    for key in deepcopy(state.elementals):
                        COORDINATES = list(map(int, key.split()))
                        FURTHEST_AXIS = max(abs(COORDINATES[0]-state.bots[bot_name]["coordinates"][0]), abs(COORDINATES[1]-state.bots[bot_name]["coordinates"][1]))
                        damage(key, (MANA_BLAST_AGAINST_ELEMENTAL_MULTIPLIER if not state.elementals[key]["visible_stats"]["infused"] else 1) * CRIPPLE_MULTIPLIER * INFUSION_MULTIPLIER * max(int((PREVIOUS_MANA/100 - FURTHEST_AXIS + 1) * 10), 0), DEATH_MESSAGES["mana_blast"], source_name=bot_name)
          elif action.split()[1] == "shield":
            original_max_shield = state.max_shield
            if state.bots[bot_name]["visible_stats"]["infused"]:
                state.max_shield *= 2
            if state.bots[bot_name]["shield"] < state.max_shield:
                if bot_name == AI_NAME:
                    if state.bots[bot_name]["mana"] < MANA_COSTS["per_shield_hp"]:
                        _add_reward_to_last_steps(state.memories[AI_NAME], -5.0, last_n=1)
                    if state.bots[bot_name]["shield"] >= state.max_shield:
                        _add_reward_to_last_steps(state.memories[AI_NAME], -5.0, last_n=1)
                MAX_AFFORDABLE = min(int(action.split()[2]), (state.max_shield - state.bots[bot_name]["shield"])*MANA_COSTS["per_shield_hp"], state.bots[bot_name]["mana"])
                state.bots[bot_name]["mana"] -= MAX_AFFORDABLE
                state.bots[bot_name]["shield"] += MAX_AFFORDABLE // MANA_COSTS["per_shield_hp"] + (1 if MAX_AFFORDABLE % MANA_COSTS["per_shield_hp"] and random.randint(0, MAX_AFFORDABLE % MANA_COSTS["per_shield_hp"]) else 0)
                if state.max_shield - state.bots[bot_name]["shield"] == 1:
                    state.bots[bot_name]["shield"] = state.max_shield
                state.bots[bot_name]["visible_stats"]["shield_sector"] = ["none", "weak", "moderate", "strong"][math.ceil((state.bots[bot_name]["shield"]*3) / (MAX_MANA // MANA_COSTS["per_shield_hp"]))]
                if bot_name == AI_NAME:
                    if state.bots[bot_name]["shield"] < state.max_shield and state.recommended_action != "shield":
                        _add_reward_to_last_steps(state.memories[AI_NAME], -5.0, last_n=1)
            state.max_shield = original_max_shield
          elif action.split()[1] == "infusion":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["infusion"]:
                state.bots[bot_name]["mana"] -= MANA_COSTS["infusion"]
                INFUSION_DAMAGE_TARGET = bot_name if state.bots[bot_name]["hexed"] is None else state.bots[bot_name]["hexed"]["source"]
                damage(INFUSION_DAMAGE_TARGET, INFUSION_HP_COST / INFUSION_MULTIPLIER / CRIPPLE_MULTIPLIER, DEATH_MESSAGES["infusion"], True) # dunno why anyone would use infusion on infusion, but if they do, it's half damage
                state.bots[bot_name]["visible_stats"]["infused"] = True
          elif action.split()[1] == "enhance":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["enhance"]:
                state.bots[bot_name]["mana"] -= MANA_COSTS["enhance"]
                state.bots[bot_name]["visible_stats"]["enhancement"] += ENHANCEMENT_TIME * INFUSION_MULTIPLIER
          elif action.split()[1] == "soul_search":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["soul_search"]:
                state.bots[bot_name]["mana"] -= MANA_COSTS["soul_search"]
                INVERSE = not (len(action.split()) == 2 or not action.split()[2])
                CENTER_POINT = tuple(state.bots[bot_name]["coordinates"]) if len(action.split()) < 5 else (int(action.split()[3]), int(action.split()[4]))
                player_distances = {}
                for remaining_player in state.reaction_times.copy():
                    if remaining_player == bot_name or (TEAM_MODE and state.bots[remaining_player]["visible_stats"]["team"] == state.bots[bot_name]["visible_stats"]["team"]):
                        continue
                    player_distances[remaining_player] = (abs(CENTER_POINT[0] - state.bots[remaining_player]["coordinates"][0])**2 + abs(CENTER_POINT[1] - state.bots[remaining_player]["coordinates"][1])**2)**(1/2)
                if player_distances:
                    player_distances = dict(sorted(player_distances.items(), key=lambda item: item[1], reverse=INVERSE))
                    if not state.bots[bot_name]["visible_stats"]["infused"]:
                        SEARCHED_TARGET = list(player_distances.keys())[0]
                        player_distances = {SEARCHED_TARGET: player_distances[SEARCHED_TARGET]}
                    for remaining_player in player_distances:
                        if remaining_player == bot_name:
                            continue
                        state.info_messages[bot_name].append(["soul_search", state.bots[remaining_player]])
                        state.bot_memory_maps[bot_name][state.bots[remaining_player]["coordinates"][0]][state.bots[remaining_player]["coordinates"][1]] = [remaining_player[0], 0]
          elif action.split()[1] == "invisibility":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["invisibility"]:
                state.bots[bot_name]["mana"] -= MANA_COSTS["invisibility"]
                state.bots[bot_name]["invisibility"] += INVISIBILITY_TIME # yes, +=. It stacks.
          elif action.split()[1] == "summon_elemental":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["summon_elemental"] and action.split()[2] in ["fire", "water", "earth", "wind", "ice", "lightning", "darkness"]:
                try:
                    if state.bots[bot_name]["coordinates"][0] + delta_y < 0 or state.bots[bot_name]["coordinates"][1] + delta_x < 0:
                        raise IndexError
                    if state.board[state.bots[bot_name]["coordinates"][0] + delta_y][state.bots[bot_name]["coordinates"][1] + delta_x] == "_":
                        state.bots[bot_name]["mana"] -= MANA_COSTS["summon_elemental"]
                        state.board[state.bots[bot_name]["coordinates"][0] + delta_y][state.bots[bot_name]["coordinates"][1] + delta_x] = "e"
                        KEY = f"{state.bots[bot_name]['coordinates'][0]+delta_y} {state.bots[bot_name]['coordinates'][1]+delta_x}"
                        state.elementals[KEY] = deepcopy(ELEMENTAL)
                        state.elementals[KEY]["visible_stats"]["element"] = action.split()[2]
                        state.elementals[KEY]["visible_stats"]["allegiance"] = bot_name
                        state.elementals[KEY]["visible_stats"]["orientation"] = state.bots[bot_name]["visible_stats"]["orientation"]
                        state.elementals[KEY]["visible_stats"]["remaining_spell_count"] = ELEMENTAL_STARTING_SPELL_COUNT * INFUSION_MULTIPLIER
                        state.elementals[KEY]["visible_stats"]["infused"] = state.bots[bot_name]["visible_stats"]["infused"]
                        state.elementals[KEY]["visible_stats"]["crippled"] = state.bots[bot_name]["visible_stats"]["crippled"]
                        state.elementals[KEY]["hp"] *= INFUSION_MULTIPLIER
                        state.elemental_memories[bot_name][KEY] = None
                except IndexError:
                   pass
          elif action.split()[1] == "hex":
            if state.bots[bot_name]["mana"] >= MANA_COSTS["hex"]:
                state.bots[bot_name]["mana"] -= MANA_COSTS["hex"]
                if target["type"] == "bot":
                    state.bots[target["name"]]["hexed"] = {"source": bot_name, "time": HEX_TIME}
                    if state.bots[bot_name]["visible_stats"]["infused"]:
                        state.bots[target["name"]]["hexed"]["time"] *= 2
                    else:
                        state.bots[bot_name]["visible_stats"]["stun"] = HEX_TIME
                elif target["type"] == "elemental":
                    KEY = f"{state.bots[bot_name]['coordinates'][0] + delta_y * target['distance']} {state.bots[bot_name]['coordinates'][1] + delta_x * target['distance']}"
                    ORIGINAL_ALLEGIANCE = target["allegiance"]
                    state.elementals[KEY]["visible_stats"]["allegiance"] = bot_name
                    for key in state.elemental_memories[ORIGINAL_ALLEGIANCE]:
                        if key == KEY:
                            del state.elemental_memories[ORIGINAL_ALLEGIANCE][key]
                            break
                    state.elemental_memories[bot_name][KEY] = None
                    if state.bots[bot_name]["visible_stats"]["infused"]:
                        for elemental in state.elementals:
                            if state.elementals[elemental]["visible_stats"]["allegiance"] == ORIGINAL_ALLEGIANCE and state.elementals[elemental]["visible_stats"]["element"] == target["element"]:
                                state.elementals[elemental]["visible_stats"]["allegiance"] = bot_name
                        state.elementals[KEY]["visible_stats"]["infused"] = True
                        state.elementals[KEY]["visible_stats"]["remaining_spell_count"] *= 2
          elif action.split()[1] == "cripple":
              if state.bots[bot_name]["mana"] >= MANA_COSTS["cripple"]:
                  state.bots[bot_name]["mana"] -= MANA_COSTS["cripple"]
                  if target["type"] == "bot":
                      state.bots[target["name"]]["visible_stats"]["crippled"] += CRIPPLE_TIME * INFUSION_MULTIPLIER
                  elif target["type"] == "elemental":
                      KEY = f"{state.bots[bot_name]['coordinates'][0] + delta_y * target['distance']} {state.bots[bot_name]['coordinates'][1] + delta_x * target['distance']}"
                      state.elementals[KEY]["visible_stats"]["crippled"] += CRIPPLE_TIME * INFUSION_MULTIPLIER
                      if state.bots[bot_name]["visible_stats"]["infused"] and state.elementals[KEY]["visible_stats"]["remaining_spell_count"] > 1:
                          state.elementals[KEY]["visible_stats"]["remaining_spell_count"] // 2
          else:
            print(f"Error: Unknown spell. Player: {bot_name}, action: {action}")
        elif action == "meditate": # because if action is meditate, the entire action is meditate
            if bot_name == AI_NAME and state.bots[bot_name]["mana"] == MAX_MANA:
                _add_reward_to_last_steps(state.memories[AI_NAME], -0.7, last_n=1)
            if state.bots[bot_name]["visible_stats"]["is_meditating"]:
                state.bots[bot_name]["mana"] += 50
            else:
                state.bots[bot_name]["mana"] += 20
                state.bots[bot_name]["visible_stats"]["is_meditating"] = True
            state.bots[bot_name]["mana"] = min(state.bots[bot_name]["mana"], MAX_MANA)
        elif action == "hybernate":
            if state.bots[bot_name]["hexed"] is None or not state.bots[state.bots[bot_name]["hexed"]["source"]]["visible_stats"]["stun"]:
                state.bots[bot_name]["visible_stats"]["hybernation"] = HYBERNATION_TIME
                if bot_name == AI_NAME:
                    _add_reward_to_last_steps(state.memories[AI_NAME], -3 * state.bots[bot_name]["shield"], last_n=1)
                    _add_reward_to_last_steps(state.memories[AI_NAME], -0.5 * state.bots[bot_name]["mana"], last_n=1)
                state.bots[bot_name]["shield"] = 0
        elif action.split()[0] == "physical_attack":
          if action.split()[1] == "punch":
            if target["distance"] == 1:
                if target["type"] == "bot":
                    if target["is_parrying"]:
                        damage(bot_name, ATTACK_DAMAGE["punch"]*ENHANCEMENT_MULTIPLIER*CRIPPLE_MULTIPLIER, DEATH_MESSAGES["parry"]("punch", target["name"]), source_name=target["name"])
                        state.bots[target["name"]]["visible_stats"]["is_parrying"] = False
                    else:
                        damage(target["name"], ATTACK_DAMAGE["punch"]*ENHANCEMENT_MULTIPLIER*CRIPPLE_MULTIPLIER, DEATH_MESSAGES["punch"], source_name=bot_name)
                elif target["type"] == "elemental":
                    KEY = f"{state.bots[bot_name]['coordinates'][0] + delta_y} {state.bots[bot_name]['coordinates'][1] + delta_x}"
                    damage(KEY, ATTACK_DAMAGE["punch"]*ENHANCEMENT_MULTIPLIER*CRIPPLE_MULTIPLIER, DEATH_MESSAGES["punch"])
          elif action.split()[1] == "slash":
            for x in range(-1, 2) if delta_y else [delta_x]:
                for y in [delta_y] if delta_y else range(-1, 2):
                    if state.bots[bot_name]["coordinates"][0] + y < 0 or state.bots[bot_name]["coordinates"][1] + x < 0:
                        continue
                    if state.bots[bot_name]["coordinates"][0] + y >= SIDE_LENGTH or state.bots[bot_name]["coordinates"][1] + x >= SIDE_LENGTH:
                        continue
                    if state.board[state.bots[bot_name]["coordinates"][0] + y][state.bots[bot_name]["coordinates"][1] + x].isupper(): # this returns false also when it's "_"
                        TARGET_NAME = state.letters[state.board[state.bots[bot_name]["coordinates"][0] + y][state.bots[bot_name]["coordinates"][1] + x]]
                        if state.bots[TARGET_NAME]["visible_stats"]["is_parrying"]:
                            damage(bot_name, int(ATTACK_DAMAGE["slash"]*ENHANCEMENT_MULTIPLIER*CRIPPLE_MULTIPLIER), DEATH_MESSAGES["parry"]("slash", TARGET_NAME), source_name=TARGET_NAME)
                            state.bots[TARGET_NAME]["visible_stats"]["is_parrying"] = False
                        else:
                           damage(TARGET_NAME, int(ATTACK_DAMAGE["slash"]*ENHANCEMENT_MULTIPLIER*CRIPPLE_MULTIPLIER), DEATH_MESSAGES["slash"], source_name=bot_name)
                    KEY = f"{state.bots[bot_name]['coordinates'][0] + y} {state.bots[bot_name]['coordinates'][1] + x}"
                    if KEY in state.elementals:
                        damage(KEY, int(ATTACK_DAMAGE["slash"]*ENHANCEMENT_MULTIPLIER*CRIPPLE_MULTIPLIER), DEATH_MESSAGES["slash"])
          elif action.split()[1] == "charge":
              if state.bots[bot_name]["hexed"] is None:
                MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = get_deltas(state.bots[bot_name]["visible_stats"]["orientation"])
                designated_orientation = state.bots[bot_name]["visible_stats"]["orientation"]
                state.bots[bot_name]["visible_stats"]["charge_destination"] = int(action.split()[2])
                charge(bot_name, MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y)
          elif action.split()[1] == "parry":
            state.bots[bot_name]["visible_stats"]["is_parrying"] = True
          else:
            print(f"Error: Unknown physical attack. Player: {bot_name}, action: {action}")
        else:
          print(f"ERROR: unknown action. Player: {bot_name}, action: {action}")
        
        #if bot_name == AI_NAME and PREVIOUS_MANA != state.bots[bot_name]["mana"]:
        #   _add_reward_to_last_steps(state.memories[AI_NAME], -0.001 * (PREVIOUS_MANA - state.bots[bot_name]["mana"]), last_n=1)

        if bot_name == AI_NAME and PREVIOUS_MANA > state.bots[bot_name]["mana"] and state.recommended_action == "cast_spell" and bot_actions[bot_name][0] and bot_actions[bot_name][0].split()[0] == "cast_spell":
            _add_reward_to_last_steps(state.memories[AI_NAME], +20.0, last_n=1)

        if action and action.split()[0] == "cast_spell" and action.split()[1] != "infusion":
            state.bots[bot_name]["visible_stats"]["infused"] = False

        if bot_name not in state.reaction_times:
            continue
        
        # countdown stun
        if not state.bots[bot_name]["visible_stats"]["stun"]:
           state.bots[bot_name]["visible_stats"]["orientation"] = designated_orientation
        
        # countdown slowness
        if state.bots[bot_name]["visible_stats"]["slowness"]:
            state.bots[bot_name]["visible_stats"]["slowness"] -= 1

        # countdown enhancement
        if state.bots[bot_name]["visible_stats"]["enhancement"]:
            state.bots[bot_name]["visible_stats"]["enhancement"] -= 1

        # countdown hex
        if state.bots[bot_name]["hexed"] is not None:
            state.bots[bot_name]["hexed"]["time"] -= 1
            if not state.bots[bot_name]["hexed"]["time"]:
                state.bots[bot_name]["hexed"] = None
                state.bots[bot_name]["velocity_y"] = 0
                state.bots[bot_name]["velocity_x"] = 0

        # countdown cripple
        if state.bots[bot_name]["visible_stats"]["crippled"]:
            state.bots[bot_name]["visible_stats"]["crippled"] -= 1

        state.board[state.bots[bot_name]["coordinates"][0]][state.bots[bot_name]["coordinates"][1]] = state.bots[bot_name]["visible_stats"]["name"][0]

      # do ice spike emergence
      for index, potential_ice_spike in enumerate(state.future_ice_spikes):
          if not potential_ice_spike["time_until_emergence"]:
            KEY = " ".join(list(map(str, potential_ice_spike["coordinates"])))
            SQUARE = state.board[int(KEY.split()[0])][int(KEY.split()[1])]
            if SQUARE in ["_", "f", "w"]:
              if SQUARE == "f" and KEY in state.fireballs:
                fireball_explode(int(KEY.split()[0]), int(KEY.split()[1]), state.fireballs[KEY]["source_name"], state.fireballs[KEY]["infused"], state.fireballs[KEY]["visible_stats"]["crippled"])
                del state.fireballs[KEY]
              elif SQUARE == "w" and KEY in state.water:
                del state.water[KEY]
              state.ice_spikes[KEY] = deepcopy(ICE_SPIKE)
              state.ice_spikes[KEY]["visible_stats"]["infused"] = potential_ice_spike["infused"]
              state.ice_spikes[KEY]["time_remaining"] = ICE_SPIKE_STARTING_TIME * (2 if potential_ice_spike["infused"] else 1)
              state.board[int(KEY.split()[0])][int(KEY.split()[1])] = "i"
            elif KEY in state.elementals or state.board[int(KEY.split()[0])][int(KEY.split()[1])].isupper():
              if KEY in state.elementals:
                TARGET_NAME = KEY
                state.elementals[KEY]["visible_stats"]["slowness"] = ICE_SLOWNESS_TIME * (2 if potential_ice_spike["infused"] else 1)
              else:
                TARGET_NAME = state.letters[state.board[int(KEY.split()[0])][int(KEY.split()[1])]]
                state.bots[TARGET_NAME]["visible_stats"]["slowness"] = ICE_SLOWNESS_TIME * (2 if potential_ice_spike["infused"] else 1)
              damage(TARGET_NAME, ATTACK_DAMAGE["ice_spike"]*(2 if potential_ice_spike["infused"] else 1), DEATH_MESSAGES["ice_spike"], damage_element="ice", source_name=potential_ice_spike["source_name"])
            try:
                state.future_ice_spikes.remove(potential_ice_spike)
            except ValueError as e:
                raise ValueError(f"ERROR: {e}, potential_ice_spike: {potential_ice_spike}, KEY: {KEY}, state.future_ice_spikes: {state.future_ice_spikes}")
          else:
            state.future_ice_spikes[index]["time_until_emergence"] -= 1
    
      # do ice spike disappearance
      for ice_spike in deepcopy(state.ice_spikes):
          if not state.ice_spikes[ice_spike]["time_remaining"]:
            state.board[int(ice_spike.split()[0])][int(ice_spike.split()[1])] = "_"
            state.ice_spikes.pop(ice_spike)
          else:
            state.ice_spikes[ice_spike]["time_remaining"] -= 1

      # debug warnings about elementals desync with board
      for y in range(SIDE_LENGTH): # debug
        for x in range(SIDE_LENGTH):
            key = f"{y} {x}"
            if state.board[y][x] == "e" and key not in state.elementals:
                input(f"WARNING: Board has 'e' at {key} but state.elementals dict is missing it!")
            if state.board[y][x] != "e" and key in state.elementals:
                input(f"WARNING: Elementals dict has {key} but state.board is '{state.board[y][x]}'!")
            if state.board[y][x] == "e" and not any([key in state.elemental_memories[bot_name] for bot_name in state.elemental_memories]):
                input(f"WARNING: Elemental memories missing {key}!")

      # do elemental actions
      for key in deepcopy(state.elementals):
        if key not in state.elementals.keys(): # if it's dead
            continue
        elemental = state.elementals[key]
        OWNER = elemental["visible_stats"]["allegiance"]
        INFUSION_MULTIPLIER = (2 if elemental["visible_stats"]["infused"] else 1)
        CRIPPLE_MULTIPLIER = calculate_cripple_effect(elemental["visible_stats"]["crippled"])
        COORDINATES = list(map(int, key.split()))
        delta_x, delta_y = get_deltas(elemental["visible_stats"]["orientation"])
        visible_target = get_target(COORDINATES, delta_x, delta_y, respect_invisibility=True, is_bot=False) 
        actual_target = get_target(COORDINATES, delta_x, delta_y, respect_invisibility=False, is_bot=False)
        if elemental["visible_stats"]["slowness"]:
            state.elementals[key]["visible_stats"]["slowness"] -= 1
        if elemental["visible_stats"]["stun"]:
            state.elementals[key]["visible_stats"]["stun"] -= 1
        elif elemental["visible_stats"]["infused"] and state.bots[OWNER]["elemental_protocol"] is not None: # if it's infused and the bot has custom instructions for its infused state.elementals
            try:
                action, orientation, state.elemental_memories[OWNER][key] = state.bots[OWNER]["elemental_protocol"](list(map(int, key.split())), elemental, visible_target, state.elemental_memories[OWNER][key])
                if action and action.split()[0] == "move":
                    MOVEMENT_DIRECTION = action.split()[1]
                    MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = get_deltas(MOVEMENT_DIRECTION)
                    int(action.split()[2])
            except Exception as e:
                """state.board[key[0]][key[1]] = "_"
                del state.elementals[key]
                del state.elemental_memories[OWNER][key]""" 
                raise Exception(e) # debug
            NEW_KEY = key
            if not action:
                pass
            elif action.split()[0] == "move":
                NEW_KEY = move(key, min(int(action.split()[2]), 2 if elemental["visible_stats"]["orientation"] == MOVEMENT_DIRECTION else 1), MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y)
            elif action.split()[0] == "cast_spell":
                SPELL = ELEMENT_TO_SPELL[elemental["visible_stats"]["element"]]
                SPELL_TO_FUNCTION[SPELL](COORDINATES, delta_x, delta_y, infused=elemental["visible_stats"]["infused"], target=actual_target, name=key, source_name="elemental")
                state.elementals[key]["visible_stats"]["remaining_spell_count"] -= 1
                if not state.elementals[key]["visible_stats"]["remaining_spell_count"]:
                    damage(key, state.elementals[key]["hp"]) # kill them
                    continue
            state.elementals[NEW_KEY]["visible_stats"]["orientation"] = orientation
        elif ((is_hostile(elemental, visible_target)) and (visible_target["type"] != "elemental" or random.randint(0, 1))) or \
             (elemental["visible_stats"]["element"] == "wind" and visible_target["type"] in ["boulder", "water", "fireball"]): # If it sees an enemy, but only 50-50 chance if it's an elemental or it's a wind elemental and sees an object
            SPELL = ELEMENT_TO_SPELL[elemental["visible_stats"]["element"]]
            if SPELL == "shockwave" and visible_target["distance"] > 2:
                MOVEMENT_DIRECTION = elemental["visible_stats"]["orientation"]
                MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = get_deltas(MOVEMENT_DIRECTION)
                move(key, 2, MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y)
            else:
                SPELL_TO_FUNCTION[SPELL](COORDINATES, delta_x, delta_y, infused=elemental["visible_stats"]["infused"], target=actual_target, name=key, source_name="elemental")
                state.elementals[key]["visible_stats"]["remaining_spell_count"] -= 1
                if not state.elementals[key]["visible_stats"]["remaining_spell_count"]:
                    state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                    del state.elementals[key]
                    del state.elemental_memories[OWNER][key]
                    continue
        else: # if being peaceful, moving about
            MOVEMENT_DIRECTION = random.choice(CARDINAL_DIRECTIONS)
            MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y = get_deltas(MOVEMENT_DIRECTION)
            
            try:
                NEW_KEY = move(key, 2 if elemental["visible_stats"]["orientation"] == MOVEMENT_DIRECTION else 1, MOVEMENT_DELTA_X, MOVEMENT_DELTA_Y)
            except Exception as e:
                organize("elemental memories", state.elemental_memories) # debug
                raise Exception(e, key) # debug
            
            state.elementals[NEW_KEY]["visible_stats"]["orientation"] = random.choice(CARDINAL_DIRECTIONS)
      
      # move players from velocity
      for player_to_be_moved in state.reaction_times.copy():
        if state.bots[player_to_be_moved]["coordinates"][0] + 1 > SIDE_LENGTH-1 and state.bots[player_to_be_moved]["velocity_y"] > 0 or state.bots[player_to_be_moved]["coordinates"][0] - 1 < 0 and state.bots[player_to_be_moved]["velocity_y"] < 0:
          damage(player_to_be_moved, ATTACK_DAMAGE["crash"] * abs(state.bots[player_to_be_moved]["velocity_y"]), DEATH_MESSAGES["crash"]) 
          state.bots[player_to_be_moved]["velocity_y"] = 0
        if state.bots[player_to_be_moved]["coordinates"][1] + 1 > SIDE_LENGTH-1 and state.bots[player_to_be_moved]["velocity_x"] > 0 or state.bots[player_to_be_moved]["coordinates"][1] - 1 < 0 and state.bots[player_to_be_moved]["velocity_x"] < 0:
          damage(player_to_be_moved, ATTACK_DAMAGE["crash"] * abs(state.bots[player_to_be_moved]["velocity_x"]), DEATH_MESSAGES["crash"])
          state.bots[player_to_be_moved]["velocity_x"] = 0
        if player_to_be_moved not in state.reaction_times:
          continue
        SGN_PLAYER_VELOCITY_X = 1 if state.bots[player_to_be_moved]["velocity_x"] > 0 else (-1 if state.bots[player_to_be_moved]["velocity_x"] else 0)
        SGN_PLAYER_VELOCITY_Y = 1 if state.bots[player_to_be_moved]["velocity_y"] > 0 else (-1 if state.bots[player_to_be_moved]["velocity_y"] else 0)
        if state.board[state.bots[player_to_be_moved]["coordinates"][0] + SGN_PLAYER_VELOCITY_Y][state.bots[player_to_be_moved]["coordinates"][1] + SGN_PLAYER_VELOCITY_X] == "b":
          damage(player_to_be_moved, ATTACK_DAMAGE["crash"] * (abs(state.bots[player_to_be_moved]["velocity_x"])+abs(state.bots[player_to_be_moved]["velocity_y"])), DEATH_MESSAGES["crash"])
        elif state.board[state.bots[player_to_be_moved]["coordinates"][0] + SGN_PLAYER_VELOCITY_Y][state.bots[player_to_be_moved]["coordinates"][1] + SGN_PLAYER_VELOCITY_X] == "_":
          state.board[state.bots[player_to_be_moved]["coordinates"][0]][state.bots[player_to_be_moved]["coordinates"][1]] = "_"
          state.bot_memory_maps[player_to_be_moved][state.bots[player_to_be_moved]["coordinates"][0]][state.bots[player_to_be_moved]["coordinates"][1]] = ["_", 0]
          state.bots[player_to_be_moved]["coordinates"] = (state.bots[player_to_be_moved]["coordinates"][0] + SGN_PLAYER_VELOCITY_Y, state.bots[player_to_be_moved]["coordinates"][1] + SGN_PLAYER_VELOCITY_X)
          state.board[state.bots[player_to_be_moved]["coordinates"][0]][state.bots[player_to_be_moved]["coordinates"][1]] = player_to_be_moved[0]
          state.bot_memory_maps[player_to_be_moved][state.bots[player_to_be_moved]["coordinates"][0]][state.bots[player_to_be_moved]["coordinates"][1]] = [player_to_be_moved[0], 0]
          state.bots[player_to_be_moved]["velocity_x"] -= SGN_PLAYER_VELOCITY_X
          state.bots[player_to_be_moved]["velocity_y"] -= SGN_PLAYER_VELOCITY_Y
      
      # Before moving all state.water objects
      for y in range(SIDE_LENGTH): # debug
        for x in range(SIDE_LENGTH):
            key = f"{y} {x}"
            if state.board[y][x] == "w" and key not in state.water:
                input(f"WARNING: Board has 'w' at {key} but state.water dict is missing it!")
            if state.board[y][x] != "w" and key in state.water:
                input(f"WARNING: Water dict has {key} but state.board is '{state.board[y][x]}'!")
      
      # before moving state.elementals
      for y in range(SIDE_LENGTH): # debug
        for x in range(SIDE_LENGTH):
            key = f"{y} {x}"
            if state.board[y][x] == "e" and key not in state.elementals:
                input(f"WARNING: Board has 'e' at {key} but state.elementals dict is missing it!")
            if state.board[y][x] != "e" and key in state.elementals:
                input(f"WARNING: Elementals dict has {key} but state.board is '{state.board[y][x]}'!")
            if state.board[y][x] == "e" and not any([key in state.elemental_memories[bot_name] for bot_name in state.elemental_memories]):
                input(f"before moving state.elementals. WARNING: Elemental memories missing {key}!")

      # move objects from velocity
      for objects in [state.boulders, state.water, state.fireballs, state.elementals]:
        for key, value in objects.copy().items():
          # in case the object died or was destroyed during another iteration of this loop
          try:
            objects[key]
          except KeyError:
            continue
          
          try: # test to see if the object hits a wall
            COORDINATES = tuple(map(int, key.split()))
            if (COORDINATES[0] + 1 > SIDE_LENGTH-1+state.avalanche_progress[1] and value["velocity_y"] > 0) or (COORDINATES[0] - 1 < state.avalanche_progress[1] and value["velocity_y"] < 0):
              objects[key]["velocity_y"] = 0
              raise HitWall(f"Debug info: {key}, {objects[key]}")
            if (COORDINATES[1] + 1 > SIDE_LENGTH-1+state.avalanche_progress[0] and value["velocity_x"] > 0) or (COORDINATES[1] - 1 < state.avalanche_progress[0] and value["velocity_x"] < 0):
              objects[key]["velocity_x"] = 0
              raise HitWall(f"Debug info: {key}, {objects[key]}")
          except HitWall: # if it does hit a wall
            if (COORDINATES[1] + 1 > SIDE_LENGTH-1 and value["velocity_x"] > 0) or (COORDINATES[1] - 1 < 0 and value["velocity_x"] < 0): # still need to test just in case both
              objects[key]["velocity_x"] = 0
            if objects == state.water:
              state.board[COORDINATES[0]][COORDINATES[1]] = "_"
              del state.water[key]
              continue
            elif objects == state.fireballs:
              FIREBALL_Y, FIREBALL_X = COORDINATES
              fireball_explode(FIREBALL_Y, FIREBALL_X, source_name=None, infused=value["infused"])
              del state.fireballs[key]
              continue
            elif objects == state.elementals:
              damage(key, ATTACK_DAMAGE["crash"] * (abs(value["velocity_y"])+abs(value["velocity_x"])))
          
          # in case the object was state.water or a fireball that hit a wall or an elemental that crashed into a wall and died
          try:
            objects[key]
          except KeyError:
            continue
          
          INFUSION_MULTIPLIER = 2 if value["visible_stats"]["infused"] else 1
          SGN_NONPLAYER_VELOCITY_X = 1 if value["velocity_x"] > 0 else (-1 if value["velocity_x"] else 0)
          SGN_NONPLAYER_VELOCITY_Y = 1 if value["velocity_y"] > 0 else (-1 if value["velocity_y"] else 0)
          COORDINATES = tuple(map(int, key.split()))
          new_coordinates = (COORDINATES[0] + SGN_NONPLAYER_VELOCITY_Y, COORDINATES[1] + SGN_NONPLAYER_VELOCITY_X)
          
          # if the object has velocity
          if SGN_NONPLAYER_VELOCITY_Y or SGN_NONPLAYER_VELOCITY_X:
            try:
                NEXT_SQUARE = state.board[new_coordinates[0]][new_coordinates[1]]
            except IndexError as e: # debug 
                print(f"new_coordinates: {new_coordinates}, COORDINATES: {COORDINATES}, SGN_NONPLAYER_VELOCITY_X: {SGN_NONPLAYER_VELOCITY_X}, SGN_NONPLAYER_VELOCITY_Y: {SGN_NONPLAYER_VELOCITY_Y}, key: {key}, value: {value}, state.avalanche_progress: {state.avalanche_progress}")
                raise IndexError(e)
            NEW_KEY = " ".join([str(new_coordinates[0]), str(new_coordinates[1])])

            if NEXT_SQUARE == "f":
                try:
                    state.fireballs[NEW_KEY]
                except KeyError:
                    NEXT_SQUARE = "_"
            elif NEXT_SQUARE == "w":
                try:
                    state.water[NEW_KEY]
                except KeyError:
                    NEXT_SQUARE = "_"

            if NEXT_SQUARE == "_":
                state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                del objects[key]
                objects[NEW_KEY] = value
                state.board[new_coordinates[0]][new_coordinates[1]] = "b" if objects == state.boulders else "w" if objects == state.water else "f" if objects == state.fireballs else "e"
                if objects == state.elementals:
                    state.elemental_memories[state.elementals[NEW_KEY]["visible_stats"]["allegiance"]][NEW_KEY] = state.elemental_memories[state.elementals[NEW_KEY]["visible_stats"]["allegiance"]][key]
                    del state.elemental_memories[state.elementals[NEW_KEY]["visible_stats"]["allegiance"]][key]
            elif NEXT_SQUARE.isupper() or NEXT_SQUARE == "e": # if there is a bot_name or elemental there
                if NEXT_SQUARE.isupper():
                    TARGET_NAME = state.letters[NEXT_SQUARE]
                else:
                    TARGET_NAME = NEW_KEY
                if objects == state.boulders:
                    damage(TARGET_NAME, INFUSION_MULTIPLIER * (ATTACK_DAMAGE["boulder"] * abs(SGN_NONPLAYER_VELOCITY_X) + ATTACK_DAMAGE["boulder"] * abs(SGN_NONPLAYER_VELOCITY_Y)), DEATH_MESSAGES["boulder"], False, "earth", source_name=value["source_name"])
                    value["velocity_x"] = 0
                    value["velocity_y"] = 0
                elif objects == state.water:
                    damage(TARGET_NAME, INFUSION_MULTIPLIER * (ATTACK_DAMAGE["wave"] * abs(SGN_NONPLAYER_VELOCITY_X) + ATTACK_DAMAGE["wave"] * abs(SGN_NONPLAYER_VELOCITY_Y)), DEATH_MESSAGES["wave"], False, "water", source_name=value["source_name"])
                    apply_velocity = True
                    if TARGET_NAME in state.reaction_times:
                        dictionary = state.bots
                    elif TARGET_NAME in state.elementals.keys():
                        dictionary = state.elementals
                    else:
                        apply_velocity = False
                    if apply_velocity:
                        dictionary[TARGET_NAME]["velocity_x"] += SGN_NONPLAYER_VELOCITY_X * 3 * INFUSION_MULTIPLIER
                        dictionary[TARGET_NAME]["velocity_y"] += SGN_NONPLAYER_VELOCITY_Y * 3 * INFUSION_MULTIPLIER
                    state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                    del state.water[key]
                elif objects == state.fireballs:
                    FIREBALL_Y, FIREBALL_X = map(int, key.split())
                    try:
                        value["infused"]
                    except KeyError:
                        organize("value", value) # debug
                    fireball_explode(FIREBALL_Y+SGN_NONPLAYER_VELOCITY_Y, FIREBALL_X+SGN_NONPLAYER_VELOCITY_X, source_name=state.fireballs[key]["source_name"], infused=value["infused"])
                    state.board[FIREBALL_Y][FIREBALL_X] = "_"
                    del state.fireballs[key]
            elif NEXT_SQUARE == "f":
                if objects == state.fireballs:
                    fireball_explode(COORDINATES[0], COORDINATES[1], source_name=None, infused=value["infused"])
                    state.fireballs[NEW_KEY]["velocity_x"] += value["velocity_x"]
                    state.fireballs[NEW_KEY]["velocity_y"] += value["velocity_y"]
                elif objects == state.water:
                    state.board[new_coordinates[0]][new_coordinates[1]] = "_"
                    del state.fireballs[NEW_KEY]
                else: # objects is state.boulders or state.elementals
                    fireball_explode(*map(int, NEW_KEY.split()), source_name=None, infused=state.fireballs[NEW_KEY]["infused"])
                    del state.fireballs[NEW_KEY]
                
                if objects != state.elementals or key in state.elementals: # if not an elemental or an elemental that is still alive
                    try:
                        objects[key]
                    except KeyError:
                        raise KeyError(objects, key) # debug
                    objects[NEW_KEY] = objects[key]
                    state.board[new_coordinates[0]][new_coordinates[1]] = "b" if objects == state.boulders else "w" if objects == state.water else "f" if objects == state.fireballs else "e"
                    state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                    del objects[key]
            elif NEXT_SQUARE == "b":
                if objects == state.fireballs:
                    fireball_explode(COORDINATES[0], COORDINATES[1], source_name=None, infused=value["infused"])
                    state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                    del state.fireballs[key]
                elif objects == state.elementals:
                    damage(key, (abs(objects[key]["velocity_y"]) + abs(objects[key]["velocity_x"])) * ATTACK_DAMAGE["crash"])
                else:
                    if objects == state.water:
                        state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                        del objects[key]
                    if any([state.boulders[NEW_KEY][f"velocity_{axis}"] * value[f"velocity_{axis}"] < 0 or (state.boulders[NEW_KEY][f"velocity_{axis}"] == 0 and value[f"velocity_{axis}"] != 0) for axis in ["x", "y"]]): # if they are different directions in any axis or it was 0 and now has movement
                        state.boulders[NEW_KEY]["source_name"] = value["source_name"]
                    state.boulders[NEW_KEY]["velocity_x"] += value["velocity_x"]
                    state.boulders[NEW_KEY]["velocity_y"] += value["velocity_y"]
                    if objects == state.boulders:
                        state.boulders[key]["velocity_x"] = state.boulders[key]["velocity_y"] = 0
            elif NEXT_SQUARE == "w":
                try:
                    state.water[NEW_KEY]
                except KeyError:
                    NEXT_SQUARE = "_"

                if objects == state.fireballs:
                    state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                    del state.fireballs[key]
                else:
                    VECTOR_SUMS = [value[f"velocity_{axis}"] + state.water[NEW_KEY][f"velocity_{axis}"] for axis in ["y", "x"]]
                    for axis_index, axis in enumerate(["y", "x"]):
                        if not value[f"velocity_{axis}"]:
                            continue
                        elif value[f"velocity_{axis}"] * VECTOR_SUMS[axis_index] > 0: # if both negative or both positive
                            state.water[NEW_KEY] # debug
                            state.water[NEW_KEY][f"velocity_{axis}"] = VECTOR_SUMS[axis_index]
                            if objects == state.water and not value[f"velocity_{['y', 'x'][1-axis_index]}"]:
                                state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                                del state.water[key]
                                continue
                        elif not VECTOR_SUMS[axis_index]: # if they are equal magnitude opposite directions
                            if objects == state.water and not value[f"velocity_{['y', 'x'][1-axis_index]}"]:
                                state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                                del state.water[key]
                            else: # if it's a boulder or moving in perpendicular axis
                                objects[key][f"velocity_{axis}"] = 0
                            if not state.water[NEW_KEY][f"velocity_{['y', 'x'][1-axis_index]}"]:
                                state.board[new_coordinates[0]][new_coordinates[1]] = "_"
                                del state.water[NEW_KEY]
                                break
                            else: # if it's moving in perpendicular axis
                                state.water[NEW_KEY][f"velocity_{axis}"] = 0
                        elif value[f"velocity_{axis}"] * VECTOR_SUMS[axis_index] < 0: # if one negative and the other positive
                            objects[key][f"velocity_{axis}"] = VECTOR_SUMS[axis_index] + (1 if VECTOR_SUMS[axis_index] < 0 else -1) 
                            if not state.water[NEW_KEY][f"velocity_{['y', 'x'][1-axis_index]}"]:
                                del state.water[NEW_KEY]
                                state.board[new_coordinates[0]][new_coordinates[1]] = "_"
                                if objects == state.elementals:
                                    assert move(key, 1, SGN_NONPLAYER_VELOCITY_X, SGN_NONPLAYER_VELOCITY_Y) == NEW_KEY
                                else:
                                    try:
                                        assert objects in [state.boulders, state.water, state.fireballs]
                                    except AssertionError:
                                        print(key, objects) # debug
                                    state.board[new_coordinates[0]][new_coordinates[1]] = "b" if objects == state.boulders else "w" if objects == state.water else "f"
                                    state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                                    objects[NEW_KEY] = objects[key]
                                    del objects[key]
                                break
            elif NEXT_SQUARE == "i" and objects == state.water: # if it's state.water and there is an ice spike
                state.board[COORDINATES[0]][COORDINATES[1]] = "_"
                del state.water[key]
            value["velocity_x"] += 1 if value["velocity_x"] < 0 else (-1 if value["velocity_x"] else 0)
            value["velocity_y"] += 1 if value["velocity_y"] < 0 else (-1 if value["velocity_y"] else 0)
          elif objects == state.fireballs: # if it's a fireball without any velocity
              fireball_explode(COORDINATES[0], COORDINATES[1], source_name=value["source_name"], infused=value["infused"])
              state.board[COORDINATES[0]][COORDINATES[1]] = "_"
              del state.fireballs[key]
          elif objects == state.water: # if it's state.water without any velocity
              state.board[COORDINATES[0]][COORDINATES[1]] = "_"
              del state.water[key]
      
      # After moving all state.water objects
      for y in range(SIDE_LENGTH): # debug
        for x in range(SIDE_LENGTH):
            key = f"{y} {x}"
            if state.board[y][x] == "w" and key not in state.water:
                input(f"WARNING: Board has 'w' at {key} but state.water dict is missing it!")
            if state.board[y][x] != "w" and key in state.water:
                input(f"WARNING: Water dict has {key} but state.board is '{state.board[y][x]}'!")

      # find out if avalanche or else time remaining
      do_avalanche = False
      if state.current_time < AVALANCHE_STARTING_TIME:
        state.time_until_avalanche = AVALANCHE_STARTING_TIME - state.current_time
        if not state.time_until_avalanche:
            do_avalanche = True
      else:
        state.time_until_avalanche = AVALANCHE_PERIODICITY - ((state.current_time - AVALANCHE_STARTING_TIME) % AVALANCHE_PERIODICITY)
        if state.time_until_avalanche == AVALANCHE_PERIODICITY:
            do_avalanche = True
      print(f"Time until avalanche: {state.time_until_avalanche}")
      
      # do avalanche
      if do_avalanche:
        #display_map(state.board) # debug
        axis = state.current_time // AVALANCHE_PERIODICITY % 2
        for direction in [0, 1]:
            for y in [state.avalanche_progress[axis] if direction else SIDE_LENGTH-1 - state.avalanche_progress[axis]] if axis else range(SIDE_LENGTH):
                for x in [state.avalanche_progress[axis] if 1-direction else SIDE_LENGTH-1 - state.avalanche_progress[axis]] if 1-axis else range(SIDE_LENGTH):
                    if state.board[y][x].isupper() or state.board[y][x] == "e":
                        print(f"y: {y}, x: {x}, axis: {axis}, direction: {direction}") # debug                        
                        bot_name = state.letters[state.board[y][x]]
                        bot_coordinates = state.bots[bot_name]["coordinates"]
                        displace(y, x, axis, direction)
                        if bot_coordinates == state.bots[bot_name]["coordinates"] and state.bots[bot_name]["hp"] > 0: # if the bot didn't move
                            input(f"WARNING: Bot {bot_name} at {bot_coordinates} didn't move during avalanche! Debug info: y: {y}, x: {x}, axis: {axis}, direction: {direction}") # debug
                        state.board[y][x] = "p"
                    elif state.board[y][x] == "f":
                        fireball_explode(y, x, None)
                        del state.fireballs[f"{y} {x}"]
                    elif state.board[y][x] == "w":
                        del state.water[f"{y} {x}"]
                    elif state.board[y][x] == "b":
                        del state.boulders[f"{y} {x}"]
                    elif state.board[y][x] == "i":
                        del state.ice_spikes[f"{y} {x}"]
                    state.board[y][x] = "p"
        state.avalanche_progress[axis] += 1
      
      # rewards for R_bot
      if AI_NAME in state.reaction_times:
        _add_reward_to_last_steps(state.memories[AI_NAME], +0.50, last_n=1)
        
        if AI_NAME in bot_actions:
            if (state.recommended_action == bot_actions[AI_NAME][0].split()[0] and not (state.recommended_action == "cast_spell" and bot_actions[AI_NAME][0].split()[1] in ["shield", "mana_blast"])) or (bot_actions[AI_NAME][0].split()[0] == "cast_spell" and state.recommended_action == bot_actions[AI_NAME][0].split()[1]):
                _add_reward_to_last_steps(state.memories[AI_NAME], +10.0 * state.guide_relevance, last_n=1)
            else:
                _add_reward_to_last_steps(state.memories[AI_NAME], -11.0 * state.guide_relevance, last_n=1)

            if state.recommended_orientation == state.bots[AI_NAME]["visible_stats"]["orientation"]:
                _add_reward_to_last_steps(state.memories[AI_NAME], +10.0 * state.guide_relevance, last_n=1)
            else:
                _add_reward_to_last_steps(state.memories[AI_NAME], -11.0 * state.guide_relevance, last_n=1)
        #else:
        #    _add_reward_to_last_steps(state.memories[AI_NAME], -22.0 * state.guide_relevance, last_n=1)

      state.current_time += 1
      state.max_shield -= 1 if not random.randint(0, 4) and state.max_shield else 0

      if PAUSE_BETWEEN_TURNS and not ("Player" in state.reaction_times and state.bots["Player"]["visible_stats"]["hybernation"]):
        input("\nPress enter to continue ")
      clear() # remove # when not debugging, add # when debugging
      
      if "Player" not in state.reaction_times or DEBUG_MODE:
          for death_message in state.death_message_queue:
            display_info_message(death_message)
    
      # if only one team remains, that team wins and the loop is exited
      team_index = next((team_index for team_index, team_members in enumerate(TEAMS) if set(state.reaction_times.keys()).issubset(set(team_members))), None)
      if team_index is not None and TEAM_MODE:
        print(f"Only team {team_index} remains")
        break 
    
    # display final state.board
    if MAP_DISPLAYED:
        display_map(state.board)

    # determine winner and display it
    if EMPTY_MODE:
        if state.reaction_times:
            WINNER = list(state.reaction_times.keys())[0]
        else:
            WINNER = ""
    else:
        try:
            WINNER = list(state.reaction_times.keys())[0] # the winner is the only remaining bot_name
        except IndexError: # if the remaining players died simultaneously, the winner is chosen based on fastest reaction speed
            REMAINING_PLAYERS = [death_message[0] for death_message in state.death_message_queue]
            fastest = {}
            for remaining_player in REMAINING_PLAYERS:
                if not fastest or state.final_reaction_times[remaining_player] < list(fastest.values())[0]:
                    fastest = {remaining_player: state.final_reaction_times[remaining_player]}
            WINNER = list(fastest.keys())[0]
    
    print(f"The winner is {WINNER}")
    if TEAM_MODE:
        print(f"(from team {state.bots[WINNER]['visible_stats']['team']})")
    state.previous_winner = WINNER

    # r_bot learning procedure
    if AI_NAME in state.bots:
        # reward r_bot if won
        if WINNER == AI_NAME:
            _add_reward_to_last_steps(state.memories[AI_NAME], +50.0, last_n=1)
            state.time_r_bot_survived = state.current_time
            state.r_bot_wins += 1

        finalize_episode_and_store(state.memories[AI_NAME])

        traj = state.memories[AI_NAME]["rbot_trajs"][-1]
        total_reward = sum(step["reward"] for step in traj)
        avg_reward = total_reward / len(traj)
        episode_len = len(traj)

        print(f"[R-Bot] Episode {len(state.memories['R_bot']['rbot_trajs'])}: "
            f"steps={episode_len:4d}, total_reward={total_reward:8.2f}, avg={avg_reward:6.3f}") # debug

        acts = Counter(step["action"] for step in traj)
        print(f"    Action distribution this episode: {dict(acts)}")
        
        #try:
        #    state.win_counts[PLAYER_ONLINE_TEXT]["R"]
        #except KeyError as e:
        #    input(f"KeyError: {e}. state.win_counts: {state.win_counts}") # debug
        #else:
        train_after_episode(state.memories[AI_NAME])

        save_memory_pickle(state.memories[AI_NAME], "rbot_memory.pkl")

    # win count file
    if not DEBUG_MODE and not EMPTY_MODE:
        # if there was no file, and therefore no data
        if None in state.win_counts_data.values(): # if not 1 then not any
            assert all([value is None for value in state.win_counts_data.values()]) # still, just in case

            # fills in the rest of the win counts as 0
            for player_online_text in state.win_counts:
                if player_online_text in ["offline_no_team", "online_no_team"]:
                    for person in state.bots: 
                        if person[0] not in state.win_counts[player_online_text]:
                            state.win_counts[player_online_text][person[0]] = 0
                else:
                    for team_index, _ in enumerate(TEAMS):
                        if team_index not in state.win_counts[player_online_text]:
                            state.win_counts[player_online_text][team_index] = 0

        
        if TEAM_MODE:
            state.win_counts[PLAYER_ONLINE_TEXT][state.bots[WINNER]["visible_stats"]["team"]] += 1
        else:
            state.win_counts[PLAYER_ONLINE_TEXT][WINNER[0]] += 1
        state.win_counts["offline_no_team"]["P"] = 0 # so it doesn't get an error

        # save win counts to file
        with open(FILE_PATH, "w") as file:
            file.write("\n".join(
                    list(",".join(f"{bot_name[0]}:{state.win_counts[key][bot_name[0]]}" for bot_name in state.bots) for key in ["online_no_team", "offline_no_team"]) +
                    list(",".join(f"{team_name}:{state.win_counts[key][team_name]}" for team_name, _ in enumerate(TEAMS)) for key in ["online_team", "offline_team"])
                )
            )

    # If pause between rounds, wait for input before starting next round
    if PAUSE_BETWEEN_ROUNDS:
        input()
except Exception as e: # debug
    print("Exception. Btw, here is the state.board the moment before:")
    display_map(state.board) # since the state.board otherwise displayed is slightly outdated
    raise Exception(e)