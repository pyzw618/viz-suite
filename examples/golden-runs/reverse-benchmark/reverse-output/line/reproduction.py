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

SERIES = [{"name": "Series A", "values": [11.975, 17.988, 15.014, 23.935, 19.948, 27.987], "x": [0, 1, 2, 3, 4, 5]}, {"name": "Series B", "values": [7.923, 9.949, 13.936, 15.962, 18.968, 21.974], "x": [0, 1, 2, 3, 4, 5]}]
COLORS = {"Series A": "#0072B2", "Series B": "#D55E00"}
AX_RECT = [0.13, 0.15000000000000002, 0.8, 0.7]
XLIM = [-0.305, 5.3]; YLIM = [-0.051, 31.974]
TITLE = "Weekly Trend by Series"
XLABEL = "Week"
YLABEL = "Value"
XTICKS = [0, 1, 2, 3, 4, 5]
YTICKS = [0, 5, 10, 15, 20, 25, 30]

def main():
    fig = plt.figure(figsize=(10.0, 7.0), dpi=100, facecolor='white')
    ax = fig.add_axes(AX_RECT)
    for s in SERIES:
        ax.plot(s['x'], s['values'], color=COLORS.get(s['name'], '#0072B2'), marker='o',
                linewidth=2, markersize=5, label=s['name'])
    if XLIM: ax.set_xlim(XLIM)
    if YLIM: ax.set_ylim(YLIM)
    if XTICKS: ax.set_xticks(XTICKS)
    if YTICKS: ax.set_yticks(YTICKS)
    ax.legend(loc='upper left', frameon=False, fontsize=9)
    ax.set_title(TITLE, fontsize=14, pad=12)
    if XLABEL: ax.set_xlabel(XLABEL, fontsize=10)
    if YLABEL: ax.set_ylabel(YLABEL, fontsize=10)
    style_axes(ax)
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
