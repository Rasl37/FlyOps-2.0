# FlyOps: Распределенный биологический коннектом в Kubernetes

Распределенная микросервисная архитектура, симулирующая ориентированный подграф коннектома мозга дрозофилы (*Drosophila melanogaster*). Система демонстрирует два независимых контура отказоустойчивости: **прикладную нейропластичность на уровне L7 (динамическая перемаршрутизация в обход сбоя)** и **инфраструктурный Self-Healing на уровне L4 (автовосстановление силами контроллеров Kubernetes)** в условиях сложного циклического графа.

---

## Архитектура системы

```text
[ Входной сенсор (Sensory) ]
           │  (периодическая стимуляция 4-6 с)
           ▼
[ Сетка обработки (17 нейронов Processing) ] ── (Циклический граф с L7-фильтром)
     │                                    │
     ▼ (Основной маршрут)                 ▼ (Резервный синапс)
[ neuron-4490 (Узкое горлышко / SPOF) ] [ neuron-8152 (Отказ) ] ──> Failover через neuron-3323
     │
     ▼
[ Моторный нейрон (Motor / Конечный узел) ]
```

Система переносит 19 взаимосвязанных биологических нейронов в отдельные поды Kubernetes под управлением легковесного скрипта на Python.

* **Service Discovery:** прямое межсервисное взаимодействие через Kubernetes CoreDNS (`http://<имя-нейрона>:8000/fire`).
* **Топологический движок:** каждый микросервис при старте вычисляет свою функциональную роль (`Sensory`, `Processing`, `Motor`) на основе входящих и исходящих ребер из `topology.json`.

<p align="center">
  <img src="docs/Screenshot_2.png" alt="Статус всех подов нейронов в кластере" width="850">
</p>

---

## Инженерные механизмы

### 1. Предотвращение зацикливания (Биологический рефрактерный период)
Наличие циклов и обратных связей в топологии мозга неизбежно порождает лавинообразное усиление трафика (Retry Storms / Echo Loops).
* **Механизм:** локальная блокировка состояния фиксирует время спайка и выдерживает паузу в 400 мс (`REFRACTORY_PERIOD = 0.4`).
* **Поведение:** импульсы, приходящие в течение периода невозбудимости, мгновенно сбрасываются с легким ответом HTTP 200, разрывая замкнутый сетевой шторм без падения сокетов.

### 2. Двухуровневая отказоустойчивость

| Уровень | Триггер сбоя | Механизм обработки | Время восстановления |
| :--- | :--- | :--- | :--- |
| **L7 Приложение (Нейропластичность)** | Обрыв соединения с целевым узлом (`Connection refused`) | Программное перенаправление трафика на оставшиеся активные синапсы | Менее 5 мс (без потери импульса) |
| **L4 Платформа (Оркестрация)** | Принудительное удаление / сбой SPOF-узла (`neuron-4490`) | Срабатывание Reconciliation Loop контроллера ReplicaSet в K8s | 1–3 секунды |

---

## Observability и визуализация (Grafana Node Graph)

Каждый микросервис отдает нативный эндпоинт `/metrics` в формате Prometheus. Структура метрик адаптирована для прямой отрисовки топологии в **Grafana Node Graph Panel**:

<p align="center">
  <img src="docs/Screenshot_1.png" alt="Grafana Node Graph - топология спайков" width="850">
</p>

### Экспортируемые метрики

| Метрика | Тип | Лейблы | Описание |
| :--- | :--- | :--- | :--- |
| `flyops_node_spikes_total` | Counter | `id`, `title`, `subtitle` | Суммарное число спайков, обработанных данным нейроном |
| `flyops_edge_spikes_total` | Counter | `id`, `source`, `target` | Трафик импульсов по конкретному синапсу (ребру) |
| `flyops_node_status` | Gauge | `id` | Рабочий статус узла (`1` = Healthy, `0` = Degraded) |
| `flyops_edge_status` | Gauge | `id`, `source`, `target` | Статус связи (`1` = Доступен, `0` = Ошибка сети) |

### Запросы PromQL для панели

* **Узлы (Nodes Query):** `flyops_node_status`
* **Ребра (Edges Query):** `rate(flyops_edge_spikes_total[1m])`

---

## Проверка сценариев отказоустойчивости

### 1. L7-перемаршрутизация прикладного уровня (Нейропластичность)
При искусственном отключении целевого узла `neuron-8152` маршрутизирующий узел `neuron-3323` перехватывает ошибку сокета и перенаправляет импульс по резервным синапсам:

<p align="center">
  <img src="docs/Screenshot_3.png" alt="L7 Failover - Активация резервно


го пути" width="850">
</p>

```text
[neuron-3323] Ошибка синапса к neuron-8152 (neuron-8152): <urlopen error [Errno 111] Connection refused>
[neuron-3323] Резервный путь активирован: перенаправление импульса в обход сбоя!
```

### 2. L4-самовосстановление инфраструктуры (Kubernetes Self-Healing)
Мгновенное удаление критического узкого горлышка (`neuron-4490`) инициирует автоматическое поднятие новой реплики контроллером ReplicaSet из локального кэша за считанные секунды:

<p align="center">
  <img src="docs/Screenshot_4.png" alt="L4 Self-Healing - Мгновенное пересоздание пода" width="850">
</p>

```bash
kubectl delete pod -n monitoring -l app=neuron-4490 --now && \
  echo "--- 1. CREATING ---" && kubectl get pods -n monitoring -l app=neuron-4490 && \
  sleep 3 && \
  echo "--- 2. RECOVERED ---" && kubectl get pods -n monitoring -l app=neuron-4490
```

```text
pod "neuron-4490-64cffdc7b7-lb28r" deleted from monitoring namespace
--- 1. CREATING (AGE 1s) ---
NAME                                READY   STATUS    RESTARTS   AGE
neuron-4490-64cffdc7b7-s54zq        1/1     Running   0          3s
--- 2. RECOVERED (RUNNING) ---
NAME                                READY   STATUS    RESTARTS   AGE
neuron-4490-64cffdc7b7-s54zq        1/1     Running   0          6s
```

---

## Быстрый запуск

### Требования
* Minikube >= v1.30
* Утилита kubectl
* Docker

### 1. Подготовка кластера
```bash
minikube start --cpus=2 --memory=4096
kubectl create namespace monitoring
```

### 2. Сборка и развертывание
```bash
# Переключение окружения на Docker Minikube
eval $(minikube docker-env)

# Сборка образа внутри кластера
docker build -t flyops-neuron:latest .

# Развертывание манифестов
kubectl apply -f k8s/ -n monitoring
```

### 3. Проверка статуса компонентов
```bash
kubectl get pods -n monitoring -l role=neuron
```

---

## Стек технологий
* **Среда исполнения:** Python 3.11 (`http.server`, `urllib`, `threading`)
* **Оркестрация и сеть:** Kubernetes (Deployments, Services, CoreDNS)
* **Сбор метрик:** Prometheus Client Python (`prometheus_client`)
* **Визуализация топологии:** Grafana (Node Graph API)
