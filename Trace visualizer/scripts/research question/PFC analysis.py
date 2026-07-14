import matplotlib as mpl
import shutil
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Questi valori verranno sostituiti dopo leggendo i dati
START_TIME = 2000000000
END_TIME = 2020000000

FOLDER_NAME = "cache_L50_T0.02"
OUTPUT_FOLDER_NAME = "PFC"+FOLDER_NAME

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

from pathlib import Path

def compute_pfc_statistics(filename):
    """
    Calcola:
        - numero totale di eventi PAUSE
        - numero di interfacce che hanno avuto almeno una PAUSE

    Una PAUSE è ogni evento con type=1.

    Ritorna:
        pause_count, interface_count
    """

    filename = Path(filename)

    if filename.stat().st_size == 0:
        return 0, 0


    pause_count = 0
    interfaces = set()


    with filename.open("r") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) < 5:
                continue


            ts = int(parts[0])
            node_id = int(parts[1])
            if_index = int(parts[3])
            event_type = int(parts[4])


            if ts < START_TIME:
                continue

            if ts > END_TIME:
                break


            if event_type == 1:

                pause_count += 1

                interfaces.add(
                    (node_id, if_index)
                )


    return pause_count, len(interfaces)

def compute_pause_time_per_interface(filename):
    """
    Calcola il tempo totale di PFC pause per ogni interfaccia.

    La chiave dell'interfaccia è:
        (node_id, if_index)

    Formato input:
        timestamp node_id node_type if_index type

    type:
        1 -> pause
        0 -> resume

    Ritorna:
        dict {(node_id, if_index): pause_time_ns}
    """

    filename = Path(filename)

    if filename.stat().st_size == 0:
        return {}

    events = {}

    with filename.open("r") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) < 5:
                continue

            ts = int(parts[0])
            node_id = int(parts[1])
            node_type = int(parts[2])
            if_index = int(parts[3])
            event_type = int(parts[4])

            # fuori finestra
            if ts < START_TIME:
                continue

            if ts > END_TIME:
                break

            key = (node_id, if_index)

            events.setdefault(key, []).append(
                (ts, event_type)
            )


    pause_times = {}


    for interface, evs in events.items():

        evs.sort(key=lambda x: x[0])

        paused = False
        pause_start = None
        total_pause = 0


        for ts, event_type in evs:

            # PAUSE
            if event_type == 1:

                if not paused:
                    paused = True
                    pause_start = ts


            # RESUME
            elif event_type == 0:

                if paused:

                    start = max(pause_start, START_TIME)
                    end = min(ts, END_TIME)

                    if end > start:
                        total_pause += end - start

                    paused = False
                    pause_start = None


        # pausa ancora aperta alla fine
        if paused and pause_start is not None:

            start = max(pause_start, START_TIME)
            end = END_TIME

            if end > start:
                total_pause += end - start


        pause_times[interface] = total_pause


    return pause_times

def compute_total_pause_time(filename, switches_only=False):
    """
    Restituisce il tempo totale di PFC pause sommato su tutte
    le interfacce.

    switches_only=False:
        considera tutte le interfacce (switch + server).

    switches_only=True:
        considera solo le interfacce appartenenti agli switch
        (node_type != 0).
    """

    filename = Path(filename)

    if filename.stat().st_size == 0:
        return 0

    events = {}

    with filename.open("r") as f:

        for line in f:

            parts = line.split()

            if len(parts) < 5:
                continue

            ts = int(parts[0])

            if ts < START_TIME:
                continue

            if ts > END_TIME:
                break

            node_id = int(parts[1])
            node_type = int(parts[2])
            if_index = int(parts[3])
            event_type = int(parts[4])

            # Se richiesto, ignora le interfacce dei server
            # (assumendo node_type == 0 per i server)
            if switches_only and node_type == 0:
                continue

            key = (node_id, if_index)

            events.setdefault(key, []).append((ts, event_type))

    total_pause = 0

    for evs in events.values():

        evs.sort()

        paused = False
        pause_start = None

        for ts, event in evs:

            if event == 1:

                if not paused:
                    paused = True
                    pause_start = ts

            elif event == 0:

                if paused:

                    total_pause += ts - pause_start

                    paused = False
                    pause_start = None

        # pausa ancora aperta a END_TIME
        if paused:

            total_pause += END_TIME - pause_start

    return total_pause

