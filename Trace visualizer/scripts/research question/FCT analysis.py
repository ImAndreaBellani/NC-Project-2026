import matplotlib as mpl
import operator as op
FILE_NAME = "FCT_alistorage_50%"
REAL_FILE_NAME = FILE_NAME+".txt"
INCAST = op.contains(FILE_NAME, "incast")

colors = [
    "#A020F0",  # viola
    "#2CA25F",  # verde
    "#4FC3F7",  # azzurro
    "#E69F00",  # arancione
    "#FFE100",  # giallo
    "#1F77B4",  # blu
    "#E41A1C",  # rosso
    "#000000",  # nero
]

mpl.rcParams.update({
    'figure.figsize': (7.0, 3.0),
    'figure.dpi': 150,
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 13,
    'axes.titlesize': 15,
    'axes.labelsize': 13,
    'axes.linewidth': 1.2,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.major.size': 4,
    'ytick.major.size': 4,
    'xtick.major.width': 1.0,
    'ytick.major.width': 1.0,
    'legend.fontsize': 11,
    'legend.frameon': False,
    'lines.linewidth': 1.8,
    'savefig.bbox': 'tight',
})

import shutil
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, ScalarFormatter


INPUT_FILE = Path("data") / "input" / REAL_FILE_NAME
OUTPUT_FOLDER = Path("data") / "output" / FILE_NAME

CC_NAMES = [
    "DCQCN+win",
    "DCQCN",
    "DCTCP",
    "HPCC",
    "TIMELY+win",
    "TIMELY",
]

CC_STYLE = {
    "DCQCN+win": dict(color=colors[2], linestyle=":", linewidth=1.8),
    "DCQCN":      dict(color=colors[0], linestyle=":", linewidth=1.8),
    "DCTCP":      dict(color=colors[4], linestyle="--", linewidth=1.8),
    "HPCC":       dict(color=colors[5], linestyle="-", linewidth=2.0),
    "TIMELY+win": dict(color=colors[3], linestyle="--", linewidth=1.8),
    "TIMELY":     dict(color=colors[1], linestyle="--", linewidth=1.8),
}

def plot_fct_99pct():

    if OUTPUT_FOLDER.exists():
        shutil.rmtree(OUTPUT_FOLDER)

    OUTPUT_FOLDER.mkdir(parents=True)

    data = np.loadtxt(INPUT_FILE)

    flow_size = data[:, 1]

    # Figura un po' più larga
    fig, ax = plt.subplots(figsize=(10, 4))

    for i, cc in enumerate(CC_NAMES):
        col = 2 + i * 3 + 2      # 99° percentile
        ax.plot(
            flow_size,
            data[:, col],
            label=cc,
            **CC_STYLE[cc]
        )

    x_incast = 500 * 1024
    # Linea verticale a 500K
    if INCAST:
        ax.axvline(
            x=x_incast,
            color="red",
            linestyle=(5, (10, 3)),
            linewidth=1.5,
        )

        ax.text(
            x_incast * 1.02,
            4,
            " incast flows",
            color="red",
            fontsize=13,
            ha="left",
            va="bottom",
        )

    ax.set_xscale("log")
    ax.set_yscale("log")

    ax.set_xlabel("Flow size (Byte)")
    ax.set_ylabel("FCT Slowdown")

    if INCAST:
        xticks = [
            1,
            32,
            64,
            128,
            256,
            512,
            1024,
            4096,
            16384,
            65536,
            262144,
            x_incast,       # 500K
            1048576,
            4194304,
        ]
    else:
        xticks = [
            1,
            32,
            64,
            128,
            256,
            512,
            1024,
            4096,
            16384,
            65536,
            262144,
            1048576,
            4194304,
        ]

    ax.set_xlim(flow_size.min(), xticks[-1])

    xticks = [x for x in xticks if x >= flow_size.min()]

    labels = []
    for x in xticks:
        if x == 10485760:
            labels.append("10 M")
        elif x >= 1024 * 1024:
            labels.append(f"{int(x/(1024*1024))}M")
        elif x >= 1024:
            labels.append(f"{int(x/1024)}K")
        else:
            labels.append(str(int(x)))

    ax.set_xticks(xticks)
    ax.set_xticks(xticks)
    tick_labels = ax.set_xticklabels(labels, rotation=45, ha="right")

    # Colora solo la label del punto di incast
    for tick, x in zip(tick_labels, xticks):
        if x == x_incast:
            tick.set_color("red")

    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(ScalarFormatter())

    ymin = 10 ** np.floor(np.log10(data[:, 4::3].min()))
    ymax = 10 ** np.ceil(np.log10(data[:, 4::3].max()))

    ax.set_ylim(ymin, ymax)

    ax.grid(False)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legenda sopra il grafico
    handles, labels = ax.get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.99),
        ncol=6,
        frameon=False,
        handlelength=2.5,
        columnspacing=0.8,
        handletextpad=0.4,
    )

    # Il grafico occupa tutta la larghezza, lasciando solo spazio alla legenda
    fig.subplots_adjust(
        left=0.09,
        right=0.99,
        bottom=0.20,
        top=0.82,
    )

    plt.savefig(
        OUTPUT_FOLDER / "99th_fct_slowdown.png",
        dpi=300,
    )

    plt.close(fig)

if __name__ == "__main__":
    plot_fct_99pct()