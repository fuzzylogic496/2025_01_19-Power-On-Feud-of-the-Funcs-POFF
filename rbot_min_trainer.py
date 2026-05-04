# rbot_min_trainer.py

import state
from config import *
from utils import *

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import csv

class PolicyValueNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(INPUT_SIZE, HIDDEN_SIZE)
        self.fc_action = nn.Linear(HIDDEN_SIZE, NUM_ACTIONS)
        self.fc_orient = nn.Linear(HIDDEN_SIZE, NUM_ORIENT)
        self.fc_value = nn.Linear(HIDDEN_SIZE, 1)  # critic head

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        return self.fc_action(x), self.fc_orient(x), self.fc_value(x).squeeze(-1)

def _safe_copy_numpy_to_torch(tensor, np_arr):
    """Copy overlapping region from np_arr into tensor.data.
    If sizes mismatch, copy min-shape and init remaining elements."""
    t = tensor.data
    # ensure numpy dtype matches
    arr = np.asarray(np_arr, dtype=np.float32)
    if arr.ndim == 1:
        # bias vector
        min_len = min(t.shape[0], arr.shape[0])
        if min_len > 0:
            t[:min_len].copy_(torch.from_numpy(arr[:min_len]))
        if t.shape[0] > arr.shape[0]:
            # init remaining
            nn.init.uniform_(t[arr.shape[0]:], -0.1, 0.1)
    else:
        # matrix
        # find overlapping block
        r = min(t.shape[0], arr.shape[0])
        c = min(t.shape[1], arr.shape[1])
        if r > 0 and c > 0:
            t[:r, :c].copy_(torch.from_numpy(arr[:r, :c]))
        # init any extra rows/cols
        if t.shape[0] > arr.shape[0] or t.shape[1] > arr.shape[1]:
            nn.init.xavier_uniform_(t)  # re-init full matrix to avoid strange zeros
            # then re-overwrite the overlapping block so original values persist
            if r > 0 and c > 0:
                t[:r, :c].copy_(torch.from_numpy(arr[:r, :c]))

def _load_params_into_model(model, params):
    # params may contain: W1 (input, hidden), b1 (hidden,),
    # W2 (hidden, output) where output was action+orient in old format,
    # b2 (output,)
    # new optional keys: value_W (hidden,1) and value_b (1,)
    # Mapping to PyTorch:
    #  - model.fc1.weight: (hidden, input)  <-> params["W1"].T
    #  - model.fc1.bias: (hidden,)          <-> params["b1"]
    #  - model.fc_action.weight: (NUM_ACTIONS, hidden) <-> W2[:NUM_ACTIONS].T
    #  - model.fc_action.bias: (NUM_ACTIONS,) <-> b2[:NUM_ACTIONS]
    #  - model.fc_orient.weight: (NUM_ORIENT, hidden)  <-> next block
    #  - model.fc_orient.bias: (NUM_ORIENT,)           <-> next block
    #  - model.fc_value.weight: (1, hidden)            <-> params.get("value_W")
    #  - model.fc_value.bias: (1,)                     <-> params.get("value_b")
    try:
        # fc1
        if "W1" in params:
            W1 = params["W1"]  # expected shape (input, hidden)
            _safe_copy_numpy_to_torch(model.fc1.weight, W1.T)
        if "b1" in params:
            _safe_copy_numpy_to_torch(model.fc1.bias, params["b1"])

        # W2 (hidden, output). split columns
        if "W2" in params and "b2" in params:
            W2 = params["W2"]  # expected (hidden, output)
            b2 = params["b2"]
            # action head
            wa = W2[:, :NUM_ACTIONS] if W2.shape[1] >= NUM_ACTIONS else W2[:, :W2.shape[1]]
            ba = b2[:NUM_ACTIONS] if b2.shape[0] >= NUM_ACTIONS else b2
            _safe_copy_numpy_to_torch(model.fc_action.weight, wa.T if wa.ndim==2 else wa.reshape(1,-1))
            _safe_copy_numpy_to_torch(model.fc_action.bias, ba)

            # orient head
            start = NUM_ACTIONS
            if W2.shape[1] > start:
                wo = W2[:, start:start+NUM_ORIENT]
                bo = b2[start:start+NUM_ORIENT]
                _safe_copy_numpy_to_torch(model.fc_orient.weight, wo.T)
                _safe_copy_numpy_to_torch(model.fc_orient.bias, bo)

        # optional: separate value weights (preferred)
        if "value_W" in params and hasattr(model, "fc_value"):
            # expected (hidden, 1)
            _safe_copy_numpy_to_torch(model.fc_value.weight, params["value_W"].T)
        if "value_b" in params and hasattr(model, "fc_value"):
            _safe_copy_numpy_to_torch(model.fc_value.bias, params["value_b"])
    except Exception as e:
        print(f"Trainer: warning loading params robustly: {e}")

