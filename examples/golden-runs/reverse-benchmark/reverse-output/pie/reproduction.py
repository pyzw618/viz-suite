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

LABELS = ["North", "South", "East", "West", "Central"]
VALUES = [35.302, 25.035, 19.831, 11.674, 8.158]
COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9"]
AX_RECT = [0.12, 0.1, 0.76, 0.76]
TITLE = "Share by Region"

def main():
    fig = plt.figure(figsize=(10.0, 7.0), dpi=100, facecolor='white')
    ax = fig.add_axes(AX_RECT)
    ax.pie(VALUES, labels=LABELS, colors=COLORS, startangle=90, counterclock=False,
           wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}, textprops={'fontsize': 9})
    ax.set_title(TITLE, fontsize=14, pad=14)
    ax.axis('equal')
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
