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

FILE_NAME = "mix_incast_incastflow_hp95ai300.tr"
INPUT_FOLDER_ROOT = "data\\input\\"+FILE_NAME+".txt"
OUTPUT_FOLDER = "data\\output\\"+FILE_NAME+"\\"

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
                self.protocol = self.elementi[4]
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
                self.protocol = self.elementi[4]
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
                if tr.type == "ACK" and tr.protocol == "Recv":
                    flow_id = reverse_identifica_flow_id(tr)
                    if (tr.dip+":"+tr.dp) == flows[flow_id]["source"]:
                        if flows[flow_id]["last acknowledged"] >= tr.seq:
                            continue
                        sum = 0

                        keys_to_remove = []
                        for data in flows[flow_id]["data received"]:
                            if int(data) >= flows[flow_id]["last acknowledged"] and int(data) < tr.seq:
                                sum += flows[flow_id]["data received"][data]
                                keys_to_remove.append(data)

                        for k in keys_to_remove:
                            del flows[flow_id]["data received"][k]

                        flows[flow_id]["last acknowledged"] = tr.seq
                        value = sum / (tr.time - flows[flow_id]["throughput"][-1]["time"])
                        flows[flow_id]["throughput"].append({
                            "time": tr.time,
                            "value": value
                        })

                elif tr.type == "DATA":
                    if not flow_id in flows:
                        flows[flow_id] = {
                            "throughput": [{"time": 2000000000, "value": 0}],
                            "data received": {},
                            "last acknowledged": 0,
                            "source": tr.sip+":"+tr.sp
                        }
                    flows[flow_id]["data received"][str(tr.seq)] = tr.size

                if not queue_id in queues:
                    queues[queue_id] = {
                        "lengths": [{"time": 2000000000, "value": 0}],
                    }

                queues[queue_id]["lengths"].append({"time": tr.time, "value": tr.qlen})


    return flows, queues


def identifica_flow_id(trace):
    return f"{trace.sip}:{trace.sp}->{trace.dip}:{trace.dp}"


def reverse_identifica_flow_id(trace):
    return f"{trace.dip}:{trace.dp}->{trace.sip}:{trace.sp}"


def grafica_throughput_aggregato(aggregate_throughput):
    """Crea un grafico 2D del throughput aggregato in funzione del tempo (1 sola curva)"""

    # Extraere tempi e valori
    tempi = [elem["time"] for elem in aggregate_throughput]
    throughput = [elem["value"] for elem in aggregate_throughput]

    # Creare il grafico
    plt.figure(figsize=(12, 6))
    plt.plot(tempi, throughput, 'b-', linewidth=2, label='Throughput Aggregato')

    # Titoli e label
    plt.xlabel('Tempo (us)', fontsize=12)
    plt.ylabel('Throughput (Gbps)', fontsize=12)
    plt.title('Throughput Aggregato in Funzione del Tempo', fontsize=14)

    # Grid e legenda
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', fontsize=10)

    # Formattare l'asse x per numeri grandi
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(fontsize=10)

    # Salva il grafico
    plt.tight_layout()
    plt.savefig(OUTPUT_FOLDER+'throughput_aggregato.png', dpi=150, bbox_inches='tight')
    print("\nGrafico salvato in: throughput_aggregato.png")

    # Mostra il grafico (opzionale, utile in ambiente interactivo)
    plt.show()


def grafica_qlen_aggregato(aggregate_qlen):
    """Crea un grafico 2D del throughput aggregato in funzione del tempo (1 sola curva)"""

    # Extraere tempi e valori
    tempi = [elem["time"] for elem in aggregate_qlen]
    qlen = [elem["value"] for elem in aggregate_qlen]

    # Creare il grafico
    plt.figure(figsize=(12, 6))
    plt.plot(tempi, qlen, 'b-', linewidth=2, label='Qlen Aggregate')

    # Titoli e label
    plt.xlabel('Tempo (us)', fontsize=12)
    plt.ylabel('Qlen (KBytes)', fontsize=12)
    plt.title('Qlen Aggregate in Funzione del Tempo', fontsize=14)

    # Grid e legenda
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', fontsize=10)

    # Formattare l'asse x per numeri grandi
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(fontsize=10)

    # Salva il grafico
    plt.tight_layout()
    plt.savefig(OUTPUT_FOLDER+'qlen_aggregato.png', dpi=150, bbox_inches='tight')
    print("\nGrafico salvato in: qlen_aggregato.png")

    # Mostra il grafico (opzionale, utile in ambiente interactivo)
    plt.show()


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
    # Nuova chiamata: grafico throughput per ogni flow (N curve)
    start_t = 2000000000
    end_t = 2001000000
    grafica_throughput_per_flow(flows, start_t, end_t)

    aggregate_throughput = []
    aggregate_queue = []

    last_indexes_f = {}
    last_indexes_q = {}
    for f in flows:
        last_indexes_f[f] = 0
    for q in queues:
        last_indexes_q[q] = 0

    start_t = 2000000000
    end_t = 2000400000
    for t in range(start_t, end_t, 7000):
        sum = 0
        for f in flows:
            app_last_index_x = last_indexes_f[f]
            for i in range(last_indexes_f[f], len(flows[f]["throughput"])):
                if flows[f]["throughput"][i]["time"] <= t:
                    last_elem_X = flows[f]["throughput"][i]
                else:
                    app_last_index_x = i
                    break
            if t > flows[f]["throughput"][-1]["time"]:
                last_elem_X = {"time": t, "value": 0}

            last_indexes_f[f] = app_last_index_x
            sum += last_elem_X["value"]

        if (sum * 8 > 100):
            sum = 100/8
        aggregate_throughput.append({
            "time": (t - start_t) / 1000,
            "value": sum * 8
        })


    for t in range(start_t, end_t, 7000):
        sum = 0
        for q in queues:
            app_last_index_x = last_indexes_q[q]
            for i in range(last_indexes_q[q], len(queues[q]["lengths"])):
                if queues[q]["lengths"][i]["time"] <= t:
                    last_elem_Q = queues[q]["lengths"][i]
                else:
                    app_last_index_x = i
                    break


            last_indexes_q[q] = app_last_index_x

            sum = max(sum, last_elem_Q["value"])

        aggregate_queue.append({
            "time": (t - start_t) / 1000,
            "value": sum / 1000
        })

    grafica_throughput_aggregato(aggregate_throughput)
    grafica_qlen_aggregato(aggregate_queue)