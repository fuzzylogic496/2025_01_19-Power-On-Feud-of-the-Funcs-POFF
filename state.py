from config import *

from copy import deepcopy
import os
import csv

win_counts = {"online_no_team": {}, "offline_no_team": {}, "online_team": {}, "offline_team": {}}
win_counts_data = {"online_no_team": None, "offline_no_team": None, "online_team": None, "offline_team": None}

# Check if the file exists
if os.path.exists(FILE_PATH):
    # If the file exists, read its contents into a string
    with open(FILE_PATH, "r") as file:
        contents = file.read()
        if contents:
            win_counts_data["online_no_team"], win_counts_data["offline_no_team"], win_counts_data["online_team"], win_counts_data["offline_team"] = [line.split(",") for line in contents.split("\n")]
    try:
        for index, win_counts_lines in enumerate([win_counts_data["online_no_team"], win_counts_data["offline_no_team"]]):
            for bot_name in win_counts_lines:
                win_counts[["online_no_team", "offline_no_team"][index]][bot_name[0]] = int(bot_name[2:])
        for index, win_counts_lines in enumerate([win_counts_data["online_team"], win_counts_data["offline_team"]]):
            for team_name in win_counts_lines:
                win_counts[["online_team", "offline_team"][index]][int(team_name[0])] = int(team_name[2:])
    except TypeError:
        pass
else:
    # If the file doesn't exist, create it
    with open(FILE_PATH, "w") as file:
        contents = "" # Create an empty file

boulders = {}
water = {}
fireballs = {}
elementals = {}
ice_spikes = {}
future_ice_spikes = []

avalanche_progress = [0, 0] 
time_until_avalanche = AVALANCHE_STARTING_TIME

observing = START_OBSERVING

previous_winner = ""

bots = {}
reaction_times = {}
player_funcs = {}
memories = {}
elemental_memories = {}
if TEAM_MODE:
    team_memory_maps = [deepcopy(BLANK_MEMORY_MAP) for _ in TEAMS]
bot_memory_maps = {}
info_messages = {}
final_reaction_times = {}

letters = {
    "b": "boulder",
    "f": "fireball",
    "w": "water",
    "i": "ice_spike",
    "p": "perimeter",
    "e": "elemental"
}

board = []

death_message_queue = []

max_shield = STARTING_MAX_SHIELD

current_time = 0

player_just_took_damage = False

time_r_bot_survived = 0

# get amount of wins r_bot has so far
try:
    with open("rbot_log.csv", "r", newline="") as csvfile:
        # get last row
        for row in csv.reader(csvfile): 
            pass
        
        r_bot_wins = int(row[3])
except FileNotFoundError:
    r_bot_wins = 0

recommended_action = "move"
recommended_orientation = "east"
guide_relevance = 1