#!/usr/bin/env python3
"""
Analizza trace ns-3 per calcolare throughput e latenza per flow
Trace format: tempo n:node intf:qidx qidx qlen ecn:sip dip sport dport prot seq ts pg size(payload)
"""
import shutil
from pathlib import Path
from collections import defaultdict
import argparse

import plt

FILE_NAME = "mix_incast_incastflow3_hr95ai50-2.tr"
INPUT_FOLDER_ROOT = "data\\input\\"+FILE_NAME+".txt"
OUTPUT_FOLDER = "data\\output\\"+FILE_NAME+"\\"

OUTPUT_INTERVAL = 1500
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
    return f"{trace.intf}:{trace.qidx}"

def calcola_throughput_e_queues_lengths(nome_file):
    """Legge il file e crea un oggetto Trace per ogni riga"""

    flows = {}
    queues = {}
    with open(nome_file, 'r', encoding='utf-8') as file:
        for linea in file:
            linea = linea.strip()
            if linea:
                tr = Trace(linea)
                flow_id = identifica_flow_id(tr)
                queue_id = identifica_queue_id(tr)
                if tr.type == "ACK" and tr.event_kind == "Enqu":
                    flow_id = reverse_identifica_flow_id(tr)
                    if (tr.dip+":"+tr.dp) == flows[flow_id]["source"]:
                        if flows[flow_id]["last acknowledged"] >= tr.seq:
                            continue
                        sum = 0

                        keys_to_remove = []
                        for data in flows[flow_id]["data received"].keys():
                            if int(data) >= flows[flow_id]["last acknowledged"] and int(data) < tr.seq:
                                sum += flows[flow_id]["data received"][data]
                                keys_to_remove.append(data)

                        for k in keys_to_remove:
                            del flows[flow_id]["data received"][k]

                        flows[flow_id]["last acknowledged"] = tr.seq
                        value = sum / (tr.time - flows[flow_id]["last time acknowledged"])
                        flows[flow_id]["throughput"][str(tr.time)] = value
                        flows[flow_id]["last time acknowledged"] = tr.time

                elif tr.type == "DATA":
                    if not flow_id in flows:
                        flows[flow_id] = {
                            "throughput": {},
                            "data received": {},
                            "last acknowledged": 0,
                            "last time acknowledged": tr.time,
                            "source": tr.sip+":"+tr.sp
                        }
                    flows[flow_id]["data received"][str(tr.seq)] = tr.size

                if not queue_id in queues:
                    queues[queue_id] = {
                        "lengths": {},
                    }

                queues[queue_id]["lengths"][str(tr.time)] = tr.qlen


    return flows, queues


def identifica_flow_id(trace):
    return f"{trace.sip}:{trace.sp}->{trace.dip}:{trace.dp}"


def reverse_identifica_flow_id(trace):
    return f"{trace.dip}:{trace.dp}->{trace.sip}:{trace.sp}"

