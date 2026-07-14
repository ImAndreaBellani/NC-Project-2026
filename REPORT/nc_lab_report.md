# Replicating: HPCC: High Precision Congestion Control

**Team Members:**  
Andrea Bellani ([andrea1.bellani@mail.polimi.it](mailto:andrea1.bellani@mail.polimi.it));

Andrea Migliorini ([andrea1.migliorini@mail.polimi.it](mailto:andrea1.migliorini@mail.polimi.it)).

---

**Source Paper:**

Y. Li, R. Miao, H. H. Liu, Y. Zhuang, F. Feng, L. Tang, Z. Cao, M. Zhang, F. Kelly, M. Alizadeh, M. Yu: HPCC: High Precision Congestion Control. In SIGCOMM '19, August 19–23, 2019, Beijing, China, © 2019 Association for Computing Machinery.

**Project:**
[link to our repository](https://github.com/ImAndreaBellani/NC-Project-2026)

---
<div class="pagebreak"></div>

# 1. Introduction

HPCC: High Precison Congestion Control presents a novel approach to Congestion Control for Datacenter networks. In particular, it is a window-based Congestion Control algorithm designed for high-speed RDMA (*Remote Direct Memory Access*) networks that leverages INT-MD (*In-band Network Telemetry - EMbed Data*) to get precise queue lenghts information.

In the paper, authors explain the motivation and theoretical foundations behind HPCC, its design and test its effectiveness with both testbed and NS-3 simulations, comparing it with state-of-art other Congestion Control algorithms for Datacenter Networks.

## 1.1. HPCC main contributions
The main contribution of the paper is the leverage of INT to improve the Congestion Control on large-scale and high-speed networks. The paper present a detailed description of the in-production Congestion Control mechanism running in the Alibaba Group datacenters, which can provide insights for the design of new CC (Congestion Control) mechanisms that leverage INT (which had not been  leveraged by other state-of-art CC mechanisms yet).

Moreover, the paper also shares Alibaba production experiences on the difficulties to operate on RDMA networks with the state-of-art CC mechanisms and clarifies the challenges of designing a Congestion Control algorithm for RDMA networks. 


## 1.2. Challenges in achieving High Precision Congestion Control for RDMA applications

### 1.2.1. RDMA networks in Datacencter

The demand of high-speed Datacenter networks is driven by two main trends, according to both state-of-art and authors experience:
- new *resource disaggregation* and *heterogeneous computing* architectures require both low network latency levels and high network bandwidth;
- new applications (eg. large-scale ML training on high computation speed devices) that periodically trasfer large volume data with super-fast storage and computation speeds, often making the network the real performance bottleneck.

To sustain these requirements, new approaches started to offload network stacks into hardware. Authors, in particular, started to deploy large-scale networks with RDMA over *RoCEv2* (RDMA over Converged Ethernet Version 2).

### 1.2.2. Why design a new Congestion Control algorithm

HPCC tries to cope with the foundamental challenges authors have experienced with RoCEv2 and overcome limitations of other state-of-art Congestion Control mechanism.

Authors highlight that in RDMA networks:
- many flows starting at line rate, if not properly controlled, will cause severe congestions and deep packet queueing;
- congestions lead switches to trigger PFC pauses, which cause huge traffic drops;
- short flows can experience sudden peaks in latency due to deep packet queueing.

To tame the problems mentioned above, an adequate Congestion Control mechanism is essential however, state-of-art CC algorithms (such as DCQCN and TIMELY) face important limitations, such as:
- slow convergence of iterative methods that leverage coarse-grained feedback signals (eg. ECN);
- techniques inherently based on mechanisms that wait queues build-ups (eg. ECN marking or detecting RTT increasing) to adjust sender rates;
- complicated parameter tuning due to an high number of parameters or laking of simple rules of thumb to set them.

Authors highlight how these limitation are a consequence of the heuristics implented to adjust sender rates accordingly to a estimated network utilization. Instead, HPCC overcomes these limitations leveraging INT, which enables senders to continuosly and precisely compute network utilization in order to quickly adjust their windows to the current network load.

## 1.3. How HPCC works


<center>
  <img
    alt="HPCC leveraging INT-MD"
    src="figures/HPCC - Figure 4.jpg"
    style="width:70%;"
  />
  <p><b>Figure 1: The overview of HPCC framework</b></p>
</center>

The main keypoint of HPCC is the usage of INT-MD (*In-band Network Telemetry - EMbed Data*) to obtain precise link loads in particular, each switch in the path enqueues an INT header that contains various information which sender can use to proactively adjust its sending rate (eg. Queue Length). Instead of relying on heuristics or iterative approaches, senders receive per-ACK updates to rapidly adjust the sending window, with a minimal set of parameters.

When a new ACK arrives, the sender computes the current network utilization $U$ using information retrived from the INT headers collected over the flow path and updates its window. In particular, we can distinguish two different phases in the HPCC algorithm (the following terminology is introduced for clarity):
- *agnostic phase* : the sender increases its window regardless of network utilization $U$, while still calculating it;
- *adaptive phase* : the sender adapts its window adjusting it by a factor $\frac{\eta}{U}$ (note that if $U<\eta$ the window increases, which is fine since the network is not congested).

Senders normally start in the agnostic phase and pass to the adaptive one after a certain number of RTTs or if $U\geq\eta$.

Instead of directly updating sending window starting from the previous value, sender always adjusts its window from what we can call a *reference window* $W^C$ that is updated nearly every-RTT; to be more precise, it is updated only when the ACK of the first packet sent after the last $W^C$ update is received. This technique is implemented to ensure what authors call *fast reaction without overreaction*. In other words, it is essential that the sender quickly reacts to changes (so, every-ACK received), but adjusting its window completely every ACK received would make the sender overreact since ACKs interleaved less than an RTT present almost the same information. So, the window adjustment is performed per-ACK starting from a reference window ($W^C$) that is only updated every-RTT.

Note that HPCC requires just $3$ parameters to be configured, which purpose is quite orthogonal and straight-forward:
<center>
  <table>
    <tr>
      <th>Parameter</th><th>Meaning</th><th>How to set it</th>
    </tr>
    <tr>
      <th>$\eta$</th>
      <td>Network utilization threshold that triggers the adaptive phase</td>
      <td>Close to $1$, depening on how much utilization headroom is desired. Lower values increase network stability while higher values will increase network utilization.</td>
    </tr>
    <tr>
      <th>$W_{AI}$</th>
      <td>Additive Increase window to ensure fairness</td>
      <td>A simple rule of thumb is $W_{AI} = \frac{W_{init}\times(1-\eta)}{N}$, where $N$ is the (maximum) number of expected concurrent flows on a single link</td>
    </tr>
    <tr>
      <th>$maxStage$</th>
      <td>Number of maximum stages before passing to the adaptive phase</td>
      <td>It controls the tradeoff between steady state stability and the speed to reclaim free bandwidth. Authors found that $maxStage = 5$ provides a good balance.</td>
    </tr>
  </table>
</center>



<div class="pagebreak"></div>

# 2. Selected Result
## 2.1. Fairness and queue size with $W_{AI}$

 Properly understanding how to tune $W_{AI}$ is important to ensure fairness while maximizing the aggregated throughput. Authors then provide a simple rule-of-thumb to set it: $W_{AI} = \frac{W_{init}\times(1-\eta)}{N}$, where $N$ is the (maximum) number of expected concurrent flows on a single link.

Authors investigate the effect of different choices of $W_{AI}$ by simulating a 16 to 1 incast within a single rack.
Therefore, for a 16 to 1 solo-incast, considering $\eta = 0.95$ and $W_{init} = 100 Gbps \times 4\mu s = 50 KB$ leads to $W_{AI} \approx 156 B$. As a consequence, we expect that different $W_{AI}$ settings affect negatively algorithm performances.

<center>
  <img
    alt="Considering an incast of 16 flows, Figure 14a shows the average throughput for different W_AI values, Figure 14b shows length's percentiles of the incast Queue"
    src="figures/HPCC - Figure 14.jpg"
    style="width:70%;"
    />
  <p><b>Figure 2: Fairness and queue lengths with $W_{AI}$ considering a 16 to 1 incast analyzed in the first $10\ ms$</b></p>
</center>

We see from Figure 2 that:
- a $W_{AI}$ set to a value really lower than the one suggested by the rule of thumb leads to a noticeble imbalance among flows throughputs, which we can see as an "unfair" behavior since it gives more bandwidth to some flows and a lower aggregated average throughput;
- a $W_{AI}$ set to a value really higher than the one suggested does not impact fairness but introduces higher tail-queue lengths and a slightly lower aggregated average throughput, which is less desirable.

In conclusion, since a less complicated set of parameters to tune is one of the challenges of CC algorithms that HPCC tried to tame, from these results we can say that the simple rule of thumb identifies a good trade-off between queue lengths and fairness.


## 2.2. Comparison of HPCC with other state-of-art CC algorithms (NS-3 simulations)
<center>
  <img
    alt="Considering an incast of 16 flows, Figure 14a shows the average throughput for different W_AI values, Figure 14b shows length's percentiles of the incast Queue"
    src="figures/HPCC - Figure 11.jpg"
    style="width:100%;"
    />
  <p><b>Figure 3: FCT (<i>Flow Completion Time</i>) slow down at 95-percentile, PFC and latency with FB_Hadoop (30% avg.load + 60-to-1 incast and 50% avg.load)</b></p>
</center>

In order to properly understand how HPCC behaves compared to other CC algorithms the authors decide to simulate the behaviour of various other CC algorithms used in RDMA plotting them based on flow completion time, latency and PFC pauses using widely accepted and publicly available data center traffic traces (in this case, FB_Hadoop).
The graphs show that even in the case of sudden incast events HPCC still didnt trigger any PFC pauses.
This clearly illustrates how much faster HPCC completes smaller flows than the other algorithms, and lower tail-latency compared to the others. Thus, accomplishing the stated goals of preventing PFC pauses and lowering the latency of packets.


<!--
## 2.3. Different ways of reacting to ACK.
<center>
  <img
    alt="Considering an incast of 16 flows, Figure 14a shows the average throughput for different W_AI values, Figure 14b shows length's percentiles of the incast Queue"
    src="figures/HPCC - Figure 13.jpg"
    style="width:90%;"
    />
  <p>Considering an incast of 16 flows, Figure 13a and Figure 13b shows respectively the aggregated throughput and Queue Length running HPCC with different reacting policies</p>
</center>
-->

# 3. Environment Setup
## 3.1. Hardware Environment
We ran the ns3 simulations and plot generations on a custom-built workstation with the followings HW specifications:
<center>

| Component | Specification |
|-----------|--------------|
| **CPU** | AMD Ryzen 5 7600X 6 core/12 threads at 5.4GHz |
| **Memory** | 32  GB DDR 5  4800 MHz |
| **Storage** | 1  TB NVMe SSD| 

</center>

## 3.2. Software Environment
<center>

| Component | Specification |
|-----------|--------------|
| **OS** | WSL Ubuntu|
| **Kernel version** | v24.04 |
| **NS-3 Compiler** | GCC v4.8 |
| **Python (NS-3 scripts)**  | v2.7.18 |
| **Python (performance evaluation scripts)** | v3.12 |
| **NS-3 Version** | v3.17 |
| **Paper artifact commit hash** | `9f4be2a9ead8a90e8bf732c66bd758c00e58e5be` |

</center>

## 3.3. Configuration Parameters
### 3.3.1. Network topology
We ran our experiments on two different topologies:
- for section 4.1. experiments we rebuilt the topology used in HPCC section 5.4.
- for sections 4.2. and 5. we used the fat-tree topology described in `simulation/mix/fat.txt` (which is also the one used in HPCC section 5.1)
### 3.3.2. Traffic generation
- for section 4.2 and 5.2 we generated the flows with a custom script `traffic_gen_incast.py` passing `-c <DISTRIBUTION_FILE> -n 320 -l <LOAD FRACTION> -b 100G -t 0.02` (which are, regardless of `-t`, coherent with the ones described in HPCC section 5.1.) while for flows with incasts passing `-c <DISTRIBUTION_FILE> -n 320 -l <LOAD FRACTION> -b 100G -t 0.02 -i 1 -p 2` (`-i 1` enables incast generation and `-p` details the incast percentage);
- for section 4.1 we have manually written the flows (see section 3.4.).
### 3.3.3. Simulation parameters
- we always ran the simulations with `run.py --cc <ccAlgorithm> --trace <Flow> --bw 100 --topo <Topology> --hpai <Rate_AI> --enable_tr 1` without any changes to the default algorithm configuration files.

## 3.4. Deviations from the Original Setup
We produced our experiments with no Software version differences according to the one described in the Paper artifact however, some deviations have been adopted for complexity or lack of information reasons.
### 3.4.1. Deviations for unavailable components or information

#### 3.4.1.1. Deviations in section 4.1. experiments


| Deviation | What is missing in the paper/artifact | What we chose |
|-----------|------------------------------|---------------|
| **16 to 1 incast flow file** | The file was not already  present in the artifact | We wrote it accordingly to the required format |
| **$W_{AI}$ convertion from bytes to rates** | Paper always states $W_{AI}$ as a Byte value (i.e. window size) but artifact always specifies it as a rate | We converted it according to `Rate_AI` $=\frac{W_{AI}}{RTT}\times 8$, $[RTT] = \mu s$|
| **Throughput and queue lengths evaluation**  |  Artifact did not include any script for evaluating queues lengths or throughput from L3 traces | We implemented a script to calculate them (see section 4.1.). 
| **Start time of the $W_{AI}$ fairness evaluation** | The paper does not specify any period before actually evaluating the experiment of figures 14a and 14b | We started to evaluate the traces after $20\ \mu s$ (i.e. $5\ RTT$s) |
| **End time of queue lenghts observation for $W_{AI}$ fairness evaluation** | The paper does not specify clearly the end time of the queue length analysis in figure 14b | We put it a $10\ ms + 5RTT$ |

#### 3.4.1.2. Deviations in section 4.2. experiments


| Deviation | What is missing in the paper/artifact | What we chose |
|-----------|------------------------------|---------------|
| **Generation of flows with random incast** | the paper establishes in 5.3 how they reproduced the incasts events but doesnt establish what does it mean by "network capacity" nor offers a program to create the flows | we created a new version of `traffic_gen.py`: `traffic_gen_incast.py`. This script uses a Poisson distribution based on the probability of a single server being the receiver of a incast event to generate these events.|
| **PFC pauses evaluation** | It is not stated how the fraction of pausing time is calculated (i.e. by summing the puasing time of each interface or calculating just the time fraction the simulation was affected by at least one pause) | We calculated both the number of pauses verified in the simulation and the overall time each interface has been paused |
| **Latency evaluation** | Artifact did not include any script for evaluating end-to-end latencies from L3 traces | We implemented a script to calculate them (see section 4.1.).


### 3.4.2. Deviations for complexity reasons
The length of the traffic ($0.1s$) simulated in the paper generated hundreds of GBs of traces, so we reduced the traces to ($0.02s$) this  reduced the size to around $50 GBs$ while still mantaining statistical significance.

# 4. Experiment Result
## 4.1. Fairness and queue size with $W_{AI}$ reproduction
In order to reproduce results shown in HPCC figures 14a and 14b we first gerated all L3 traces of an in-rack incast 16-to-1 for the four $W_{AI}$ values, then we plotted throughputs and queue length percentiles of the only queue that was affected by the incast (any other queue had always zero length). As mentioned in section 3.4.1.1., we calculated average throughputs and queue length's percentiles with an ad hoc script we implemented.

Considering the deviations mentioned in section 3.4.1.1. we analyzed both queue lengths and throughputs between  $20\ \mu s$ (i.e. $5\ RTT$s, for the topology considered) and $10.02\ ms$, since starting from $0\ \mu s$ lead us to 99-pcts (for $W_{AI}=5,25,150$ near $17 KB$) which we seen as consequences of the extremely high peak of in the queue lengths near the beginning of the simulation. Note that $20\ \mu s$ is the standard duration of the agnostic phase with $maxStage=5$ (as it is set by default).

Queue lengths are counted just by looking at the parameter in the L3 traces and instant throughput is calculated as $\frac{tr.size}{last\_time - tr.time}$ (where $last\_time$ is the time of the last throughput measurement for that flow, $tr.size$ is the packet size and $tr.time$ is the instant in which the packet was received by the destination node) each time a packet arrives to the destination node. Then, to estimate the average throughput of a flow from the collection of the instant measurements, we held each sample until the next one and sampled each collection every $1\ \mu s$ (as HPCC paper does for Queue Lengths).

<center>
  <img
    src="figures/W_AI analysis.jpg"
    style="width:100%;"
    />
  <p><b>Figure 4: our reproduction of HPCC figures 14a and 14b</b></p>
</center>

Although results are quite similar to the ones shown in section 2.1., some small differences need to be pointed out:
- from HPCC figure 14a, the $W_{AI}=5$ stack was a bit lower than the one for $W_{AI}=25$ however, the differences in fairness are still evident and other stacks heights are much more similar to the ones shown in the paper;
- 95-pct and 99-pct for $W_{AI}=300$ are slighty higher than the paper ones (from paper figures, nearly $1.5\ KB$ of difference).

To better validate the coherence of our results w.r.t. to the L3 traces we generated from NS-3, we also plotted flows throughputs evolutions and Queue Lengths CDFs:
<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/throughput_evolution_5.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/throughput_evolution_25.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/throughput_evolution_150.png"
      style="width:100%"
      />
  </div>
</center>
<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/throughput_evolution_300.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/queue_cdf_0_1_3.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 5: flows throughputs evolutions and Queue Length CDFs during the 16-to-1 incast</b></p>
</center>

## 4.2. Comparison of HPCC with other state-of-art CC algorithms (NS-3 simulations) reproduction

To reproduce figure $11$ from the paper we had to create a system capable of generating realistic incast events across servers of the topology. In the paper they establish it’s a $60$ to $1$ incast of $500\ \mathrm{kB}$, so an incast event is $60$ new flows of $500\ \mathrm{kB}$. We had to find out that in order to add a $2\%$ load incast to the experiment (as HPCC paper does) the bandwith the incasts had to occupy was $n_{\mathrm{servers}} \times \mathrm{NIC}_{\mathrm{bw}} \times 0.02$. 
We decided to use a Poisson distribution based on the expected number of incasts on a single server so that across $320$ servers on $100\ \mathrm{Gb}$ NICs and the $2\%$ load stated we expected to see $2667$ incast events, which corresponds to $\frac{320 \cdot \mathrm{NIC}_{\mathrm{bw}} \cdot 0.02}{60 \cdot 500\ \mathrm{KB}}$, validated experimentally by generating $10$ flows with this script.

Once the script was validated we generated performed $2$ simulations with the distribution $\mathrm{FB\_Hadoop}$ with the parameters generally established in section $3.3.2$: one with incast enabled and at $30\%$ load and one with incast disabled and $50\%$ load, as established in the paper as well.

We then simulated the behaviour of the CC algorithms represented in the paper; as this process is single core based this process will usually take hours on a homebuilt pc.

After completing the simulation we used the `fct_analysis.py` and the `trace_reader.cpp` to derive FCT slowdown percentiles.

The latency analysis was done by extracting the $5$ most common pair of servers in the first million lines and then evaluating their average latency between them across the entire trace. We experimented with picking $50$ random traces but it didn’t correspond well to the results in the paper, as well as not filtering L3 traces but running small simulations of $1\ ms$. Since no script was provided in the artifact to calculate the end-to-end latencies we implemented an ad hoc one. Simply, first traces are analyzed to detect which is the residence node of each server, then end-to-end is calculated as the time needed for the packet to traverse the network from the source node to the destination one.

With the PFC pauses instead we had to determine what the authors actually meant by fraction of PFC time, as no clear definition was given. So, in order to obtain still relevant results for the paper question (i.e. measuring the PFC impact running each CC algorithm) we plotted both the number of PFC pauses verified during the simulation and the total amount of time interfaces passed in pause (i.e. the sum over all interfaces of the total amount of time each has been in pause). NS-$3$ artifact implementation already provides the report of PFC pauses and resumes events by interfaces, so counting them and evaluating their duration was trivial. 

<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/fct_fbdhp_L30I2.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/LATENCY_fbhdp_30_incast/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/PFC_fbhdp_L30I2/pfc_pause_events_and_total_time.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 6: replication of FCT analysis, end-to-end latencies and PFC pauses for FB_Hadoop 30% avg.load + 60-to-1 incast</b></p>
</center>

<center>
  <div style="display:inline-block; width:49%;">
    <img
      src="figures/fct_fbdhp_L50.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:49%;">
    <img
      src="figures/LATENCY_fbhdp_50/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 7: replication of FCT analysis, end-to-end latencies and PFC pauses for FB_Hadoop 50% avg.load</b></p>
</center>

The FCT analysis result corresponded quite well to the results shown by the paper, despite the smaller sample size. As we can see HPCC out-performs all other algorithms on short flows (i.e. $<250\ KB$), which was the goal stated in the paper.

The end-to-end latency analysis still shows HPCC as the best performing algorithm and clearly shows how not window-based algoritms struggle in keeping low tail-latency levels, especially if incasts are present. However, latencies values are quite different from the ones shown in the paper, especially for algorithms that produce the highest values.

The PFC analys shows how PFC is triggered almost only in no window-based algorithms, with only TIMELY+win as an exception. PFC total pause time results are coherent with the PFC pause time fractions shown in the paper. It is worth noticing that we were able also to reproduce the near-zero pause time of TIMELY+win. No PFC plot was added for the no-incast experiment since no algorithm ever triggered PFC on any interface in that experiment.

# 5. Further Exploration

We decided to further investigate the behavior of HPCC (w.r.t. to the state-of-art ones) by simulating it with other RDMA workloads we found in the literature. We were particularly interested in verifying if the promising results with the paper distributions would have maintened across different workloads. In addition, differently from other algorithms (e.g. DCQCN) which would require a parameters tuning depending on the kind of workload selected, HPCC needs not.

<center>
  <div>
    <img
      src="figures/distCDFs.png"
      style="width:100%"
      />
  </div>
</center>
For each of the three chosen distributions, we performed an analysis analogue to the section 4.2. and additionally simulated the network under $50\%$ load with a $2\%$ load-equivalent incast events.

## 5.1. CC algorithms comparison with different distributions results

<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/alist_L30_I2_fct comp/95th_fct_slowdown.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/LATENCY_alist_30_incast/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/PFC_alist_L30I2/pfc_pause_events_and_total_time.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 9: FCT analysis, latencies and PFC with AliStorage for 30% avg.load + incast</b></p>
</center>

<center>
  <div style="display:inline-block; width:49%;">
    <img
      src="figures/alist_L50_T002_fct_comp/95th_fct_slowdown.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:49%;">
    <img
      src="figures/LATENCY_alist_50/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 10: FCT analysis, latencies and PFC with AliStorage for 50% avg.load</b></p>
</center>

<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/alist_L50_T0002_I2_FCT_comparison/95th_fct_slowdown.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/LATENCY_alist_50_incast/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/PFC_alist_L50I2/pfc_pause_events_and_total_time.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 11: FCT analysis, latencies and PFC with AliStorage for 50% avg.load + incast</b></p>
</center>

<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/cache_L30_T0.02_I2 fct comparisons/95th_fct_slowdown.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/LATENCY_cache_30_incast/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/PFC_cache_L30I2/pfc_pause_events_and_total_time.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 12: FCT analysis, latencies and PFC with CacheFollower for 30% avg.load + incast</b></p>
</center>

<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/cache_L50_T0.02fct comparisons/95th_fct_slowdown.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/LATENCY_cache_50/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/PFC_cache_L50/pfc_pause_events_and_total_time.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 13: FCT analysis, latencies and PFC with CacheFollower for 50% avg.load</b></p>
</center>
<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/cache_L50_T002_I2FCT comp/95th_fct_slowdown.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/LATENCY_cache_50_incast/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/PFC_cache_L50I2/pfc_pause_events_and_total_time.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 14: FCT analysis, latencies and PFC with CacheFollower for 50% avg.load + incast</b></p>
</center>

<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/googl_L30_T0.02_I2_fct_comp/95th_fct_slowdown.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/LATENCY_googl_30_incast/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/PFC_googl_L30I2/pfc_pause_events_and_total_time.png"
      style="width:100%"
      />
  </div>
    <p><b>Figure 15: FCT analysis, latencies and PFC with GoogleRPC for 30% avg.load + incast</b></p>
</center>
<center>
  <div style="display:inline-block; width:49%;">
    <img
      src="figures/googl_L50_T0.02_fct_comp/95th_fct_slowdown.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:49%;">
    <img
      src="figures/LATENCY_googl_50/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
      <p><b>Figure 16: FCT analysis, latencies and PFC with GoogleRPC for 50% avg.load</b></p>

</center>
<center>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/fct_googl_L50_t0.002_I2_fct_incast_comp/95th_fct_slowdown.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/LATENCY_googl_50_incast/packet_latency_95pct.png"
      style="width:100%"
      />
  </div>
  <div style="display:inline-block; width:32%;">
    <img
      src="figures/PFC_googl_L50I2/pfc_pause_events_and_total_time.png"
      style="width:100%"
      />
  </div>
  <p><b>Figure 17: FCT analysis, latencies and PFC with GoogleRPC for 50% avg.load+incast</b></p>

</center>

## 5.2. CC algorithms comparison with different distributions analysis

As we can see, HPCC outperforms any other algorithm regardless of traffic distributions or loads and has never triggered PFC pauses. This result positively answers to our question confirming HPCC as a better traffic-agnostic CC algorithm that successfuly meets the desired properties of low FCTs for short flows, minimal end-to-end latencies and zero PFC triggering. Even in presence of higher loads with incasts.

More in detail, experiments with AliStorage show similar FCTs and PFC pauses proportions to the ones obtained with FB_Hadoop distribution however, the number of PFC pauses are slightly increased and end-to-end latencies distributions are more contained.

No PFC pauses were detected in incast-free experiments apart for CacheFollower distribution, in which TIMELY experienced $3.7\ ms$ of pause time. In general, we see how, regardless of distributions, window-based schemes tend to have almost no PFC-pauses, lower FCTs and more contained latencies distributions.

We notice that GoogleRPC with-incasts scenarios are the only ones that do not follow the trend of lower latencies for window-based algorithms, revealing almost identical percentiles in every CC scheme. Due to the methodology implemented to select the most meaningful L3 traces, these results might just be the consequence of an unlucky flow selection.


# 6. Reproducibility Assessment of the Paper
## 6.1 Paper evaluation
The paper was well-organized, clearly answering to the research questions and motivating their relevance, while also sharing their experience in Alibaba Datacenters. HPCC's design was well described both with algorithm's pseudocode and comprehensive explanations of windows adjustments. In the end, we have not faced problem in understanding the techniques implemented by HPCC.

Experimental results were clearly organized and described, properly stating network topologies, traffic distributions and insights on why these results were expected. However, as we pointed out in section 3.4.1., some details and definitions were missing, in particular,the authors state *PFC pause duration* as a performance metric but there was no definition on how the Fraction of pause time was computed (eg. if considering just the time in which at least one interface was paused or by summing up each pause duration). 

## 6.2 Replication Package evaluation
We appreciated that the entire replication package was built upon an NS3 distribution, making it easier to run it an modifying it. While the generation of L3 traces was pretty straigh-forward, there are some problems we faced in our analysis:
- apart for the FCT plots, there were no scripts to easily extract from L3 traces information needed to reproduce the plots. In particular, throughput, queue lenghts, end-to-end latencies and PFC pauses durations have not been included;
- the $W_{AI}$ parameter, which the paper always describes as a window size, the artifact considered it as a rate, which we had to deduct how to convert;
- one of the results we had tried to reproduce were the ones in HPCC figures 13a and 13b. The artifact does not provide any way to run the HPCC algorithm with different response-policies (just the `fast_react` flag in configuration parameters). We believe that to effectively reproduce these results is necessary to heavily modify the HPCC algorithimn outside of `rdmahw.cc`, as after a fair few attempts, our results didnt match the paper(for brevity we didnt include this in the paper).
- in order to understand how traffic with incasts was generated in the paper's experiments we had to look at a Github issue [#36](https://github.com/alibaba-edu/High-Precision-Congestion-Control/issues/36) opened by an user attempting to reproduce these results, since neither the paper nor the artifact provided insights on how to simulate them.


# 7. Conclusion

We successfuly reproduced some interesting results of the HPCC paper and we confirmed some of the main paper takeways under additional scrutiny.

We confirmed the effectiveness of the rule of thumb suggested by the authors for $W_{AI}$ tuning.

By straining the selected CC algorithms with four different traffic distributions, we were able to confirm that window-based schemes show better FCTs for short flows, more contained latencies distributions and near-zero PFC pauses. Out of all CC algorithms, HPCC was the most performing one for each of the analysed metrics in any traffic condition.

---