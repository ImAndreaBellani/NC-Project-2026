import matplotlib as mpl
import shutil
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Questi valori verranno sostituiti dopo leggendo i dati
START_TIME = 2000000000
END_TIME = 2020000000

FOLDER_NAME = "traces_hadoop_L30_T0.02_I2"
OUTPUT_FOLDER_NAME = "LATENCY_hadoop_30%_incast"

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
    "DCQCN": "dcqcn.tr",
    "DCTCP": "dctcp",
    "HPCC": "hp",
    "TIMELY+win": "timely_vwin",
    "TIMELY": "timely.tr",
}

CC_COLORS = {
    "DCQCN+win": colors[2],
    "DCQCN":      colors[0],
    "DCTCP":      colors[4],
    "HPCC":       colors[5],
    "TIMELY+win": colors[3],
    "TIMELY":     colors[1],
}

from pathlib import Path

def _stile_assi(ax):
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

def compute_packet_latencies(filename):
    """
    Calcola la latenza end-to-end di ogni pacchetto.

    Un pacchetto è identificato da:
        (src_ip, dst_ip, src_port, dst_port, seq, is_ack)

    dove is_ack=True se il campo [10] è 'A'.

    Algoritmo:
      1) Prima passata:
            ricava la mappa ip -> nodo sorgente.

      2) Seconda passata:
            misura il tempo tra la prima comparsa sul nodo sorgente
            e la prima comparsa sul nodo destinazione.

    Ritorna:
        lista delle latenze (ns)
    """

    filename = Path(filename)

    if filename.stat().st_size == 0:
        return []

    # ==========================================================
    # Prima passata: IP -> nodo
    # ==========================================================

    ip_to_node = {}

    seen_first = set()

    with filename.open("r") as f:

        for line in f:

            parts = line.split()

            if len(parts) < 12:
                continue

            ts = int(parts[0])

            if ts < START_TIME:
                continue

            if ts > END_TIME:
                break

            node = int(parts[1].split(":")[1])

            src_ip = parts[6]
            dst_ip = parts[7]
            src_port = parts[8]
            dst_port = parts[9]

            pkt_type = parts[10]

            seq = parts[11]

            key = (
                src_ip,
                dst_ip,
                src_port,
                dst_port,
                seq,
                pkt_type == "A"
            )

            if key in seen_first:
                continue

            seen_first.add(key)

            ip_to_node.setdefault(src_ip, node)

    # ==========================================================
    # Seconda passata: misura latenze
    # ==========================================================

    departures = {}

    latencies = []

    measured = set()

    with filename.open("r") as f:

        for line in f:

            parts = line.split()

            if len(parts) < 12:
                continue

            ts = int(parts[0])

            if ts < START_TIME:
                continue

            if ts > END_TIME:
                break

            node = int(parts[1].split(":")[1])

            src_ip = parts[6]
            dst_ip = parts[7]
            src_port = parts[8]
            dst_port = parts[9]

            pkt_type = parts[10]

            seq = parts[11]

            key = (
                src_ip,
                dst_ip,
                src_port,
                dst_port,
                seq,
                pkt_type == "A"
            )

            if key in measured:
                continue

            src_node = ip_to_node.get(src_ip)
            dst_node = ip_to_node.get(dst_ip)

            if src_node is None or dst_node is None:
                continue

            # prima comparsa sul nodo sorgente
            if node == src_node:

                departures.setdefault(key, ts)

            # prima comparsa sul nodo destinazione
            elif node == dst_node:

                if key in departures:

                    latencies.append(ts - departures[key])

                    measured.add(key)

                    del departures[key]

    return latencies

def plot_packet_latency_95pct():

    if OUTPUT_FOLDER.exists():
        shutil.rmtree(OUTPUT_FOLDER)

    OUTPUT_FOLDER.mkdir(parents=True)

    files = list(INPUT_FOLDER.glob("*.txt"))

    stats = {}

    for cc, substring in CC_NAMES.items():

        matching_files = [
            f for f in files
            if substring in f.name
        ]


        latencies = np.asarray(
            compute_packet_latencies(
                matching_files[0]
            ),
            dtype=float
        )

        if len(latencies) == 0:
            stats[cc] = 0
            continue

        # ns -> us
        latencies /= 1000.0

        median = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)

        stats[cc] = {
            "median": median,
            "p95": p95,
            "p99": p99,
        }


        print(f"\n{cc}")
        print(f"Packets measured : {len(latencies)}")
        print(f"Median           : {np.median(latencies):.2f} us")
        print(f"95th percentile  : {p95:.2f} us")
        print(f"99th percentile  : {np.percentile(latencies,99):.2f} us")

    labels = [
        "DCQCN",
        "DCQCN+win",
        "TIMELY",
        "TIMELY+win",
        "DCTCP",
        "HPCC",
    ]

    x = np.arange(len(labels))

    width = 0.22

    fig, ax = plt.subplots(figsize=(6.5, 3.8))

    bars1 = ax.bar(
        x - width,
        [stats[c]["median"] for c in labels],
        width,
        color=colors[0],
        label="Median"
    )

    bars2 = ax.bar(
        x,
        [stats[c]["p95"] for c in labels],
        width,
        color=colors[1],
        label="95pct-latency"
    )

    bars3 = ax.bar(
        x + width,
        [stats[c]["p99"] for c in labels],
        width,
        color=colors[2],
        label="99pct-latency"
    )

    for bars in (bars1, bars2, bars3):

        for bar in bars:
            h = bar.get_height()

            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h,
                f"{h:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
                rotation=90
            )

    ax.set_xticks(x)

    ax.set_xticklabels(
        [" " +l for l in labels],
        rotation=35,
        ha="right"
    )

    ax.set_ylabel("Latency (us)")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _stile_assi(ax)

    ax.legend(
        loc="upper right",
        frameon=False
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_FOLDER /
        "packet_latency_95pct.png",
        dpi=300
    )

    plt.close(fig)


if __name__ == "__main__":
    plot_packet_latency_95pct()