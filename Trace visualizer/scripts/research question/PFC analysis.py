import matplotlib as mpl
import shutil
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import operator as op


START_TIME = 2000000000
END_TIME = 2020000000

FOLDER_NAME = "alistorage_L30_T0.02_I2"
OUTPUT_FOLDER_NAME = "PFC_alistorage_30%_incast"

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
    'legend.fontsize': 11,
    'legend.frameon': False,
    'lines.linewidth': 1.8,
    'savefig.bbox': 'tight',
})


INPUT_FOLDER = Path("..") / ".." / Path("data") / "input" / FOLDER_NAME
OUTPUT_FOLDER = Path("..") / ".." / Path("data") / "output" / OUTPUT_FOLDER_NAME


CC_NAMES = {
    "DCQCN+win": "dcqcn_vwin",
    "DCQCN": "dcqcn.txt",
    "DCTCP": "dctcp",
    "HPCC": "hp",
    "TIMELY+win": "timely_vwin",
    "TIMELY": "timely.txt",
}

CC_COLORS = {
    "DCQCN+win": colors[2],
    "DCQCN":      colors[0],
    "DCTCP":      colors[4],
    "HPCC":       colors[5],
    "TIMELY+win": colors[3],
    "TIMELY":     colors[1],
}

def compute_pause_time(filename):

    if filename.stat().st_size == 0:
        return 0

    data = np.loadtxt(filename)

    if data.ndim == 1:
        data = data.reshape(1, -1)

    timestamps = data[:, 0]
    states = data[:, -1]

    pause_time = 0
    pause_start = None


    for timestamp, state in zip(timestamps, states):

        if state == 1 and pause_start is None:
            pause_start = timestamp

        elif state == 0 and pause_start is not None:

            start = max(pause_start, START_TIME)
            end = min(timestamp, END_TIME)

            if end > start:
                pause_time += end - start

            pause_start = None


    # se il file finisce mentre sei ancora in pausa
    if pause_start is not None:

        start = max(pause_start, START_TIME)
        end = END_TIME

        if end > start:
            pause_time += end - start


    return pause_time

def _stile_assi(ax):
    ax.tick_params(axis='both', which='major', labelsize=11, width=1.0, length=4, direction='in')
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)

def plot_pfc_time():

    if OUTPUT_FOLDER.exists():
        shutil.rmtree(OUTPUT_FOLDER)

    OUTPUT_FOLDER.mkdir(parents=True)


    pause_percentages = {}
    total_time = END_TIME - START_TIME


    if not INPUT_FOLDER.exists():
        raise FileNotFoundError(
            f"Input folder does not exist: {INPUT_FOLDER}"
        )


    files = list(INPUT_FOLDER.glob("*.txt"))


    for cc, substring in CC_NAMES.items():

        matching_files = [
            f for f in files
            if substring in f.name
        ]

        if len(matching_files) == 0:
            print(f"WARNING: file not found for {cc}")
            pause_percentages[cc] = 0
            continue


        if len(matching_files) > 1:
            print(f"WARNING: multiple files for {cc}, using first one")


        pause_time = compute_pause_time(matching_files[0])

        percentage = 100 * pause_time / total_time

        pause_percentages[cc] = percentage


    labels = list(pause_percentages.keys())
    values = list(pause_percentages.values())


    fig, ax = plt.subplots(figsize=(4.8, 3.0))


    x = np.arange(len(labels))


    bars = ax.bar(
        x,
        values,
        width=0.55,
        color=[
            CC_COLORS[label]
            for label in labels
        ]
    )


    # valori sopra le barre
    for bar, value in zip(bars, values):

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=9
        )


    ax.set_xticks(x)
    ax.set_xticklabels(
        labels,
        rotation=35,
        ha="right"
    )


    ax.set_ylabel(
        "PFC pause time (%)"
    )


    # scala y simile al tuo stile queue_stats
    ymax = max(values)

    if ymax == 0:
        ax.set_ylim(0, 1)
        ax.set_yticks([0, 0.5, 1])
    else:
        ymax = np.ceil(ymax / 5) * 5
        ax.set_ylim(0, ymax * 1.15)
        ax.set_yticks(np.arange(0, ymax + 1, 5))


    # stile assi identico all'altro plot
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


    _stile_assi(ax)


    plt.tight_layout()


    plt.savefig(
        OUTPUT_FOLDER / "pfc_pause_time_proportion.png",
        dpi=300
    )

    plt.close(fig)

if __name__ == "__main__":
    plot_pfc_time()