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

CATS = ["A", "B", "C", "D", "E"]
VALS = [13.333, 20.278, 9.861, 27.222, 16.806]
COLOR = "#0072B2"
AX_RECT = [0.165, 0.15000000000000002, 0.7275, 0.6]
XLIM = [-0.65, 4.65]; YLIM = [-0.556, 27.222]
TITLE = "Monthly Revenue by Channel"
XLABEL = "Channel"
YLABEL = "Revenue (k)"
YTICKS = [0, 5, 10, 15, 20, 25]

def main():
    fig = plt.figure(figsize=(4.0, 2.8), dpi=100, facecolor='white')
    ax = fig.add_axes(AX_RECT)
    ax.bar(range(len(CATS)), VALS, color=COLOR, width=0.62)
    ax.set_xticks(range(len(CATS))); ax.set_xticklabels(CATS)
    if XLIM: ax.set_xlim(XLIM)
    if YLIM: ax.set_ylim(YLIM)
    if YTICKS: ax.set_yticks(YTICKS)
    ax.set_title(TITLE, fontsize=14, pad=12)
    if XLABEL: ax.set_xlabel(XLABEL, fontsize=10)
    if YLABEL: ax.set_ylabel(YLABEL, fontsize=10)
    style_axes(ax)
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