def _save_model_back_to_memory(model, memory):
    params = memory.setdefault("nn_params", {})
    # fc1
    params["W1"] = model.fc1.weight.detach().cpu().numpy().T.copy()  # (input, hidden)
    params["b1"] = model.fc1.bias.detach().cpu().numpy().copy()     # (hidden,)

    # fc_action and fc_orient into W2 (hidden, output)
    W_action = model.fc_action.weight.detach().cpu().numpy()   # (NUM_ACTIONS, hidden)
    W_orient  = model.fc_orient.weight.detach().cpu().numpy()  # (NUM_ORIENT, hidden)
    # concatenate rows -> shape (NUM_ACTIONS + NUM_ORIENT, hidden), then transpose
    W2 = np.concatenate([W_action, W_orient], axis=0).T.copy()  # (hidden, output)
    b2 = np.concatenate([model.fc_action.bias.detach().cpu().numpy(),
                         model.fc_orient.bias.detach().cpu().numpy()], axis=0).copy()
    params["W2"] = W2
    params["b2"] = b2

    # Save critic separately if available
    if hasattr(model, "fc_value"):
        params["value_W"] = model.fc_value.weight.detach().cpu().numpy().T.copy()  # (hidden,1) -> saved as (hidden,1)
        params["value_b"] = model.fc_value.bias.detach().cpu().numpy().copy()     # (1,)

def _discounted_returns(rewards, gamma=0.99):
    R = 0.0
    out = []
    for r in reversed(rewards):
        R = r + gamma * R
        out.append(R)
    out.reverse()
    return out

def train_after_episode(memory, lr=1e-2, gamma=0.8, epochs=5, value_coef=0.5):
    device = torch.device("cpu")
    model = PolicyValueNet().to(device)
    if "nn_params" in memory:
        try:
            _load_params_into_model(model, memory["nn_params"])
        except Exception as e:
            print(f"Trainer: warning loading params: {e}")

    optimizer = optim.Adam(model.parameters(), lr=lr)

    all_trajs = memory.get("rbot_trajs", [])
    #input(all_trajs) # debug
    if not all_trajs:
        return

    states, actions, orients, rewards, traj_lens = [], [], [], [], []
    for traj in all_trajs:
        traj_lens.append(len(traj))
        for i, step in enumerate(traj):
            states.append(step["state"])
            actions.append(int(step["action"]))
            orients.append(int(step["orient"]))
            """
            # Orientation: use previous step's orientation, or 0 if first step
            if i > 0:
                orients.append(int(traj[i - 1]["orient"]))
            else:
                orients.append(0)
            """
            rewards.append(float(step["reward"]))

    if not states:
        memory["rbot_trajs"] = []
        return

    states_t = torch.from_numpy(np.stack(states)).float().to(device)
    actions_t = torch.tensor(actions, dtype=torch.long, device=device)
    orients_t = torch.tensor(orients, dtype=torch.long, device=device)

    # compute returns per-step
    returns = []
    idx = 0
    for L in traj_lens:
        r = rewards[idx: idx+L]
        idx += L
        #input(r) # debug
        returns.extend(_discounted_returns(r, gamma=gamma))
        #input([(r[i], round(returned, 2)) for i, returned in enumerate(returns)]) # debug
    returns_t = torch.tensor(returns, dtype=torch.float32, device=device)
    
    #print(returns_t) # debug

    # Normalize returns
    returns_mean = returns_t.mean()
    returns_std = returns_t.std() + 1e-8
    returns_t = (returns_t - returns_mean) / returns_std

    #print(returns_mean) # debug
    #print(returns_std) # debug
    #input(returns_t) # debug

    for _ in range(epochs):
        optimizer.zero_grad()
        action_logits, orient_logits, values = model(states_t)

        # log-probs for chosen actions and orientations
        action_logp = torch.log_softmax(action_logits, dim=1)
        orient_logp = torch.log_softmax(orient_logits, dim=1)
        chosen_action_logp = action_logp[torch.arange(action_logp.shape[0]), actions_t]
        chosen_orient_logp = orient_logp[torch.arange(orient_logp.shape[0]), orients_t]
        logp = chosen_action_logp + chosen_orient_logp

        # Compute advantage and losses
        advantage = returns_t - values
        policy_loss = -(advantage.detach() * logp).mean()
        value_loss = value_coef * (advantage ** 2).mean()
        loss = policy_loss + value_loss

        loss.backward()
        optimizer.step()

    # Logging to CSV
    game_number = get_game_number()
    score = sum(step["reward"] for step in state.memories[AI_NAME]["rbot_trajs"][-1])
    turns_survived = state.time_r_bot_survived
    with open("rbot_log.csv", "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([game_number, score, turns_survived, state.r_bot_wins])

    _save_model_back_to_memory(model, memory)
    memory["rbot_trajs"] = []
    print("    Updated weights (actor-critic).")

    print(f"    Policy loss: {policy_loss.item():.4f}, Value loss: {value_loss.item():.4f}")
    print(f"    Mean return: {returns_t.mean().item():.2f}, Mean value: {values.mean().item():.2f}")
    #input("so something happened") # debug

def get_game_number():
    game_number = 0
    if os.path.exists("rbot_log.csv"):
        with open("rbot_log.csv", "r") as csvfile:
            reader = csv.reader(csvfile)
            for _ in range(1):  # Skip the header row
                try:
                    _ = next(reader)
                    game_number = max(int(row[0]) for row in reader)
                except (StopIteration, ValueError):
                    pass
    return game_number + 1