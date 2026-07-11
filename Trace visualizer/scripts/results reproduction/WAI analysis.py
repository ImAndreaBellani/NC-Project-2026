#!/usr/bin/env python3
"""
Analizza trace ns-3 per calcolare throughput e latenza per flow
Trace format: tempo n:node intf:qidx qidx qlen ecn:sip dip sport dport prot seq ts pg size(payload)
"""
import os
import shutil
from pathlib import Path
import matplotlib as mpl
import numpy as np
import matplotlib.pyplot as plt

START_TIME = 2000000000

OUTPUT_INTERVAL = 150000

RTT = 4

def from_rate_to_window(rate):
    return int((rate*RTT)/8)

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

def _stile_assi(ax):
    ax.tick_params(axis='both', which='major', labelsize=11, width=1.0, length=4, direction='in')
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)

class Trace:
    def __init__(self, linea):
        self.elementi = linea.split(" ")
        self._parse()  # ← Chiamare _parse() qui

    def _parse(self):
        match self.elementi[10]:
            case "U" | "T":
                self.type = "DATA"
                self.time = int(self.elementi[0])
                self.node = int(self.elementi[1].split(":")[1])
                self.intf = int(self.elementi[2].split(":")[0])
                self.qidx = int(self.elementi[2].split(":")[1])
                self.qlen = int(self.elementi[3])
                self.event_kind = self.elementi[4]
                self.ecn = int(self.elementi[5].split(":")[1]) == 1
                self.sip = self.elementi[6]
                self.dip = self.elementi[7]
                self.sp = self.elementi[8]
                self.dp = self.elementi[9]
                self.seq = int(self.elementi[11])
                self.size = int(self.elementi[14].split("(")[0])
            case "A":
                self.type = "ACK"
                self.time = int(self.elementi[0])
                self.node = int(self.elementi[1].split(":")[1])
                self.intf = int(self.elementi[2].split(":")[0])
                self.qidx = int(self.elementi[2].split(":")[1])
                self.qlen = int(self.elementi[3])
                self.event_kind = self.elementi[4]
                self.ecn = int(self.elementi[5].split(":")[1]) == 1
                self.sip = self.elementi[6]
                self.dip = self.elementi[7]
                self.sp = self.elementi[8]
                self.dp = self.elementi[9]
                self.seq = int(self.elementi[13])
            case _:
                print("Not interested")  # Default case

def identifica_queue_id(trace):
    return f"{trace.node}:{trace.intf}:{trace.qidx}"

def identifica_flow_id(trace):
    return f"{trace.sip}:{trace.sp}->{trace.dip}:{trace.dp}"


def reverse_identifica_flow_id(trace):
    return f"{trace.dip}:{trace.dp}->{trace.sip}:{trace.sp}"




def calcola_throughput_e_queues_lengths(nome_file):
    """Legge il file e crea un oggetto Trace per ogni riga"""

    flows = {}
    queues = {}


    with open(nome_file, 'r', encoding='utf-8') as file:
        last_time = 2000000000
        data_received = 0
        #last_time_ever = 2004700000
        last_time_ever = 2050000000
        last_time_seen = last_time
        next_time = last_time + 10000
        start = 0
        for linea in file:
            linea = linea.strip()
            if linea:
                tr = Trace(linea)
               # if tr.qlen > 0:
                last_time_seen = tr.time#-3450000*(window_size == 300)

                if tr.time > last_time_ever:
                    continue

                flow_id = identifica_flow_id(tr)
                if tr.type == "DATA" and tr.event_kind == "Recv" and tr.node == flows[flow_id]["destination node"]:
                    flows[flow_id]["data"] += tr.size
                    data_received += tr.size

                elif tr.type == "DATA":
                    if not flow_id in flows:
                        flows[flow_id] = {
                            "throughput": {},
                            "destination node": 1,
                            "data": 0
                        }
                        if len(flows.keys()) == 16:
                            next_time = tr.time+10000

                if tr.time >= next_time and (tr.time != last_time) and len(flows.keys()) == 16:
                    data_received = 0
                    for f in flows.keys():
                        flows[f]["throughput"][str(tr.time)] = flows[f]["data"]/(tr.time-last_time)
                        flows[f]["data"] = 0

                    last_time = tr.time
                    next_time = tr.time+10000

                if start == 0 and identifica_queue_id(tr)=="0:1:3" and tr.time>2000050000:
                    start = tr.time

    next_times = {}
    step = 1000

    end = last_time_ever#last_time_seen
    with open(nome_file, 'r', encoding='utf-8') as file:
        for linea in file:
            linea = linea.strip()
            if linea:
                tr = Trace(linea)
                if tr.time < start:
                    continue

                queue_id = identifica_queue_id(tr)

                if not queue_id in queues:
                    queues[queue_id] = []

                queues[queue_id].append({"time": tr.time, "value": tr.qlen / 1000})


    new_queues = {k: [] for k in queues}

    for q in queues:
        events = queues[q]

        i = 0
        last_value = 0

        for t in range(start, end, step):
            # aggiorna fino al tempo t
            while i < len(events) and events[i]["time"] <= t:
                last_value = events[i]["value"]
                i += 1

            new_queues[q].append(last_value)

    return flows, new_queues

