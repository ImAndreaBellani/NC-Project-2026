# HPCC: High Precision Congestion Control
HPCC is a new high-speed CC (Congestion Control) mechanism which is able to achive:
* ultra-low latency;
* high bandwidth;
* network stability;
  
in high-speed networks (however, authors have only tested on RDMA networks).

In particular, it leverages in-network telemetry (INT) to obtain precise link load and it is fair and easy to deploy in hardware (the
implementation of the article is done with just commodity programmable NICs and switches).

## Introduction
### Why these requirements for data center network?
Authors believe that a good Congestion Control is what enables the network to achive the requirements above because, because it is the primary mechanism to avoid packet buffering and losses due to high loads, which may lead high performance penalties and stability concerns.

Considering that data center networks link speed is growing dramatically, as well as the number of applications that require ultralow latency and high bandwidth.
In particular, authors have found (from Alibaba experience) two trends that drive the demand on high-speed networks:
* increasing usage of resource disaggregation and heterogeneous computing (eg. [17] shows that  resource disaggregation requires 3-5µs network latency and 40-100Gbps network bandwidth to maintain good application-level performance);
* increasing applications that periodically transfer large volume data with very fast storage and computation speeds (i.e. network is their bottleneck).

### Why a re-design of the CC?
In order to satify these requirements, traditional software-based network stacks in hosts are not enough and so network stacks have to be offloaded into hardware.
In fact, Alibaba has been using RDMA over Converged Ethernet Version 2 (RoCEv2) however, this solution revealed to be incosistent in satisfying the three requirements stated together, for instance:
* high speed implies that flows start at line rate and aggressively grab available network capacity, which can easily cause severe congestion in large-scale networks;
* high throughput usually results in deep packet queueing, which undermines the performance of latency-sensitive flows and the ability of the network to handle unexpected congestion.

### Limitations in the state-of-art CC mechanisms (DCQCN and TIMELY)
State-of-art CC mechanism have some essential limitations:
* slow convergence: the usage of coarse-grained feedback signals (eg. ECN or RTT) lead CC mechanisms to adapt sending rates with heuristics that iteratively try to converge to a stable rate distribution. This "slow convergence" is a particular problem when the CC has to handle large-scale congestion events;
* unavoidable packet queueing: even if with different approaches, both DCQCN and TIMELY make the sender reduce flow rates only after a queue builds up, which can significantly increase latency;
* complicated parameter tuning: heuristics of state-of-art CC mechanisms require to tune their parameters on the specific network environment, which is usually complex and time-consuming during daily operations (and there is also a risk using an incorrect setting causing network instability).

The fundamental cause behind these limitations is the lack of a fine-grained network load information in legacy networks. But recently, INT (In-network telemetry) features have become available in new commodity ASICS and so are now avaible on all levels of the network. HPCC obtains the precise link load information exactly from INT. By doing so, it receives accurate flow rate updates from switches, instead of relying on course-grain infos such as ECN markings or RTT. 

This enables HPCC to:
* only require 3 parameters to tune on deployment.
* have senders that can quickly and precisely ramp up or ramp down their rates as needed;

### HPCC challenges
Using INT in CC is not straightforward, INT information is piggybacked on packets that can be delayed by link congestion, which can delay the congestion detection. In addition, there are foundamental challenges (i.e. indipendent from leveraging INT) such as implementation friendliness and fairness.

## Experience and Motivation
### RDMA into the Alibaba network
Some basic information regarding Alibaba data center network:
* three layers Clos topology;
* each PoD is an indipendent RDMA domain;
* RoCEv2 with DCQCN as CC;
* PFC enabled in NICs and switches;
* go-back-N (i.e. NACK for retrasmission of lost packets)
RDMA was able to speed up a lot applications w.r.t. previous TCP/IP versions.
>[!warning]
>is this really necessary? its not incorrect but we arent really levaraging the "Alibaba experience" in our summary 
### Authors goals for RDMA
RDMA networks face more risks and tighter performance requirements than TCP/IP networks:
* RDMA hosts are aggressive for resources, they start sending at line rate, which makes common problems like incast much more severe than TCP/IP;
* PFC pauses all upstream interfaces once it detects a risk of packet loss, and the pauses can propagate via a tree-like graph to multiple hops away, rarely leading to:
  * PFC deadlocks;
  * PFC storms
* even in typical operations PFC can still suppress a large number of innocent senders (reported in figure 1);
* it often takes months to tune the parameters for RDMA before actual deployment, in order to find a good balance between high performances and stability, operators have to tune parameters for the deployment of each new application and new environment.

To sum up out objective is to find a solution that provides us with:
* as low as possible latency;
* as high as possible bandwidth utilization;
* as few as possible PFC pauses; 
* as low as possible operational complexity;