import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.rcParams.update({
    'figure.figsize': (7.0, 3.0),
    'figure.dpi': 150,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
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

def grafica_throughput_aggregato(aggregate_throughput):
    tempi = [elem["time"] for elem in aggregate_throughput]
    throughput = [elem["value"] for elem in aggregate_throughput]

    fig, ax = plt.subplots(figsize=(7.0, 3.0), dpi=150)
    ax.plot(tempi, throughput, color='#5DADE2', linewidth=1.8, label='HPCC')

    ax.set_xlabel('Time (us)')
    ax.set_ylabel('Throughput (Gbps)')
    ax.set_title('Throughput vs Time')

    _stile_assi(ax)
    ax.legend(loc='center left', bbox_to_anchor=(0.53, 0.58), frameon=False)

    fig.tight_layout()
    plt.savefig(OUTPUT_FOLDER + 'throughput_aggregato.png', dpi=150, bbox_inches='tight')
    plt.show()
    plt.close(fig)

def grafica_qlen_aggregato(aggregate_qlen):
    tempi = [elem["time"] for elem in aggregate_qlen]
    qlen = [elem["value"] for elem in aggregate_qlen]

    fig, ax = plt.subplots(figsize=(7.0, 3.0), dpi=150)
    ax.plot(tempi, qlen, color='#5DADE2', linewidth=1.8, label='HPCC')

    ax.set_xlabel('Time (us)')
    ax.set_ylabel('Queue length (KBytes)')
    ax.set_title('Queue length vs Time')

    _stile_assi(ax)
    ax.legend(loc='center left', bbox_to_anchor=(0.53, 0.58), frameon=False)

    fig.tight_layout()
    plt.savefig(OUTPUT_FOLDER + 'qlen_aggregato.png', dpi=150, bbox_inches='tight')
    plt.show()
    plt.close(fig)

# Nuova funzione per graficare il throughput di tutti i flow (N curve)
def grafica_throughput_per_flow(flows, start_t, end_t):
    """Crea un grafico 2D del throughput per ogni flow in funzione del tempo (N curve)"""

    # Calcolare i throughput per ogni flow sugli stessi intervalli di tempo usati per l'aggregato
    last_indexes = {}
    for f in flows:
        last_indexes[f] = {"x": 0}

    # Preparare i dati per ogni flow: dictionary {flow_id: [{"time": ..., "value": ...}, ...]}
    throughput_per_flow = {}
    for f in flows:
        throughput_per_flow[f] = []

    for t in range(start_t, end_t, 500):
        for f in flows:
            app_last_index_x = last_indexes[f]["x"]

            for i in range(last_indexes[f]["x"], len(flows[f]["throughput"])):
                if flows[f]["throughput"][i]["time"] <= t:
                    last_elem_X = flows[f]["throughput"][i]
                else:
                    app_last_index_x = i
                    break

            last_indexes[f] = {"x": app_last_index_x}
            if t > flows[f]["throughput"][-1]["time"]:
                value = 0
            else:
                value = last_elem_X["value"] * 8

            throughput_per_flow[f].append({
                "time": (t - start_t) / 1000,
                "value": value
            })

    # Creare il grafico
    plt.figure(figsize=(12, 6))

    # Disegnare una curva per ogni flow
    colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'orange', 'purple', 'brown']
    for idx, f in enumerate(throughput_per_flow):
        tempi = [elem["time"] for elem in throughput_per_flow[f]]
        throughput = [elem["value"] for elem in throughput_per_flow[f]]

        color = colors[idx % len(colors)]
        plt.plot(tempi, throughput, color=color, linewidth=2, label=f)

    # Titoli e label
    plt.xlabel('Tempo (us)', fontsize=12)
    plt.ylabel('Throughput (Gbps)', fontsize=12)
    plt.title('Throughput per Flow in Funzione del Tempo', fontsize=14)

    # Grid e legenda
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', fontsize=8)

    # Formattare l'asse x per numeri grandi
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(fontsize=10)

    # Salva il grafico
    plt.tight_layout()
    plt.savefig(OUTPUT_FOLDER+'throughput_per_flow.png', dpi=150, bbox_inches='tight')
    print("\nGrafico salvato in: throughput_per_flow.png")

    # Mostra il grafico (opzionale, utile in ambiente interactivo)
    plt.show()


# Esempio di utilizzo
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analizza trace ns-3 per throughput e latenza')
    parser.add_argument('-f', '--file', dest='file', default=INPUT_FOLDER_ROOT,
                        help='File di trace da analizzare')
    args = parser.parse_args()

    input_path = (Path(__file__).parent.resolve() / Path(args.file)).resolve()
    print(f"Leggendo trace da: {input_path}")

    flows, queues = calcola_throughput_e_queues_lengths(input_path)
    print(flows.keys())
    print(queues.keys())
    cartella = Path(OUTPUT_FOLDER)
    if cartella.exists():
        shutil.rmtree(cartella)  # La ricrea vuota cartella.mkdir(parents=True)
    cartella.mkdir(parents=True)

    aggregate_throughput = []
    aggregate_queue = []
    start_t = 2000000000
    end_t = 2000400000
    for t in range(start_t, end_t, OUTPUT_INTERVAL):
        sum = 0
        for f in flows:
            found = False
            elem = 0
            app_t = t
            cont = 0
            while app_t > (t-OUTPUT_INTERVAL):
                if str(app_t) in flows[f]["throughput"]:
                    found = True
                    elem += flows[f]["throughput"][str(app_t)]
                    cont +=1
                app_t -= 1

            if cont == 0:
                elem = 0
            else:
                elem = elem/cont

            sum += elem

        if (sum*8 > 100):
            sum = 100/8
        aggregate_throughput.append({
            "time": (t - start_t) / 1000,
            "value": sum * 8
        })


    for t in range(start_t, end_t, OUTPUT_INTERVAL):
        sum = 0
        for f in queues:
            found = False
            elem = 0
            app_t = t
            cont = 0
            while not found and app_t > (t - OUTPUT_INTERVAL):
                if str(app_t) in queues[f]["lengths"]:
                    found = True
                    elem += queues[f]["lengths"][str(app_t)]
                    cont += 1
                app_t -= 1

            if cont == 0:
                elem = 0
            else:
                elem = elem/cont

            sum += elem


        aggregate_queue.append({
            "time": (t - start_t) / 1000,
            "value": sum / 1000
        })

    grafica_throughput_aggregato(aggregate_throughput)
    grafica_qlen_aggregato(aggregate_queue)