def compute_pause_time(filename, consider_interfaces=True):
    """
    Calcola il tempo totale di PFC pause nell'intervallo:
    [START_TIME, END_TIME].

    consider_interfaces=False:
        considera tutti gli eventi come un unico FSA a due stati:
        - pause (1): inizia pausa
        - resume (0): termina pausa
        - pause consecutive e resume consecutive ignorati

    consider_interfaces=True:
        considera separatamente ogni porta dello switch:
        chiave = (node_id, if_index)

        Gli intervalli risultanti vengono poi uniti per evitare
        di contare più volte pause contemporanee.

    Ritorna il tempo totale di pausa in ns.
    """

    filename = Path(filename)

    if filename.stat().st_size == 0:
        return 0


    # ============================================================
    # Caso 1: unico FSA globale
    # ============================================================
    if not consider_interfaces:

        paused = False
        pause_start = None
        intervals = []

        with filename.open("r") as f:

            for line in f:

                line = line.strip()

                if not line:
                    continue

                parts = line.split()

                if len(parts) < 5:
                    continue

                ts = int(parts[0])
                event_type = int(parts[4])

                # eventi prima della finestra ignorati
                if ts < START_TIME:
                    continue

                # dopo END_TIME ignoriamo tutto
                if ts > END_TIME:
                    break


                # pause
                if event_type == 1:

                    if not paused:
                        paused = True
                        pause_start = ts


                # resume
                elif event_type == 0:

                    if paused:

                        start = max(pause_start, START_TIME)
                        end = min(ts, END_TIME)

                        if end > start:
                            intervals.append((start, end))

                        paused = False
                        pause_start = None


        # pausa ancora attiva a END_TIME
        if paused and pause_start is not None:

            start = max(pause_start, START_TIME)
            end = END_TIME

            if end > start:
                intervals.append((start, end))


        return sum(end - start for start, end in intervals)



    # ============================================================
    # Caso 2: FSA separato per ogni interfaccia
    # ============================================================

    events = {}

    with filename.open("r") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) < 5:
                continue


            ts = int(parts[0])
            node_id = int(parts[1])
            node_type = int(parts[2])
            if_index = int(parts[3])
            event_type = int(parts[4])


            if ts < START_TIME:
                continue

            if ts > END_TIME:
                break


            key = (node_id, if_index)

            events.setdefault(key, []).append(
                (ts, event_type)
            )


    intervals = []


    for evs in events.values():

        evs.sort(key=lambda x: x[0])

        paused = False
        pause_start = None


        for ts, event_type in evs:


            if event_type == 1:

                if not paused:
                    paused = True
                    pause_start = ts


            elif event_type == 0:

                if paused:

                    start = max(pause_start, START_TIME)
                    end = min(ts, END_TIME)

                    if end > start:
                        intervals.append((start, end))

                    paused = False
                    pause_start = None


        # pausa ancora aperta
        if paused and pause_start is not None:

            start = max(pause_start, START_TIME)
            end = END_TIME

            if end > start:
                intervals.append((start, end))



    if not intervals:
        return 0


    # ============================================================
    # Merge intervalli di porte diverse
    # ============================================================

    intervals.sort()

    merged = []

    cur_start, cur_end = intervals[0]


    for start, end in intervals[1:]:

        if start <= cur_end:
            cur_end = max(cur_end, end)

        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end


    merged.append((cur_start, cur_end))


    return sum(end - start for start, end in merged)

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


