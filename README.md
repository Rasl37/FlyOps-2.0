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