### Trade-offs in state-of-art RDMA CCs
From the authors experience, tuning DCQCN always struggles in facing two trade-offs:
* throughput vs. stability: to quickly utilize free network capacity, senders must be highly sensitive to the available bandwidth and increase flow rates fast, but this "aggressive" behavior can easily lead to large scale PFC pauses ( fig #);
* bandwidth vs. latency: for consistently low latency the network needs to maintain steadily small queues in buffers (which means low ECN marking thresholds), while senders will be too conservative to increase
flow rates if ECN marking thresholds are low (also this is shown with a dedicated experiment).

In addition, the timer-based scheduling of DCQCN can also trigger traffic oscillations during link failures and the queue-based feedback of ECN also creates a new trade-off between ECN threshold and PFC threshold.

## Design
Leveraging INT for getting precise traffic and queues information poses some challenge:

* during congestions, feedback signals can be delayed, which results in a significantly more inflight data than the Bandwidth-delay product for each sender, worsening congestion even more;
* senders must carefully navigate the tension between reacting quickly and overreacting to congestion feedback.

To deal with these challenges:
1. HPCC directly controls the number of inflight bytes (in contrast to DCQCN and TIMELY that only control the sending rate). This way, even if feedback signals are delayed, the senders do not send excessive packets congesting the system;
2. HPCC combines RTT-based and ACK-based reactions to overcome the tension in reacting, combining INT information from multiple messages at a time.

![The overview of HPCC framework.](<figures/figure 4.png> "The overview of HPCC framework.")

During the propagation of the packet from the sender to the receiver, each switch along the path leverages the INT feature of its switching ASIC to insert some meta-data that reports the current load of the packet’s egress port (eg. timestamp, queue length, transmitted bytes ecc.).
When the receiver gets the packet, it copies all the meta-data recorded by the switches to the ACK message it sends back to the sender, which uses them to decide how to adjust its flow rate (each time it receives an ACK with network load information).
>[!warning]
> this is just how normal INT works, so if we should either swap it at the start of the design section or maybe remove it (comment: to me is fine here, but when we write the final report we have to move it somewhere else)

### The HPCC algorithm
HPCC is a window-based scheme that controls the number of "inflight bytes" (i.e. bytes sent but not yet acknowledged), instead of controlling rates, which has an important advantage compared to controlling rates. 
Even if in absence of congestion $inflight=rate\times RTT$, controlling inflight bytes greatly improves the tolerance to delayed feedback during congestion, since controlling it, no matter how long the feedback gets delayed, permits to senders to immediately stop sending when the limit is reached (which greatly improves network stability).

We can divide the whole HPCC algorithm into three components:
* window management laws;
* congestion signals laws;
* control laws.

#### How senders manage their window
Each sender maintains a sending window, which limits the inflight bytes it can send. Note that this is also the standard approach of TCP however, in datacenter we have a strong difference between RTT (which is generally ultra-low compared to classic IP networks) and queueing delayes (which is the feedback delay for us).

The initial sending window size should be set so that flows can start at line rate, so authors use $W_{init} = B_{NIC}\times T$ (where $T$ is the RTT and $B_{NIC}$ is $NIC$ bandwidth) and the pacing rate at $R=\frac{W}{T}$ (this pacing is done, with just the commodity NICs functionality, to avoid bursty traffic).

#### How congestion signals are fired and windows are controlled
Given a generic link $j$, a congestion happens if $I_j = \sum_{i\in Flows(L)} W_i \ge B_j\times T$, where $B_j$ is the bandwidth of $j$, $T$ is the RTT (that we assume constant and homogeneous in the network topology) and $W_i$ is the window size of the flow $i$ traversing $j$. The goal is that each sender keeps its $W$ at a size that avoids congestions (to be precise, we set a parameter $\eta\to 1$ and try to achive $I_j = \eta \times B_j\times T$.

In general, $I_j$, which represents the number of infligh-bytes over $j$ is a sum of two components: $I_j = qlen_j + txRate_j\times T$, where $qlen_j$ is the queue lenght on link $j$.

In order to achive the goal, a sender reduces its window of a factor (considering the generic link $j$):
* $k_j = \frac{I_j}{\eta\times B_j\times T} = \frac{1}{\eta}*(\frac{qlen_j}{B_j\times T} + \frac{txRate_j}{B_j})$
which applied to the "worst" link the sender is sending over:
* $k_{max} = max_j(k_j)$
So, the window of a generic sender is:
* $W_i = \frac{W_i}{k_{max,i}}+W_{AI}$
where $W_{AI}<<W_i$ is an additive increase to ensure fairness.

Observations:
* $I_j = qlen_j + txRate_j\times T$ is an under-estimatation in case of multiple bottlenecks (WHY?), so HPCC requires multiple rounds to resolve the congestion however, during incast (which is the most common congestion case in data center according to [39]) there is only one bottleneck;
* 

## Implementation
The prototype of HPCC was implemented on commodity NICs with FPGA and commodity switching ASICs with P4 programmability. In particualar:

* on swithces: INT features are implemeneted;
* on NICs: the actual HPCC implementation.
  
In addition, authors have also implemented DCQCN just for comparison.

## Performance Evaluation
