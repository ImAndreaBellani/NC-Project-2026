# HPCC: High Precision Congestion Control
HPCC is a new high-speed CC (Congestion Control) mechanism which is able to achive:
* ultra-low latency;
* high bandwidth;
* network stability;
in high-speed networks.

In particular, it leverages in-network telemetry (INT) to obtain precise link load and it is fair and easy to deploy in hardware (the
implementation of the article is done with just commodity programmable NICs and switches).

## Introduction
Considering that data center networks link speed is growing dramatically, as well as the number of applications that require ultralow latency and high bandwidth.
In particular, authors have found (from Alibaba experience) two trends that drive the demand on high-speed networks:
* increasing usage of resource disaggregation and heterogeneous computing (eg. [17] shows that  resource disaggregation requires 3-5µs network latency and 40-100Gbps network bandwidth to maintain good application-level performance);
* increasing applications that periodically transfer large volume data with very fast storage and computation speeds (i.e. network is their bottleneck).

In order to satify these requirements, traditional software-based network stacks in hosts are not enough, and so network stacks have to be offloaded into hardware.
In fact, Alibaba has been using RDMA over Converged Ethernet Version 2 (RoCEv2) however, this solution revealed to be unsuccessful to satisfy the three requirements stated together, for instance:
* high speed implies that flows start at line rate and aggressively grab available network capacity, which can easily cause severe congestion in large-scale networks;
* high throughput usually results in deep packet queueing, which undermines the performance of latency-sensitive flows and the ability of the network to handle unexpected congestion.

## Experience and Motivation
## Design
## Implementation
## Performance Evaluation
