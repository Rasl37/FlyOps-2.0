[English](README.md) | [Русский](README.ru.md)

# FlyOps: Распределенный биологический коннектом в Kubernetes

Распределенная микросервисная архитектура, симулирующая ориентированный подграф коннектома мозга дрозофилы (*Drosophila melanogaster*), демонстрирующая двухуровневую отказоустойчивость: нейропластичность на уровне L7 и Self-Healing на уровне L4 в условиях циклического графа.

## Архитектура и механизмы

19 биологических нейронов работают в независимых подах Kubernetes (Python), используя CoreDNS для Service Discovery и `topology.json` для определения ролей (`Sensory`, `Processing`, `Motor`).

* **Рефрактерный период:** Пауза в 400 ms (`REFRACTORY_PERIOD = 0.4`) блокирует повторные импульсы и предотвращает сетевые штормы/циклы (Echo Loops).
* **Двухуровневая отказоустойчивость:** 
  * *L7 Приложение:* Перенаправление трафика на резервные синапсы за < 5 мс при `Connection refused`.
  * *L4 Платформа:* Автовосстановление подов (`neuron-4490`) силами ReplicaSet за 1–3 секунды.

## Метрики и проверка

Эндпоинт `/metrics` предоставляет данные для Grafana Node Graph (`flyops_node_spikes_total`, `flyops_edge_spikes_total`, `flyops_node_status`, `flyops_edge_status`).

### Быстрый запуск
```bash
minikube start --cpus=2 --memory=4096
kubectl create namespace monitoring
eval \$(minikube docker-env)
docker build -t flyops-neuron:latest .
kubectl apply -f k8s.yaml -n monitoring
```

*Полный исходный код документации и конфигурации доступен в оригинальном файле репозитория.*
