# FlyOps 2.0: Микросервисный стенд в Kubernetes

[English](README.en.md) | **Русский**

Учебный стенд для практики с Kubernetes, микросервисами и мониторингом. В кластере развернуто 19 взаимодействующих сервисов на базе Minikube.

Топология сети взята из схемы связей нейронов (Drosophila connectome) — это дало разветвленную сеть с перекрестными зависимостями, на которой удобно тестировать отказ узлов, перемаршрутизацию запросов и мониторинг.

---

## Что сделано в проекте:

- **Развертывание в Kubernetes:** 19 подов с ограничениями по ресурсам (CPU/RAM), пробами `livenessProbe` / `readinessProbe` и внутренним DNS (CoreDNS).
- **Восстановление при падении узлов (L4):** при удалении пода (`kubectl delete pod`) ReplicaSet поднимает новый контейнер за 3 секунды.
- **Резервные маршруты в коде (L7):** перехват ошибки `Errno 111 Connection refused`. Если соседний сервис недоступен, запрос автоматически уходит по резервному пути.
- **Ограничение частоты запросов:** защита от флуда с возвратом HTTP 429, чтобы сервисы не уходили в OOMKilled при резком росте нагрузки.
- **Мониторинг:** экспорт метрик в Prometheus через `ServiceMonitor` и дашборд с графом связей в Grafana (Node Graph).

---

## Схема взаимодействия

Каждый узел — это сервис на Python (aiohttp) в Docker-контейнере. Сервисы общаются между собой по HTTP внутри кластера:

```
                         [ Входящий запрос ]
                                  |
                                  v
+=======================================================================================+
| Входной слой (сервисы 01-04)                                                          |
+=======================================================================================+
                                  |
                                  v
+=======================================================================================+
| Промежуточный слой (сервисы 05-14)                                                    |
|                                                                                       |
|   Основной маршрут: 09 -> 10 -> 11 -> 12                                              |
|   Резервный маршрут: при недоступности узла запрос переключается на 13/14             |
+=======================================================================================+
                                  |
                                  v
+=======================================================================================+
| Выходной слой (сервисы 15-19)                                                         |
+=======================================================================================+
```

<p align="center">
  <img src="docs/Screenshot_1.png" alt="Схема связей стенда" width="850">
  <br>
  <em>Схема связей между сервисами.</em>
</p>

<p align="center">
  <img src="docs/Screenshot_2.png" alt="Поды в кластере Kubernetes" width="850">
  <br>
  <em>Запущенные поды в пространстве имен flyops.</em>
</p>

---

## Тестирование отказоустойчивости

### 1. Падение пода (L4 Self-Healing)
Удаляем работающий под и смотрим на реакцию кластера:

```bash
kubectl delete pod -n flyops -l app=neuron-4490 --now && kubectl get pods -n flyops -l app=neuron-4490
```

Kubernetes видит расхождение в ReplicaSet и запускает новый под за 3 секунды.

<p align="center">
  <img src="docs/Screenshot_4.png" alt="Восстановление пода" width="850">
  <br>
  <em>Восстановление пода после удаления.</em>
</p>

---

### 2. Перемаршрутизация при сетевом сбое (L7 Failover)
Удаляем промежуточный узел во время передачи данных:

```bash
kubectl delete pod -n flyops -l app=neuron-8152 --now
```

Сервис-отправитель перехватывает ошибку сокета (`[Errno 111] Connection refused`) и отправляет запрос на резервный адрес:

```python
async def forward_pulse(primary_target: str, fallback_target: str, payload: dict):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(primary_target, json=payload, timeout=0.050) as resp:
                if resp.status == 200:
                    METRICS_FORWARDED.labels(status="success", route="primary").inc()
                    return await resp.json()
    except (asyncio.TimeoutError, aiohttp.ClientError):
        METRICS_FAILOVER.inc()
        # Переключение на резервный адрес
        async with aiohttp.ClientSession() as session:
            async with session.post(fallback_target, json=payload, timeout=0.050) as resp:
                METRICS_FORWARDED.labels(status="success", route="fallback").inc()
                return await resp.json()
```

<p align="center">
  <img src="docs/Screenshot_3.png" alt="Лог переключения маршрута" width="850">
  <br>
  <em>Перехват ошибки Errno 111 и отправка по запасному пути.</em>
</p>

---

### 3. Нагрузочный тест и отсечение флуда
Подаем поток запросов утилитой `hey`:

```bash
hey -n 500 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"stimulus": "hyper_burst", "amplitude": 1.0}' \
  http://$(minikube ip):$(kubectl get svc neuron-01 -n flyops -o jsonpath='{.spec.ports[0].nodePort}')/stimulate
```

Сервис обрабатывает не более одного запроса за 400 мс, а лишний трафик сбрасывает с кодом 429. Потребление памяти и процессора остается стабильным.

---

## Метрики (Prometheus и Grafana)

Каждый под отдает метрики на порту `:8080/metrics`:

| Метрика | Тип | Назначение |
| :--- | :--- | :--- |
| `flyops_spikes_received_total` | Counter | Количество входящих запросов |
| `flyops_spikes_forwarded_total` | Counter | Успешно отправленные дальше запросы |
| `flyops_refractory_drops_total` | Counter | Запросы, отсеченные лимитером (HTTP 429) |
| `flyops_l7_failover_events_total` | Counter | Срабатывания переключения на резервный путь |
| `flyops_propagation_latency_seconds` | Histogram | Время сетевого ответа между сервисами |

Сбор метрик настроен через `ServiceMonitor`. Для визуализации используется Grafana Node Graph.

---

## Запуск проекта

### Требования:
- Linux / WSL2
- Docker, Minikube, kubectl, Helm v3+

### Команды для запуска:

```bash
# 1. Запуск Minikube
minikube start --cpus=4 --memory=8192 --disk-size=25g --driver=docker

# 2. Установка стека мониторинга
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

# 3. Деплой манифестов
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap-topology.yaml
kubectl apply -f k8s/02-neurons-sensory.yaml
kubectl apply -f k8s/03-neurons-inter.yaml
kubectl apply -f k8s/04-neurons-motor.yaml
kubectl apply -f k8s/05-servicemonitor.yaml

# 4. Проверка статуса
kubectl get pods -n flyops
```

---

## Структура репозитория

```
FlyOps-2.0/
├── docs/                             # Скриншоты работы стенда
├── k8s/                              # Манифесты Kubernetes
│   ├── 00-namespace.yaml
│   ├── 01-configmap-topology.yaml
│   ├── 02-neurons-sensory.yaml
│   ├── 03-neurons-inter.yaml
│   ├── 04-neurons-motor.yaml
│   └── 05-servicemonitor.yaml
├── monitoring/
│   ├── grafana-nodegraph-dash.json   # Дашборд Grafana
│   └── prometheus-rules.yaml         # Правила алертов
├── src/
│   ├── app.py                        # Код сервиса на aiohttp
│   ├── config.py                     # Загрузка конфигурации
│   ├── metrics.py                    # Метрики Prometheus
│   └── Dockerfile                    # Сборка образа
├── scripts/
│   ├── stimulate.sh                  # Отправка тестовых запросов
│   └── chaos_kill_node.sh            # Скрипт симуляции сбоев
└── README.md
```

## Лицензия
MIT
