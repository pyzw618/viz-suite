# -*- coding: utf-8 -*-
# 由 viz-reverse/calibrate_and_extract.py 生成；只含反推数据与测得的样式参数。
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.family'] = 'DejaVu Sans'


def style_axes(ax):
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color('#1F2937')
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(direction='out', length=4, width=0.9, colors='#1F2937', labelsize=9)
    ax.grid(False)

MATRIX = [[0.0949, 0.2511, 0.3966, 0.5443, 0.6983, 0.8502], [0.1962, 0.346, 0.4979, 0.6477, 0.7996, 0.9536], [0.0464, 0.1772, 0.3291, 0.4747, 0.6308, 0.7806], [0.2932, 0.4515, 0.597, 0.7532, 0.903, 0.9958], [0.0021, 0.1456, 0.2932, 0.4515, 0.597, 0.7173]]
VMIN, VMAX = [0, 1]
H_RECT = [0.1, 0.15, 0.72, 0.68]
CB_RECT = [0.85, 0.15, 0.035, 0.68]
TITLE = "Activation by Cohort"
XTICKS = ["C1", "C2", "C3", "C4", "C5", "C6"]
YTICKS = ["R1", "R2", "R3", "R4", "R5"]

def main():
    fig = plt.figure(figsize=(10.0, 7.0), dpi=100, facecolor='white')
    ax = fig.add_axes(H_RECT)
    im = ax.imshow(MATRIX, cmap="viridis", vmin=VMIN, vmax=VMAX, aspect='auto')
    ax.set_xticks(range(len(XTICKS))); ax.set_xticklabels(XTICKS, fontsize=9)
    ax.set_yticks(range(len(YTICKS))); ax.set_yticklabels(YTICKS, fontsize=9)
    ax.set_xticks(np.arange(-0.5, len(XTICKS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(YTICKS), 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=2)
    ax.tick_params(which='minor', length=0)
    ax.set_title(TITLE, fontsize=14, pad=12)
    if CB_RECT:
        cax = fig.add_axes(CB_RECT)
        fig.colorbar(im, cax=cax, ticks=[0, 0.25, 0.5, 0.75, 1])
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
