import pickle
import matplotlib.pyplot as plt
import numpy as np
import torch
from rbot_min_trainer import PolicyValueNet, _load_params_into_model
from config import INPUT_SIZE, ACTIONS, CARDINAL_DIRECTIONS
from utils import get_input_dict

with open("rbot_memory.pkl", "rb") as f:
    memory = pickle.load(f)

params = memory.get("nn_params", {})

# Get input feature names
input_keys = list(get_input_dict().keys())

"""
# Visualize weight heatmaps
weight_keys = [k for k in params.keys() if k.startswith('W') or k == 'value_W']
if weight_keys:
    fig, axes = plt.subplots(1, len(weight_keys), figsize=(15, 5))
    if len(weight_keys) == 1:
        axes = [axes]
    for i, key in enumerate(weight_keys):
        if params[key].ndim == 2:
            axes[i].imshow(params[key], cmap="viridis")
            axes[i].set_title(f"Weights: {key}")
            axes[i].set_xlabel("Columns")
            axes[i].set_ylabel("Rows")
    plt.tight_layout()
    plt.show()
else:
    print("No weight parameters found to visualize.")
"""

def build_sample_input(recommended_action="move", recommended_orientation="east"):
    sample = get_input_dict()
    for key in sample:
        sample[key] = 0.0
    sample[f"recommended_action_{recommended_action}"] = 1.0
    sample[f"recommended_orientation_{recommended_orientation}"] = 1.0
    return np.array(list(sample.values()), dtype=np.float32)

from utils import softmax

# Saliency visualization: Show input feature importance for value prediction
if params:
    model = PolicyValueNet()
    _load_params_into_model(model, params)
    model.eval()

    # Compute effective linear influence: input to output weights (ignoring ReLU nonlinearity)
    # W1: (input, hidden), W2: (hidden, output), value_W: (1, hidden)
    W1 = params["W1"]  # (input, hidden)
    W2 = params["W2"]  # (hidden, output)
    value_W = params["value_W"]  # (1, hidden)
    b1 = params.get("b1", np.zeros(W1.shape[1], dtype=np.float32))

    # Compute logits for each input feature individually (set to 1, others 0)
    num_inputs = len(input_keys)
    num_outputs = len(ACTIONS) + len(CARDINAL_DIRECTIONS)
    logits_matrix = np.zeros((num_outputs, num_inputs))

    for i in range(num_inputs):
        x_np = np.zeros(num_inputs, dtype=np.float32)
        x_np[i] = 1.0
        hidden = np.maximum(0, x_np @ W1 + b1)  # ReLU
        action_logits = hidden @ model.fc_action.weight.detach().cpu().numpy().T + model.fc_action.bias.detach().cpu().numpy()
        orient_logits = hidden @ model.fc_orient.weight.detach().cpu().numpy().T + model.fc_orient.bias.detach().cpu().numpy()
        full_logits = np.concatenate([action_logits, orient_logits])
        logits_matrix[:, i] = full_logits

    # Convert logits to probabilities using softmax per head
    action_logits_matrix = logits_matrix[:len(ACTIONS), :]
    orient_logits_matrix = logits_matrix[len(ACTIONS):, :]
    action_probs_matrix = np.apply_along_axis(softmax, 0, action_logits_matrix)
    orient_probs_matrix = np.apply_along_axis(softmax, 0, orient_logits_matrix)
    probs_matrix = np.concatenate([action_probs_matrix, orient_probs_matrix], axis=0)

    # Split into actions and orientations
    action_saliency = probs_matrix[: len(ACTIONS)]  # (5, input)
    orient_saliency = probs_matrix[len(ACTIONS) : len(ACTIONS) + len(CARDINAL_DIRECTIONS)]  # (4, input)

    # For reference, compute the sample probabilities
    sample_input = build_sample_input(recommended_action="move", recommended_orientation="east")
    sample_tensor = torch.from_numpy(sample_input).float().unsqueeze(0)
    action_logits, orient_logits, _ = model(sample_tensor)
    sample_action_probs = torch.softmax(action_logits, dim=1)[0].detach().cpu().numpy()
    sample_orient_probs = torch.softmax(orient_logits, dim=1)[0].detach().cpu().numpy()
    print("Sample input (move,east) action probs:", sample_action_probs)
    print("Sample input (move,east) orientation probs:", sample_orient_probs)
    print("Probability for move when only recommended_action_move=1:", action_probs_matrix[ACTIONS.index('move'), input_keys.index('recommended_action_move')])
    print("Probability for east when only recommended_orientation_east=1:", orient_probs_matrix[CARDINAL_DIRECTIONS.index('east'), input_keys.index('recommended_orientation_east')])


    action_vmax = np.abs(action_saliency).max()
    orient_vmax = np.abs(orient_saliency).max()

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), constrained_layout=True)

    im0 = axes[0].imshow(action_saliency, cmap='RdBu_r', aspect='auto', vmin=-action_vmax, vmax=action_vmax)
    axes[0].set_title("Action Influence Grid")
    axes[0].set_ylabel("Actions")
    axes[0].set_xticks(range(INPUT_SIZE))
    axes[0].set_xticklabels(input_keys, rotation=45, ha='right')
    axes[0].set_yticks(range(len(ACTIONS)))
    axes[0].set_yticklabels(ACTIONS)
    fig.colorbar(im0, ax=axes[0], orientation='vertical', shrink=0.8, label='Action Influence')

    im1 = axes[1].imshow(orient_saliency, cmap='RdBu_r', aspect='auto', vmin=-orient_vmax, vmax=orient_vmax)
    axes[1].set_title("Orientation Influence Grid")
    axes[1].set_xlabel("Input Feature")
    axes[1].set_ylabel("Orientations")
    axes[1].set_xticks(range(INPUT_SIZE))
    axes[1].set_xticklabels(input_keys, rotation=45, ha='right')
    axes[1].set_yticks(range(len(CARDINAL_DIRECTIONS)))
    axes[1].set_yticklabels(CARDINAL_DIRECTIONS)
    fig.colorbar(im1, ax=axes[1], orientation='vertical', shrink=0.8, label='Orientation Influence')

    plt.show()
else:
    print("No parameters loaded; skipping saliency.")