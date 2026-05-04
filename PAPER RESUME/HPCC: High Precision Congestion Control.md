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
Authors believe that a good Congestion Control is what enables the network to achive the requirements above because, bcause it is the primary mechanism to avoid packet buffering and losses due to high loads, which may lead high performance penalties and stability concerns.

Considering that data center networks link speed is growing dramatically, as well as the number of applications that require ultralow latency and high bandwidth.
In particular, authors have found (from Alibaba experience) two trends that drive the demand on high-speed networks:
* increasing usage of resource disaggregation and heterogeneous computing (eg. [17] shows that  resource disaggregation requires 3-5µs network latency and 40-100Gbps network bandwidth to maintain good application-level performance);
* increasing applications that periodically transfer large volume data with very fast storage and computation speeds (i.e. network is their bottleneck).

### Why a re-design of the CC?
In order to satify these requirements, traditional software-based network stacks in hosts are not enough, and so network stacks have to be offloaded into hardware.
In fact, Alibaba has been using RDMA over Converged Ethernet Version 2 (RoCEv2) however, this solution revealed to be unsuccessful to satisfy the three requirements stated together, for instance:
* high speed implies that flows start at line rate and aggressively grab available network capacity, which can easily cause severe congestion in large-scale networks;
* high throughput usually results in deep packet queueing, which undermines the performance of latency-sensitive flows and the ability of the network to handle unexpected congestion.

### Limitations in the state-of-art CC mechanisms (DCQCN and TIMELY)
State-of-art CC mechanism have some essential limitations:
* slow convergence: the usage of coarse-grained feedback signals (eg. ECN or RTT) lead CC mechanisms to adapt sending rates with heuristics that iteratively try to converge to a stable rate distribution. This "slow convergence" is a particular problem when the CC has to handle large-scale congestion events;
* unavoidable packet queueing: even if with different approaches, both DCQCN and TIMELY make the sended reduce flow rates only after a queue builds up, which can significantly increase latency;
* complicated parameter tuning: heuristics of state-of-art CC mechanisms require to tune their parameters on the specific network environment, which is usually complex and time-consuming during daily operations (and there is also an higher risk of coming up with incorrect setting).

The fundamental cause behind these limitations is the lack of a fine-grained network load information in legacy network (at most ECN). But recently, INT (In-network telemetry) features have become available in new ASICs and CC can really benefit from it. HPCC obtains the precise link load information exactly from INT. By doing so, it receives accurate flow rate updates from switches, instead of relying on course-grain infos such as ECN or RTT. And this is basically the secret of HPCC, in particular:
* senders can quickly and precisely ramp up on ramp down their rates at need;
* HPCC just requires 3 parameters to tune.

### HPCC challenges
Using INT in CC is not straightforward, INT information piggybacked on packets can be delayed by link congestion, which can defer the flow rate reduction for resolving the congestion (i.e. possible delays and/or ovverractions). In addition, there are foundamental challenges (i.e. indipendent by the leveraging of INT) sucb as implementation friendlyness and fairness.

## Experience and Motivation
### RDMA into the Alibaba network
Some basic information regarding Alibaba data center network:
* three layers Clos topology;
* each PoD is an indipendent RDMA domain;
* RoCEv2 with DCQCN as CC;
* PFC enabled in NICs and switches;
* go-back-N (i.e. NACK for retrasmission of lost packets)
RDMA was able to speed up a lot applications w.r.t. previous TCP/IP versions.

### Authors goals for RDMA
RDMA networks face more risks and tighter performance requirements than TCP/IP networks:
* RDMA hosts are aggressive for resources, so they start sending at line rate, which makes common problems like incast much more severe than TCP/IP;
* PFC pauses all upstream interfaces once it detects a risk of packet loss, and the pauses can propagate via a tree-like graph to multiple hops away, possibly leading to (they are pretty rare):
  * PFC deadlocks;
  * PFC storms
* even in "normal cases" (neither deadlocks nor storms), PFC can still suppress a large number of innocent senders (authors have really experienced that and reported it in figure 1);
* it often takes months to tune the parameters for RDMA before actual deployment, in order to find a good balance between high performances and stability. Moreover, because different applications have different traffic patterns, and different environments have different topologies, link
speeds, and switch buffer sizes, operators have to tune parameters
for the deployment of each new application and new environment.

To sum up:
* latency as low as possible and bandwidth/utilization as high as possible;
* congestion and PFC pauses as few as possible;
* (tuning) operational complexity as low as possible.

### Trade-offs in state-of-art RDMA CCs
From authors experience, tuning DCQCN always struggles in facing two trade-offs:
* throughput vs. stability: to quickly utilize free network capacity, senders must be highly sensitive to the available bandwidth and increase flow rates fast, but this "aggressive" behavior can easily lead to large scale PFC pauses (authors also show it with an experiment);
* bandwidth vs. latency: for consistently low latency the network needs to maintain steadily small queues in buffers (which means low ECN marking thresholds), while senders will be too conservative to increase flow rates if ECN marking thresholds are low (also this is shown with a dedicated experiment).

In addition, the timer-based scheduling of DCQCN can also trigger traffic oscillations during link failures and the queue-based feedback of ECN also creates a new trade-off between ECN threshold and PFC threshold.

## Design

## Implementation
## Performance Evaluation