def plot_stacked_throughputs(throughputs, output_folder):
    """
    Disegna un grafico a barre stacked in cui ogni barra rappresenta
    un valore di WAI e ogni segmento il throughput medio di un flow.
    """

    fig, ax = plt.subplots(figsize=(4.2, 2.8))

    wai_values = sorted(throughputs.keys(), key=int)
    x = range(len(wai_values))

    bar_width = 0.58

    stack_heights = []

    for i, wai in enumerate(wai_values):
        bottom = 0.0

        # Ordina i throughput per avere un aspetto più regolare
        values = sorted(throughputs[wai])

        for j, value in enumerate(values):
            ax.bar(
                i,
                value,
                width=bar_width,
                bottom=bottom,
                color=colors[j % len(colors)],
                edgecolor="none",
            )
            bottom += value

        # altezza totale dello stack
        stack_heights.append(bottom)

    # linea che collega le altezze degli stack
    ax.plot(
        list(x),
        stack_heights,
        marker="o",
        markersize=3,
        linewidth=1,
        color="black",
        alpha=0.6,
        zorder=5,
    )

    # valori sopra ogni punto
    for i, height in enumerate(stack_heights):
        ax.text(
            i,
            height + 2,
            f"{height:.2f}",
            ha="center",
            va="bottom",
            fontsize=7,
            alpha=0.55,
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(wai_values)

    ax.set_xlabel(r"Different $W_{AI}$ (Bytes)")
    ax.set_ylabel("Throughput (Gbps)")

    ax.set_ylim(0, 100)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _stile_assi(ax)

    plt.tight_layout()
    plt.savefig(output_folder / "throughput_stacked.png", dpi=300)
    plt.close(fig)

def plot_throughput_evolution(flows, output_folder, label):
    """
    Per ogni flow mostra l’evoluzione temporale del throughput.
    """
    fig, ax = plt.subplots(figsize=(6.0, 3.0))

    for i, (flow_id, data) in enumerate(flows.items()):
        if not data["throughput"]:
            continue

        times = sorted(int(t) for t in data["throughput"].keys())
        values = [data["throughput"][str(t)] * 8 for t in times]  # stesso scaling usato altrove

        ax.plot(
            times,
            values,
            color=colors[i % len(colors)],
            linewidth=1.5,
            label=flow_id
        )

    ax.set_xlabel("Time")
    ax.set_ylabel("Throughput (Gbps)")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _stile_assi(ax)

    plt.tight_layout()

    #plt.savefig(output_folder / f"throughput_evolution_{label}.pdf")
    plt.savefig(output_folder / f"throughput_evolution_{label}.png", dpi=300)
    plt.close(fig)

def plot_queue_stats(queue_stats, output_folder):
    """
    queue_stats[wai] = (median, 95th, 99th)
    """

    fig, ax = plt.subplots(figsize=(4.2, 2.8))

    wai_values = sorted(queue_stats.keys(), key=int)
    x = np.arange(len(wai_values))

    med = [queue_stats[w][0] for w in wai_values]
    p95 = [queue_stats[w][1] for w in wai_values]
    p99 = [queue_stats[w][2] for w in wai_values]

    bar_w = 0.18

    ax.bar(x - 1.5 * bar_w, med, width=bar_w,
           color=colors[0], label="Median")
    ax.bar(x,               p95, width=bar_w,
           color=colors[1], label="95-pct")
    ax.bar(x + 1.5 * bar_w, p99, width=bar_w,
           color=colors[2], label="99-pct")

    ax.set_xticks(x)
    ax.set_xticklabels(wai_values)

    ax.set_xlabel(r"Different $W_{AI}$ (Bytes)")
    ax.set_ylabel("Queue length (KBytes)")
    ax.set_ylim(0, 16)
    ax.set_yticks(np.arange(0, 17, 2))  # 0,2,4,...,16

    # Lascia scegliere automaticamente il range se i valori cambiano
    # oppure decommenta la riga sotto se vuoi forzare l'asse.
    # ax.set_yticks(np.arange(0, 17, 2))

    ax.legend(
        loc="upper left",
        frameon=False,
        ncol=1,  # legenda verticale
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _stile_assi(ax)

    plt.tight_layout()

    #plt.savefig(output_folder / "queue_length_stats.pdf")
    plt.savefig(output_folder / "queue_length_stats.png", dpi=300)

    plt.close(fig)

def plot_queue_distribution(all_qLens, queue_id, cartella):

    fig, ax = plt.subplots(figsize=(4.6, 2.4))

    for i, wai in enumerate(sorted(all_qLens.keys(), key=int)):
        values = np.asarray(all_qLens[wai][queue_id])

        if len(values) == 0:
            continue

        x = np.sort(values)

        print(f"AI {wai} percentili (50,95,99):",
              np.percentile(x, [50, 95, 99]))

        # CDF empirica
        y = 100 * np.arange(1, len(x) + 1) / len(x)

        ax.plot(
            x,
            y,
            color=colors[i % len(colors)],
            linewidth=1.6,
            label=f"AI {wai}"
        )

    # Assi
    ax.set_xlabel("Queue Length (KBytes)")
    ax.set_ylabel("CDF (%)")

    ax.set_xlim(0,18)
    ax.set_ylim(0, 100)

    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_xticks([0, 2, 4, 6, 8, 10, 12, 14, 16, 18])

    # stile tipo paper
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(False)

    ax.legend(
        loc="lower right",
        frameon=False,
        handlelength=2.5,
        borderpad=0.2,
        labelspacing=0.2
    )

    safe = queue_id.replace(":", "_")

    plt.savefig(
        f"{cartella}/queue_cdf_{safe}.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

# Esempio di utilizzo
if __name__ == "__main__":
    all_flows = {}
    all_qLens = {}
    for i in range(1, 1000):
        FILE_NAME = "mix_incast_incastflow3_hp95ai"+str(i)+".tr"
        INPUT_FOLDER_ROOT = "data\\input\\" + FILE_NAME + ".txt"
        window_size = from_rate_to_window(i)

        if os.path.exists(INPUT_FOLDER_ROOT):
            input_path = (Path(__file__).parent.resolve() / Path(INPUT_FOLDER_ROOT)).resolve()
            print(f"Leggendo trace da: {input_path}")

            flows, queues = calcola_throughput_e_queues_lengths(input_path)
            all_flows[str(window_size)] = flows
            all_qLens[str(window_size)] = queues


    OUTPUT_FOLDER = "data\\output\\W_AI analysis\\"

    cartella = Path(OUTPUT_FOLDER)
    if cartella.exists():
        shutil.rmtree(cartella)  # La ricrea vuota cartella.mkdir(parents=True)

    cartella.mkdir(parents=True)

    throughputs = {}
    for k in all_flows:
        print("W_AI: " + str(k))
        throughputs[k] = []
        total_sum = 0
        avg_values = []

        for f in all_flows[k]:
            partial_sum = 0.0
            for t in all_flows[k][f]["throughput"].keys():
                partial_sum  += all_flows[k][f]["throughput"][t]*8

            avg = partial_sum  / len(all_flows[k][f]["throughput"])
            print("flow: " + str(f) + " average throughput: " + str(avg))
            avg_values.append(avg)

        total_sum = sum(avg_values)

       # if total_sum > 100:
        #    scale = 100.0 / total_sum
        #else:
        scale = 1.0

        throughputs[k] = [v * scale for v in avg_values]
        total_sum *= scale

        print("total sum: " + str(total_sum))
        # 🔽 nuova chiamata
        plot_throughput_evolution(all_flows[k], cartella, k)

    plot_stacked_throughputs(throughputs, cartella)


    queue_stats = {}

    QUEUE_ID = "0:1:3"  # oppure "3:1"

    for wai in sorted(all_qLens.keys(), key=int):
        values = all_qLens[wai][QUEUE_ID]
        values = np.sort(values)

        queue_stats[wai] = (
            np.percentile(values, 50, method="linear"),
            np.percentile(values, 95,  method="linear"),
            np.percentile(values, 99,  method="linear"),
        )

    plot_queue_stats(queue_stats, cartella)
    plot_queue_distribution(all_qLens, QUEUE_ID, cartella)