def plot_pfc_pause_distribution():

    if OUTPUT_FOLDER.exists():
        shutil.rmtree(OUTPUT_FOLDER)

    OUTPUT_FOLDER.mkdir(parents=True)


    if not INPUT_FOLDER.exists():
        raise FileNotFoundError(
            f"Input folder does not exist: {INPUT_FOLDER}"
        )


    files = list(INPUT_FOLDER.glob("*.txt"))


    pause_distributions = {}


    # ============================================================
    # Calcolo distribuzione pause per interfaccia
    # ============================================================

    for cc, substring in CC_NAMES.items():

        matching_files = [
            f for f in files
            if substring in f.name
        ]


        if len(matching_files) == 0:
            print(f"WARNING: file not found for {cc}")
            continue


        if len(matching_files) > 1:
            print(
                f"WARNING: multiple files for {cc}, using first one"
            )


        pause_per_interface = compute_pause_time_per_interface(
            matching_files[0]
        )


        # ns -> us
        values = [
            t / 1000.0
            for t in pause_per_interface.values()
        ]


        pause_distributions[cc] = values


        if values:

            print("\n", cc)

            print(
                f"Interfaces: {len(values)}"
            )

            print(
                f"Median: {np.percentile(values, 50):.2f} us"
            )

            print(
                f"95th: {np.percentile(values, 95):.2f} us"
            )

            print(
                f"99th: {np.percentile(values, 99):.2f} us"
            )


    # ============================================================
    # Plot CDF
    # ============================================================

    fig, ax = plt.subplots(
        figsize=(5.2, 3.2)
    )


    for cc, values in pause_distributions.items():

        if not values:
            continue


        values = np.sort(values)

        y = np.arange(1, len(values)+1) / len(values)


        ax.plot(
            values,
            y,
            label=cc,
            color=CC_COLORS[cc]
        )

    ax.margins(x=0.05)

    ax.set_xscale("log")

    ax.set_ylabel(
        "CDF"
    )


    ax.set_xlabel(
        "PFC pause time per interface (us)"
    )

    ax.set_ylim(0, 1)

    ax.legend(
        loc="lower right"
    )


    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


    _stile_assi(ax)


    plt.tight_layout()


    plt.savefig(
        OUTPUT_FOLDER /
        "pfc_pause_time_per_interface_cdf.png",
        dpi=300
    )


    plt.close(fig)



def plot_pfc_statistics():

    files = list(INPUT_FOLDER.glob("*.txt"))


    pause_counts = {}
    interface_counts = {}


    for cc, substring in CC_NAMES.items():

        matching_files = [
            f for f in files
            if substring in f.name
        ]


        if len(matching_files) == 0:

            pause_counts[cc] = 0
            interface_counts[cc] = 0

            continue


        pauses, interfaces = compute_pfc_statistics(
            matching_files[0]
        )


        pause_counts[cc] = pauses
        interface_counts[cc] = interfaces



    labels = list(CC_NAMES.keys())


    x = np.arange(len(labels))


    width = 0.35

    fig, ax1 = plt.subplots(
        figsize=(7.2, 3.8)
    )


    ax2 = ax1.twinx()


    # posizioni delle due barre
    bars1 = ax1.bar(
        x - width/2,
        [
            pause_counts[c]
            for c in labels
        ],
        width,
        color=colors[0],
        label="PFC pause events"
    )


    bars2 = ax2.bar(
        x + width/2,
        [
            interface_counts[c]
            for c in labels
        ],
        width,
        color=colors[1],
        label="Affected interfaces"
    )


    # valori sopra le barre
    for bar in bars1:

        height = bar.get_height()

        ax1.text(
            bar.get_x() + bar.get_width()/2,
            height,
            f"{int(height)}",
            ha="center",
            va="bottom",
            fontsize=8
        )


    for bar in bars2:

        height = bar.get_height()

        ax2.text(
            bar.get_x() + bar.get_width()/2,
            height,
            f"{int(height)}",
            ha="center",
            va="bottom",
            fontsize=8
        )


    ax1.set_xticks(x)

    ax1.set_xticklabels(
        labels,
        rotation=35,
        ha="right"
    )


    ax1.set_ylabel(
        "Number of PFC pause events"
    )


    ax2.set_ylabel(
        "Number of affected interfaces"
    )


    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)


    _stile_assi(ax1)


    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left"
    )


    plt.tight_layout()


    plt.savefig(
        OUTPUT_FOLDER /
        "pfc_pause_statistics.png",
        dpi=300
    )


    plt.close(fig)

