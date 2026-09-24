# FlyOps 2.0: Resilient Drosophila Connectome Mesh in Kubernetes

[![Kubernetes](https://img.shields.io/badge/Orchestration-Kubernetes%20v1.28%2B-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus%20Operator-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Visualization-Grafana%20Node%20Graph-F46800?logo=grafana&logoColor=white)](https://grafana.com/)
[![Docker](https://img.shields.io/badge/Containerization-Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Runtime-Python%203.11%20AsyncIO-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An experimental, biologically inspired distributed systems architecture simulating a 19-neuron connectome slice of the *Drosophila melanogaster* nervous system inside a Kubernetes cluster. 

The project demonstrates high-availability distributed computing concepts, microservice mesh resiliency, service discovery over CoreDNS, storm-prevention rate limiting, dual-layer fault recovery (L4 self-healing + L7 socket failover rerouting), and real-time topology visualization through Prometheus Operator and Grafana Node Graph.

---

## Architectural Overview

FlyOps 2.0 abstracts biological neural circuits into a decentralized microservice graph where each neuron is an autonomous, containerized network unit. Rather than relying on a centralized message broker, neurons communicate directly via peer-to-peer asynchronous HTTP/TCP calls resolved dynamically via Kubernetes cluster DNS.

```
                           [ EXTERNAL INGRESS / SENSORY PULSE ]
                                            |
                                            v
+=======================================================================================+
| SENSORY LAYER (Afferent Ingress)                                                     |
|                                                                                       |
|   +---------------+      +---------------+      +---------------+      +---------------+  |
|   |   Neuron-01   |      |   Neuron-02   |      |   Neuron-03   |      |   Neuron-04   |  |
|   | [Antenna-L]   |      | [Antenna-R]   |      | [Optic-L]     |      | [Optic-R]     |  |
|   +-------+-------+      +-------+-------+      +-------+-------+      +-------+-------+  |
+===========|======================|======================|======================|======+
            |                      |                      |                      |
            +------------+---------+                      +----------+-----------+
                         |                                           |
                         v                                           v
+=======================================================================================+
| INTERMEDIATE PROCESSING LAYER (Local & Projection Interneurons)                       |
|                                                                                       |
|          +--------------------+                   +--------------------+              |
|          |     Neuron-05      |<=================>|     Neuron-06      |              |
|          |    (Antennal-L)    |   L7 Cross-Inhib  |    (Antennal-R)    |              |
|          +---------+----------+                   +----------+---------+              |
|                    |                                         |                        |
|                    v                                         v                        |
|          +--------------------+                   +--------------------+              |
|          |     Neuron-07      |                   |     Neuron-08      |              |
|          +---------+----------+                   +----------+---------+              |
|                    |                                         |                        |
|                    +--------------------+   +----------------+                        |
|                                         |   |                                         |
|                                         v   v                                         |
|          +-------------------------------------------------------------+              |
|          |              Central Complex Relay (N09 - N14)              |              |
|          |  +---------+   +---------+   +---------+   +---------+      |              |
|          |  | Neu-09  |-->| Neu-10  |-->| Neu-11  |-->| Neu-12  |      |              |
|          |  +----+----+   +----+----+   +----+----+   +----+----+      |              |
|          |       |             |             |             |           |              |
|          |       \-------------+------+------+-------------/           |              |
|          |                            |                                |              |
|          |                     +------v------+   L7 Failover Path      |              |
|          |                     |  Neu-13/14  | - - - - - - - - - - +   |              |
|          |                     | (Modulators)|                     |   |              |
|          |                     +------+------+                     |   |              |
|          +----------------------------|----------------------------|--+              |
+=======================================|============================|==================+
                                        |                            |
                                        v                            v (Alternate Route)
+=======================================================================================+
| MOTOR OUTPUT LAYER (Descending / Premotor Neurons)                                    |
|                                                                                       |
|   +---------------+      +---------------+      +---------------+      +---------------+  |
|   |   Neuron-15   |      |   Neuron-16   |      |   Neuron-17   |      |   Neuron-18/19|  |
|   | [Wing-L Beat] |      | [Wing-R Beat] |      | [Proboscis]   |      | [Escape Jump] |  |
|   +---------------+      +---------------+      +---------------+      +---------------+  |
+=======================================================================================+
```

<p align="center">
  <img src="docs/Screenshot_1.png" alt="Connectome Neural Wiring Topology" width="850">
  <br>
  <em>Figure 1: Full 19-neuron connectome communication schema, functional hierarchy, and synaptic routing layers.</em>
</p>

### Microservice Isolation & Pod Mapping
Every neuron in the connectome operates as a standalone containerized process, decoupled from its peers. Kubernetes manages individual Pod resources, ensuring independent CPU/Memory quotas, liveness lifecycle handling, and direct DNS resolution.

<p align="center">
  <img src="docs/Screenshot_2.png" alt="Kubernetes Pod Architecture" width="850">
  <br>
  <em>Figure 2: Microservice deployment running each neuron as an autonomous, isolated Kubernetes Pod.</em>
</p>

### Core Design Principles

1. **Decentralized Service Discovery**: Nodes query target downstream pods using internal CoreDNS names (`http://neuron-XX.flyops.svc.cluster.local:8080/stimulate`). No central orchestrator dictates routing at runtime.
2. **Storm Mitigation via Refractory Period (400ms)**: Biological neurons cannot fire immediately after depolarization. FlyOps implements an absolute refractory period of 400 milliseconds per pod. Any stimulus arriving during this window is dropped with a `429 Too Many Requests / Dropped` status. This prevents cascading loops and CPU starvation within circular graph structures.
3. **Dual-Layer Self-Healing**:
   - **Layer 4 (Orchestrator Level)**: Kubernetes `ReplicaSet` controllers enforce desired state. If a neuron container experiences an Out-Of-Memory (OOM) or unhandled runtime panic, Kubernetes terminates and recreates the pod, restoring network participation within seconds.
   - **Layer 7 (Application/Mesh Level)**: If an outbound TCP socket connection times out (> 50ms) or returns an HTTP 5xx error, the sending neuron executes an adaptive fallback routing policy, dynamically redirecting the action potential to an alternate downstream synaptic pathway without dropping the distributed signal chain.
4. **End-to-End Observability**: Custom Prometheus metrics capture every spike, drop, latency spike, and failover incident. A Grafana Node Graph dashboard visualizes traffic flow, edge latencies, and node health in real time.

---

## Technical Specifications

| Parameter | Specification | Description |
| :--- | :--- | :--- |
| **Cluster Nodes** | 19 Independent Pods | One Pod per biological neuron archetype |
| **Namespace** | `flyops` | Isolated virtual cluster network |
| **Refractory Window** | 400 ms | Bio-inspired rate limiting & loop dampening |
| **Synaptic Timeout** | 50 ms (configurable) | L7 threshold before initiating reroute |
| **Network Fabric** | Standard Kube-DNS / CoreDNS | Endpoint resolution across the mesh |
| **Metrics Collector**| Prometheus Operator (v0.68+) | Automated scraping via `ServiceMonitor` |
| **Telemetry Format** | Prometheus OpenMetrics | Scraped at `/metrics` on port 8080 |
| **Visualization** | Grafana (Node Graph Panel) | Visual representation of directed acyclic graph |

---

## Resilience & Fault-Tolerance Mechanics

### 1. Storm Suppression & Anti-Resonance
In an interconnected neural network with recurrent loops, positive feedback can cause an exponential amplification of signals (analogous to a packet storm or broadcast storm). 

FlyOps 2.0 enforces a strict atomic refractory timestamp check inside each neuron's event loop:

$$\Delta t = t_{\text{current}} - t_{\text{last\_depolarization}}$$

$$\text{Action} = \begin{cases} \text{Propagate Spike}, & \text{if } \Delta t \ge 400\text{ ms} \\ \text{Increment Drop Counter \& Abort}, & \text{if } \Delta t < 400\text{ ms} \end{cases}$$

This mathematical barrier guarantees that the network remains bounded and stable even under pathological external ingress loads.

### 2. L7 Dynamic Synaptic Rerouting
Each neuron maintains an internal adjacency table representing synaptic downstream targets. If the primary target fails to acknowledge the pulse within the configured window, the client initiates a secondary branch:

```python
async def forward_pulse(primary_target: str, fallback_target: str, payload: dict):
