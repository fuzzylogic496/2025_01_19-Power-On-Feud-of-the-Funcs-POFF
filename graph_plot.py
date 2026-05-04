from utils import *
import state

import csv
import matplotlib.pyplot as plt

def plot_graphs(csv_file_path):
    data = []
    with open(csv_file_path, 'r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            data.append(list(map(float, row)))

    x_values = [float(row[0]) for row in data]
    y1_values = [float(row[1]) for row in data]
    y2_values = [float(row[2]) for row in data]
    y3_values = [float(row[3]) for row in data]

    # Calculate rolling average for y1 and y2
    window_size = int(len(x_values) / 10)  # Adjust the window size as needed
    
    fig, axs = plt.subplots(3, 1, figsize=(8, 6))

    axs[0].scatter(x_values, y1_values, marker="x")
    axs[0].set_title('Total reward per game')
    axs[1].scatter(x_values, y2_values, marker="x")
    axs[1].set_title('Time survived per game')
    axs[2].plot(x_values, y3_values)
    
    if 1 < window_size <= len(x_values):
        left_center = (window_size - 1) // 2
        right_center = window_size // 2

        rolling_avg_y1 = []
        rolling_avg_y2 = []
        rolling_avg_y3 = []

        for i in range(len(x_values)):
            if i < left_center:
                start = 0
                end = i + right_center + 1
            elif i >= len(x_values) - right_center:
                start = i - right_center
                end = len(x_values)
            else:
                start = i - left_center
                end = start + window_size

            count = end - start
            rolling_avg_y1.append(sum(data[j][1] for j in range(start, end)) / count)
            rolling_avg_y2.append(sum(data[j][2] for j in range(start, end)) / count)
            rolling_avg_y3.append(sum(data[j][3] for j in range(start, end)) / count)

        axs[0].plot(x_values, rolling_avg_y1, color='orange')
        axs[1].plot(x_values, rolling_avg_y2, color='orange')
        axs[2].plot(x_values, rolling_avg_y3, color='orange')


    try:
        axs[2].plot([0, max(x_values)], [y3_values[0], y3_values[-1]], linestyle='--', color='red', label='expected wins')
    except ZeroDivisionError:
        pass
    smaller_window_size = int(window_size / 3)
    if smaller_window_size:
        axs[2].axline((max(x_values)-smaller_window_size, y3_values[-smaller_window_size-1]), (max(x_values), y3_values[-1]), linestyle='--', color='green', label='current speed')
        axs[2].axline((max(x_values)-1, y3_values[-1]-1), (max(x_values), y3_values[-1]), linestyle='--', color='blue', label='ideal')
        try:
            fig.text(0.5, 0.01, f"Slope: {smaller_window_size / (y3_values[-1] - y3_values[-smaller_window_size-1]):.2f} rounds per win", ha='center', fontsize=10)
        except ZeroDivisionError:
            pass
    axs[2].set_title('Cumulative wins')
    axs[2].legend()
    plt.tight_layout()
    plt.show()

plot_graphs('rbot_log.csv')