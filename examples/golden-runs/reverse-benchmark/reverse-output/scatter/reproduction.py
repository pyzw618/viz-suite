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

X = [0.392, 0.88, 1.356, 1.844, 2.333, 2.821, 3.297, 3.785, 4.274, 4.762, 5.238, 5.726, 6.215, 6.703, 7.179, 7.667, 8.156, 8.644, 9.12, 9.608]; Y = [3.884, 6.529, 8.673, 10.031, 13.247, 11.675, 13.533, 14.605, 15.391, 15.677, 13.462, 17.893, 17.607, 26.542, 22.539, 25.684, 20.323, 24.111, 24.254, 28.757]
COLOR = "#009E73"
AX_RECT = [0.13, 0.15000000000000002, 0.8, 0.7]
XLIM = [-0.009, 10.009]; YLIM = [-0.047, 34.976]
TITLE = "Spend vs Conversions"
XLABEL = "Spend"
YLABEL = "Conversions"
XTICKS = [0, 2, 4, 6, 8, 10]
YTICKS = [0, 5, 10, 15, 20, 25, 30, 35]

def main():
    fig = plt.figure(figsize=(10.0, 7.0), dpi=100, facecolor='white')
    ax = fig.add_axes(AX_RECT)
    ax.scatter(X, Y, s=42, color=COLOR, edgecolor='white', linewidth=0.7, zorder=3)
    if XLIM: ax.set_xlim(XLIM)
    if YLIM: ax.set_ylim(YLIM)
    if XTICKS: ax.set_xticks(XTICKS)
    if YTICKS: ax.set_yticks(YTICKS)
    ax.set_title(TITLE, fontsize=14, pad=12)
    if XLABEL: ax.set_xlabel(XLABEL, fontsize=10)
    if YLABEL: ax.set_ylabel(YLABEL, fontsize=10)
    style_axes(ax)
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