def plot_total_pause_time():

    files = list(INPUT_FOLDER.glob("*.txt"))

    values = {}

    for cc, substring in CC_NAMES.items():

        matching_files = [
            f for f in files
            if substring in f.name
        ]

        if len(matching_files) == 0:
            values[cc] = 0
            continue


        values[cc] = compute_total_pause_time(
            matching_files[0], switches_only=True
        ) / 1000.0 /1000.0     # ns -> us -> ms


    labels = list(CC_NAMES.keys())

    x = np.arange(len(labels))


    fig, ax = plt.subplots(figsize=(5.5, 3.6))


    total_time = 1 #((END_TIME-START_TIME)*(480))/(1000 * 1000)
    bars = ax.bar(
        x,
        [(values[c]/total_time) for c in labels],
        width=0.55,
        color=colors[0]
    )


    for bar in bars:

        h = bar.get_height()

        ax.text(
            bar.get_x() + bar.get_width()/2,
            h,
            f"{h:.0f}",
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
        "Total PFC pause time (ms)"
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _stile_assi(ax)

    plt.tight_layout()

    plt.savefig(
        OUTPUT_FOLDER /
        "pfc_total_pause_time.png",
        dpi=300
    )

    plt.close(fig)

def compute_pause_durations(filename):
    """
    Restituisce la durata di ogni singolo episodio di PFC.

    Ogni campione corrisponde ad una coppia:
        PAUSE -> RESUME

    Se la simulazione termina durante una pausa,
    la durata viene chiusa a END_TIME.
    """

    filename = Path(filename)

    if filename.stat().st_size == 0:
        return []

    events = {}

    with filename.open("r") as f:

        for line in f:

            parts = line.split()

            if len(parts) < 5:
                continue

            ts = int(parts[0])

            if ts < START_TIME:
                continue

            if ts > END_TIME:
                break

            node = int(parts[1])
            ifindex = int(parts[3])
            event = int(parts[4])

            key = (node, ifindex)

            events.setdefault(key, []).append((ts, event))


    durations = []

    for evs in events.values():

        evs.sort()

        paused = False
        pause_start = None

        for ts, event in evs:

            if event == 1:

                if not paused:
                    paused = True
                    pause_start = ts

            else:

                if paused:

                    durations.append(
                        (ts - pause_start) / 1000.0
                    )   # us

                    paused = False
                    pause_start = None


        if paused:

            durations.append(
                (END_TIME - pause_start) / 1000.0
            )

    return durations

def plot_pause_duration_cdf():

    files = list(INPUT_FOLDER.glob("*.txt"))

    fig, ax = plt.subplots(figsize=(5.8, 3.8))

    for cc, substring in CC_NAMES.items():

        matching = [
            f for f in files
            if substring in f.name
        ]

        if not matching:
            continue

        data = np.array(
            compute_pause_durations(matching[0])
        )

        if len(data) == 0:
            continue

        data.sort()

        y = np.arange(1, len(data)+1) / len(data)

        ax.plot(
            data,
            y,
            color=CC_COLORS[cc],
            linewidth=2,
            label=cc
        )

    ax.set_xlabel("Single PFC pause duration (µs)")
    ax.set_ylabel("CDF")

    ax.set_xlim(left=0, right=200)
    ax.set_ylim(0, 1)

    ax.set_yticks(np.linspace(0, 1, 6))

    ax.legend()

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _stile_assi(ax)

    plt.tight_layout()

    plt.savefig(
        OUTPUT_FOLDER /
        "pfc_pause_duration_cdf.png",
        dpi=300
    )

    plt.close(fig)

def compute_pause_duration_statistics(filename):
    """
    Calcola media e deviazione standard della durata
    dei singoli eventi di PFC pause.

    Ritorna:
        (mean_us, std_us)
    """

    durations = np.asarray(
        compute_pause_durations(filename),
        dtype=float
    )

    if len(durations) == 0:
        return 0.0, 0.0

    return (
        float(np.mean(durations)),
        float(np.std(durations))
    )


def plot_pause_duration_statistics():

    files = list(INPUT_FOLDER.glob("*.txt"))

    means = {}
    stds = {}

    for cc, substring in CC_NAMES.items():

        matching_files = [
            f for f in files
            if substring in f.name
        ]

        if len(matching_files) == 0:
            means[cc] = 0
            stds[cc] = 0
            continue

        mean, std = compute_pause_duration_statistics(
            matching_files[0]
        )

        means[cc] = mean
        stds[cc] = std


    labels = list(CC_NAMES.keys())

    x = np.arange(len(labels))

    width = 0.35

    fig, ax1 = plt.subplots(
        figsize=(7.2, 3.8)
    )

    ax2 = ax1.twinx()


    bars1 = ax1.bar(
        x - width/2,
        [means[c] for c in labels],
        width,
        color=colors[0],
        label="Mean"
    )

    bars2 = ax2.bar(
        x + width / 2,
        [stds[c] for c in labels],
        width,
        color=colors[1],
        label="Standard deviation"
    )


    for b in bars1:

        h = b.get_height()

        ax1.text(
            b.get_x() + b.get_width()/2,
            h,
            f"{h:.1f}",
            ha="center",
            va="bottom",
            fontsize=8
        )


    for b in bars2:

        h = b.get_height()

        ax2.text(
            b.get_x() + b.get_width()/2,
            h,
            f"{h:.0f}",
            ha="center",
            va="bottom",
            fontsize=8
        )


    ax1.set_xticks(x)

    ax1.set_xticklabels(
        labels,
        rotation=35,
        ha="right"
    )

    ax1.set_ylabel(
        "Mean pause duration (µs)"
    )

    ax2.set_ylabel(
        "Pause duration standard deviation (µs)"
    )

    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)

    _stile_assi(ax1)
    _stile_assi(ax2)

    lines = [
        plt.Rectangle((0, 0), 1, 1, color=colors[0]),
        plt.Rectangle((0, 0), 1, 1, color=colors[1]),
    ]

    ax1.legend(
        lines,
        [
            "Mean",
            "Standard deviation"
        ],
        loc="upper left"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_FOLDER / "pfc_pause_duration_statistics.png",
        dpi=300
    )

    plt.close(fig)

