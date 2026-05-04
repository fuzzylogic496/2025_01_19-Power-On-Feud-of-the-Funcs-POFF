import state
from config import *

import matplotlib.pyplot as plt

total_game_count = sum(state.win_counts[PLAYER_ONLINE_TEXT].values())
del state.win_counts["offline_no_team"]["P"]
state.win_counts[PLAYER_ONLINE_TEXT] = dict(sorted(state.win_counts[PLAYER_ONLINE_TEXT].items(), key=lambda item: item[1]))
plt.pie(
    state.win_counts[PLAYER_ONLINE_TEXT].values(), 
    labels=state.win_counts[PLAYER_ONLINE_TEXT].keys(),
    autopct=lambda percentage: f"{percentage:.1f}%\n{percentage / 100 * total_game_count:.0f}"
)
plt.title(f"Total games: {total_game_count}\nAverage: {100/len(state.win_counts[PLAYER_ONLINE_TEXT]):.1f}% ({total_game_count/len(state.win_counts[PLAYER_ONLINE_TEXT]):.1f})")
plt.axis("equal")
plt.show()
state.win_counts["offline_no_team"]["P"] = 0