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

HPCC: High Precison Congestion Control presents a novel approach to Congestion Control for Datacenter networks. In particular, it is a window-based Congestion Control algorithm designed for high-speed RDMA networks that leverages INT-MD (*In-band Network Telemetry - EMbed Data*) to get precise queue lenghts information.

In the paper, authors explain the motivation and theoretical foundations behind HPCC, its design and test its effectiveness with both testbed and NS-3 simulations, comparing it with state-of-art other Congestion Control algorithms for Datacenter Networks.

## 1.3. HPCC main contributions
The main contribution of the paper is the leverage of INT to improve the Congestion Control on large-scale and high-speed networks. The paper present a detailed description of the in-production Congestion Control mechanism running in the AliBaba Group datacenters, which can provide insights for the design of new cc mechanisms that leverage INT (which was not leveraged by other state-of-art CC mechanisms).

Moreover, the paper also shares AliBaba production experiences on the difficulties to operate on RDMA networks with the state-of-art CC mechanisms and clarifies the challenges of designing a Congestion Control algorithm for RDMA networks. 


## 1.2. Challenges in achieving High Precision Congestion Control for RDMA applications

### 1.2.1. RDMA networks in Datacencter

The demand of high-speed Datacenter networks is driven by two main trends, according to both state-of-art and authors experience:
- new *resource disaggregation* and *heterogeneous computing* architectures require both low network latency levels and high network bandwidth;
- new applications (eg. large-scale ML training on high computation speed devices) that periodically trasfer large volume data with super-fast storage and computation speeds, often making the network the real performance bottleneck.

To sustain these requirements, new approaches started to offload network stacks into hardware. Authors, in particular, started to deploy large-scale networks with *RDMA* (Remote Direct Memory Access) over *RoCEv2* (RDMA over Converged Ethernet Version 2).

### 1.2.2. Why designing a new Congestion Control algorithm

HPCC tries to cope with the foundamental challenges authors have experienced with RoCEv2 and overcome limitations of other state-of-art Congestion Control mechanism.

Authors highlight that in RDMA networks:
- many flows starting at line rate causing severe congestions and deep packet queueing;
- preventing PFC pauses, since they can cause huge traffic drops;
- short flows experiencing really long latency due to deep packet queueing.

To tame the problems mentioned above, an adequate Congestion Control mechanism is essential however, state-of-art CC algorithms (such as DCQCN and TIMELY) face important limitations, such as:
- slow convergence of iterative methods that leverage coarse-grained feedback signals (eg. ECN);
- techniques inherently based on mechanisms that wait queues build-ups (eg. ECN marking or detecting RTT increasing) to adjust sender rates;
- complicated parameter tuning due to an high number of parameters or laking of simple rules of thumb to set them.

Authors highlight how these limitation are a consequence of the heuristics implented to adjust sender rates accordingly to current network utilization. On the other side, HPCC overcomes these limitations leveraging INT, which enables senders to continuosly and precisely computing network utilization.

## 1.3. How HPCC works

<center>
  <img
    alt="HPCC leveraging INT-MD"
    src="figures/HPCC - Figure 4.jpg"
    style="width:70%;"
  />
  <p><b>Figure 1: The overview of HPCC framework</b></p>
</center>

The main keypoint of HPCC is the usage of INT-MD (*In-band Network Telemetry - EMbed Data*) to obtain precise link loads in particular, each switch in the path enqueues an INT header that contains various information which sender can use to proactively adjust its sending rate (eg. Queue Length). Instead of relying on heuristics or iterative approaches, senders receive a per-ACK updates to rapidly adjust the sending window, with a minimal set of algorithm's parameters.

When a new ACK arrives, the sender computes the current network utilization $U$ using information retrived from the INT headers collected over the flow path and updates its window. In particular, we can distinguish two different phases in the HPCC algorithm (names are invented by us to easily distinguish them):
- *agnostic phase* : the sender updates its window regardless of network utilization $U$ (tough it stills keeps calculating $U$);
- *adaptive phase* : the sender adapts its window adjusting it of a factor $\frac{\eta}{U}$ (note that if $U<<\eta$ the window increases, which is fine since the network is not congested).

Senders normally start in the agnostic phase and pass to the adaptive one after a certain number of RTTs or if $U\geq\eta$.

Instead of directly updating sending window starting from the previous value, sender always adjusts its window from what we can call a *reference window* $W^C$ that is updated nearly every-RTT (to be more precise, it is updated only when the ACK of the first packet sent from the last $W^C$ update is received). This technique is implemented to ensure what authors call *fast reaction without over-reaction*. In other words, it is essential that the sender quickly reacts to changes (so, every-ACK received), but adjusting its window completely at every ACK received is ... because ... (mettere la cosa che tutte le code sono diverse ogni RTT). So, the window adjustment is performed at per-ACK starting from a reference window ($W^C$) that is updated nearly every-RTT.

