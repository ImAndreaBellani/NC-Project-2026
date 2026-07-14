#!/usr/bin/env python3

from pathlib import Path
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt


# =====================================================
# CONFIGURAZIONE
# =====================================================

INPUT_FOLDER = Path("..") / ".." / Path("data") / Path("input") / Path("traffic_distributions")
OUTPUT_FILE = Path("..") / ".." / Path("data") / Path("output") / Path("traffic_cdfs.png")


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

percentile_colors = {
    "50pct": colors[0],
    "80pct": colors[1],
    "95pct": colors[2],
    "99pct": colors[3],
}

mpl.rcParams.update({
    'figure.figsize': (4.6, 2.4),
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


def stile_assi(ax):
    ax.tick_params(
        axis='both',
        which='major',
        labelsize=11,
        width=1.0,
        length=4,
        direction='in'
    )

    for spine in ax.spines.values():
        spine.set_linewidth(1.2)



# =====================================================
# LETTURA DISTRIBUZIONI
# =====================================================

def read_cdf(filename):
    """
    Legge una CDF nel formato:

    size    cdf

    esempio:
    0       0
    10000   15
    30000   50
    """

    values = []

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            x, y = map(float, line.split())

            values.append((x, y))

    values = np.array(values)

    return values[:, 0], values[:, 1]



# =====================================================
# PLOT
# =====================================================

def plot_all_cdfs(folder):

    files = sorted(folder.glob("*"))

    fig, ax = plt.subplots(figsize=(4.6, 2.4))


    for i, file in enumerate(files):

        if not file.is_file():
            continue

        x, y = read_cdf(file)

        # Assicura che la CDF parta da 0
        if y[0] != 0:
            x = np.concatenate(([x[0]], x))
            y = np.concatenate(([0], y))

        ax.plot(
            x,
            y,
            color=colors[i % len(colors)],
            linewidth=1.6,
            label=file.stem
        )


    ax.set_xlabel("Flow size (Bytes)")
    ax.set_ylabel("CDF (%)")


    ax.set_ylim(0, 100)

    ax.set_yticks(
        [0, 20, 40, 60, 80, 100]
    )


    # scala logaritmica per evidenziare meglio
    # la coda delle distribuzioni
    ax.set_xscale("log")


    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(False)

    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        handlelength=2.5,
        borderpad=0.2,
        labelspacing=0.4
    )


    stile_assi(ax)


    plt.tight_layout(rect=[0, 0, 0.75, 1])

    plt.savefig(
        OUTPUT_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

# =====================================================
# MAIN
# =====================================================

def get_percentile(x, cdf, percentile):
    """
    Estrae il valore x corrispondente al percentile richiesto.
    """

    idx = np.where(cdf >= percentile)[0]

    if len(idx) == 0:
        return x[-1]

    return x[idx[0]]


def plot_percentiles_histogram(folder):

    files = sorted(folder.glob("*"))

    distributions = []
    percentile_values = {
        "50pct": [],
        "80pct": [],
        "95pct": [],
        "99pct": []
    }


    for file in files:

        if not file.is_file():
            continue

        x, y = read_cdf(file)

        distributions.append(file.stem)

        percentile_values["50pct"].append(
            get_percentile(x, y, 50)
        )

        percentile_values["80pct"].append(
            get_percentile(x, y, 80)
        )

        percentile_values["95pct"].append(
            get_percentile(x, y, 95)
        )

        percentile_values["99pct"].append(
            get_percentile(x, y, 99)
        )


    fig, ax = plt.subplots(figsize=(7.5, 4.5))


    n = len(distributions)

    x_pos = np.arange(n)

    width = 0.18


    offsets = {
        "50pct": -1.5 * width,
        "80pct": -0.5 * width,
        "95pct":  0.5 * width,
        "99pct":  1.5 * width,
    }


    for percentile, values in percentile_values.items():

        ax.bar(
            x_pos + offsets[percentile],
            values,
            width,
            color=percentile_colors[percentile],
            label=percentile
        )


    ax.set_ylabel("Flow size (Bytes)")


    ax.set_xticks(x_pos)
    ax.set_xticklabels(
        distributions,
        rotation=35,
        ha="right"
    )


    ax.set_yscale("log")


    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(False)


    ax.legend(
        frameon=False,
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.15)
    )


    ax.tick_params(
        axis="x",
        which="major",
        pad=8
    )


    stile_assi(ax)


    # spazio manuale per legenda e label asse x
    fig.subplots_adjust(
        left=0.12,
        right=0.98,
        bottom=0.28,
        top=0.80
    )


    output = OUTPUT_FILE.parent / "traffic_percentiles.png"

    plt.savefig(
        output,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print(
        f"Grafico percentili salvato in {output}"
    )

def plot_distribution_shapes(folder):

    files = sorted(folder.glob("*"))

    fig, ax = plt.subplots(figsize=(4.6, 5.2))

    spacing = 1.4

    yticks = []
    yticklabels = []

    distributions = []

    # Lettura distribuzioni e calcolo dei massimi reali
    for file in files:

        if not file.is_file():
            continue

        x, cdf = read_cdf(file)

        # PDF reale (senza normalizzazione)
        pdf = np.diff(
            np.concatenate(([0], cdf))
        ).astype(float)

        pdf /= 100.0

        max_pdf = pdf.max()

        distributions.append(
            (file, x, pdf, max_pdf)
        )


    for i, (file, x, pdf, max_pdf) in enumerate(distributions):

        # normalizzazione solo per avere la stessa altezza grafica
        pdf_plot = pdf / max_pdf if max_pdf > 0 else pdf

        offset = (len(distributions) - 1 - i) * spacing

        ax.plot(
            x,
            pdf_plot + offset,
            color=colors[i % len(colors)],
            linewidth=1.6,
            alpha=0.75,
            label=file.stem
        )

        ax.fill_between(
            x,
            offset,
            pdf_plot + offset,
            color=colors[i % len(colors)],
            alpha=0.18
        )


        # Tacche con valori reali della distribuzione
        yticks.extend([
            offset,
            offset + 0.5,
            offset + 1.0
        ])

        yticklabels.extend([
            "0",
            f"{max_pdf/2:.2f}",
            f"{max_pdf:.2f}"
        ])


    ax.set_xscale("log")

    ax.set_xlabel("Flow size (Bytes)")
    ax.set_ylabel("Probability density")


    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)


    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(False)


    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        handlelength=2.5,
        borderpad=0.2,
        labelspacing=0.4
    )


    stile_assi(ax)


    output = OUTPUT_FILE.parent / "traffic_distributions.png"


    plt.savefig(
        output,
        dpi=300,
        bbox_inches="tight"
    )


    plt.close()


    print(
        f"Grafico distribuzioni salvato in {output}"
    )

if __name__ == "__main__":

    if not INPUT_FOLDER.exists():
        raise RuntimeError(
            f"Cartella non trovata: {INPUT_FOLDER}"
        )

    plot_all_cdfs(INPUT_FOLDER)

    plot_percentiles_histogram(INPUT_FOLDER)

    plot_distribution_shapes(INPUT_FOLDER)

    print(
        f"Grafico salvato in {OUTPUT_FILE}"
    )