def plot_pfc_pause_events_and_total_time():

    files = list(INPUT_FOLDER.glob("*.txt"))

    pause_counts = {}
    total_pause_times = {}

    for cc, substring in CC_NAMES.items():

        matching_files = [
            f for f in files
            if substring in f.name
        ]

        if len(matching_files) == 0:

            pause_counts[cc] = 0
            total_pause_times[cc] = 0
            continue

        pauses, _ = compute_pfc_statistics(
            matching_files[0]
        )

        pause_counts[cc] = pauses

        total_pause_times[cc] = (
            compute_total_pause_time(
                matching_files[0],
                switches_only=True
            ) / 1_000_000.0      # ns -> ms
        )


    labels = list(CC_NAMES.keys())

    x = np.arange(len(labels))

    width = 0.35

    fig, ax1 = plt.subplots(
        figsize=(7.2, 3.8)
    )

    ax2 = ax1.twinx()


    bars1 = ax1.bar(
        x - width/2,
        [pause_counts[c]/1000 for c in labels],
        width,
        color=colors[0],
        label="1K PFC pause events"
    )

    bars2 = ax2.bar(
        x + width/2,
        [total_pause_times[c] for c in labels],
        width,
        color=colors[1],
        label="Total pause time"
    )


    for bar in bars1:

        h = bar.get_height()

        ax1.text(
            bar.get_x() + bar.get_width()/2,
            h,
            f"{int(h)}",
            ha="center",
            va="bottom",
            fontsize=8
        )


    for bar in bars2:

        h = bar.get_height()

        ax2.text(
            bar.get_x() + bar.get_width()/2,
            h,
            f"{h:.1f}",
            ha="center",
            va="bottom",
            fontsize=8
        )


    ax1.set_xticks(x)

    ax1.set_xticklabels(
        labels,
        rotation=35,
        ha="right"
    )

    ax1.set_ylabel(
        "1K Number of PFC pause events"
    )

    ax2.set_ylabel(
        "Total PFC pause time (ms)"
    )

    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)

    _stile_assi(ax1)
    _stile_assi(ax2)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left"
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_FOLDER /
        "pfc_pause_events_and_total_time.png",
        dpi=300
    )

    plt.close(fig)

if __name__ == "__main__":
    plot_pfc_pause_distribution()
    plot_pfc_statistics()
    plot_total_pause_time()
    plot_pause_duration_cdf()
    plot_pause_duration_statistics()
    plot_pfc_pause_events_and_total_time()