Note that HPCC requires just $3$ parameters to be configured, which meaning is quite easy to understand:
<center>
  <table>
    <tr>
      <th>Parameter</th><th>Meaning</th><th>How to set it</th>
    </tr>
    <tr>
      <th>$\eta$</th>
      <td>Network utilization threshold that triggers the adaptive phase</td>
      <td>Nearly to $0.95$, depening on how critical the </td>
    </tr>
    <tr>
      <th>$W_{AI}$</th>
      <td>Additive Increase window to ensure fairness</td>
      <td>Rule of thumb: $W_{AI} = \frac{W_{init}\times(1-\eta)}{N}$, where $N$ is the (maximum) number of expected concurrent flows on a single link</td>
    </tr>
    <tr>
      <th>$maxStage$</th>
      <td>Number of maximum stage before passing to the adaptive phase</td>
      <td>Generally low</td>
    </tr>
  </table>
</center>



<div class="pagebreak"></div>

# 2. Selected Result
## 2.1. Fairness and queue size with $W_{AI}$

<center>
  <img
    alt="Considering an incast of 16 flows, Figure 14a shows the average throughput for different W_AI values, Figure 14b shows length's percentiles of the incast Queue"
    src="figures/HPCC - Figure 14.jpg"
    style="width:90%;"
    />
  <p><b>Figure 2: Fairness and queue size with $W_{AI}$</b></p>
</center>

## 2.2. Different ways of reacting to ACK.
<center>
  <img
    alt="Considering an incast of 16 flows, Figure 14a shows the average throughput for different W_AI values, Figure 14b shows length's percentiles of the incast Queue"
    src="figures/HPCC - Figure 13.jpg"
    style="width:90%;"
    />
  <p>Considering an incast of 16 flows, Figure 13a and Figure 13b shows respectively the aggregated throughput and Queue Length running HPCC with different reacting policies</p>
</center>


# 3. Environment Setup

*Note:* This section should contain enough information to allow someone else to
reproduce *your* report. Share hardware and/or software setup relevant to your
experiment. For example:

**Hardware Environment:**
CPU, Memory, Storage, Network, Cloud / local / cluster, Any relevant micro-architectural details

**Software Environment**
OS version, Kernel version, Compiler version, Libraries, Dependencies, Paper artifact used (Yes/No; version/commit hash)

**Configuration Parameters:**

- Workload configuration
- Dataset
- Runtime parameters and flags

**Deviations from the Original Setup:**

Clearly describe any difference between papers and your experiment environment.

- Hardware differences
- Software version differences
- Dataset substitutions
- Unavailable components

Explain why these deviations were necessary.

If something was **missing in the original paper**, state it. For example:

> The paper does not specify X. We assumed Y (or explored range *a* to *b*).

# 4. Experiment Result

> Explain how your experiment was conducted and then what results you acquired. 
Afterwards, compare your results with those of the paper and state your
takeaways.

Step-by-step description:

1. Execution procedure
1. Measurement method
1. Number of runs
1. Statistical treatment (mean, median, CI, etc.)

Also Describe:

- How did you ensure correctness (did you check also other metrics to make sure the experiment is running correctly?)
- Did you do any debugging? Discuss issues you faced and how you overcame them (if applicable consider allocating a subsection for this item) 

Share your result and compare them with the paper's. Then discuss your takeaways.

For comparison include:

- Graph(s) or table(s)
- Matching axes and units with the source paper
- Error bars if applicable
- You may want to report difference with the original results (e.g., absolute
number or percentage).

For example:

<center>
  <div style="display:inline-block; width:30%;">
    <img
      alt="The figure shows that method A improves throughput compared to method B"
      src="figures/one_bar.png"
      style="width:100%"
      />
    <p>Figure 2: The figure shows that method A improves throughput compared to method B</p>
  </div>
  <div style="display:inline-block; width:30%; padding-left: 1em">
    <img
      alt="Our reproduction of Figure 1 shows results with the similar trend as claimed by the paper"
      src="figures/two_bar.png"
      style="width:100%"
      />
    <p>Figure 3: Our reproduction of Figure 1 shows results with the similar trend as claimed by the paper</p>
  </div>
</center>

> **Reminder:** the goal is not achieve the exact results of the paper, but to do a rigorous experiment with similar assumptions from the source paper and gain insight. The insight can be correctness of work, failure to reproduce same results, or even infeasibility of doing such experiment for interesting reasons.

# 5. Further Exploration

In this project you are required to also explore a research question of your own. Either:

1. Take the same test with different input workload or a variation of a test that is not present in the paper and comment the results you obtain
1. Implement a new feature on top of the system you evaluated and show a figure showing the performance

Discuss which approach you take, and what you explored. Explain what was your
motivation and importance of your question.

## 5.1. Methodology and Result

Report the experiment you designed for answering the question and share the
result you got.

Include:

- Graph(s) or table(s)
- How the experiment was conducted (share the details)
- What did you discover?

# 6. Reproducibility Assessment of the Paper

Evaluate the paper itself:

- Was the methodology clearly described?
- Was the artifact usable?
- How difficult was reproduction?

## 6.1 Paper evaluation

## 6.2 Replication Package evaluation

# 7. Conclusion

Conclude the report by mentioning the takeaways of experiments you did


---