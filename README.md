[English](README.md) | [Русский](README.ru.md)

# FlyOps: Distributed Biological Connectome in Kubernetes

A distributed microservice architecture simulating a directed subgraph of the fruit fly (*Drosophila melanogaster*) brain connectome, featuring application-level L7 neuroplasticity and infrastructure-level L4 self-healing.

## System Architecture & Core Mechanisms
The system maps 19 interconnected biological neurons into Kubernetes pods powered by Python microservices, using CoreDNS for service discovery and a topology engine.
* **Loop Prevention:** Enforces a 400 ms refractory period (`REFRACTORY_PERIOD = 0.4`) to neutralize network echo loops.
* **Fault Tolerance:** Combines sub-millisecond L7 runtime rerouting with 1–3 second L4 Kubernetes pod reconciliation.

## Observability & Deployment
Exposes Prometheus metrics (`/metrics`) designed for the Grafana Node Graph Panel. Quick start and testing involve Minikube, Docker, and `kubectl` commands for deployment and failover verification.

*(Full documentation, setup steps, PromQL queries, and complete configuration can be found in the provided code block).*

