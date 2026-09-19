import json
import time
import random
import threading
from prometheus_client import start_http_server, Counter, Gauge

# 1. Загрузка графа
with open('topology.json', 'r', encoding='utf-8') as f:
    topo = json.load(f)

nodes = topo['nodes']
edges = topo['edges']

# 2. Метрики с точными лейблами для Grafana Node Graph
EDGE_SPIKES = Counter(
    'flyops_edge_spikes_total',
    'Spikes transmitted over connectome edge',
    ['id', 'source', 'target']
)

NODE_SPIKES = Counter(
    'flyops_node_spikes_total',
    'Spikes processed by neuron',
    ['id', 'title', 'subtitle']
)

NODE_STATUS = Gauge(
    'flyops_node_status',
    'Neuron operational status: 1 active, 0 degraded',
    ['id']
)

# 3. Предварительный прогрев нулями всех узлов и ребер
for n in nodes:
    n_id = n['id']
    layer = n.get('layer', 'Processing')
    NODE_SPIKES.labels(id=n_id, title=n_id, subtitle=layer).inc(0)
    NODE_STATUS.labels(id=n_id).set(1)

for e in edges:
    src = e['source']
    tgt = e['target']
    edge_id = f"{src}--{tgt}"
    EDGE_SPIKES.labels(id=edge_id, source=src, target=tgt).inc(0)


# 4. Логика симуляции импульсов
def run_simulation():
    targets_set = {e['target'] for e in edges}
    roots = [n['id'] for n in nodes if n['id'] not in targets_set]
    if not roots:
        roots = [nodes[0]['id']]

    # Карта для быстрого поиска слоев
    layer_map = {n['id']: n.get('layer', 'Processing') for n in nodes}

    while True:
        # Старт от одного из входных сенсорных нейронов
        source = random.choice(roots)
        NODE_SPIKES.labels(id=source, title=source, subtitle=layer_map[source]).inc()

        current = [source]
        while current:
            next_layer = []
            for curr_node in current:
                out_edges = [e for e in edges if e['source'] == curr_node]
                for e in out_edges:
                    src = e['source']
                    tgt = e['target']
                    weight = e.get('weight', 500)

                    # Вероятность проведения импульса зависит от веса синапса
                    prob = min(0.95, weight / 1500)
                    if random.random() < prob:
                        edge_id = f"{src}--{tgt}"
                        EDGE_SPIKES.labels(id=edge_id, source=src, target=tgt).inc()
                        NODE_SPIKES.labels(id=tgt, title=tgt, subtitle=layer_map[tgt]).inc()
                        next_layer.append(tgt)
            current = list(set(next_layer))
            time.sleep(0.1)

        time.sleep(random.uniform(0.3, 0.8))


if __name__ == '__main__':
    start_http_server(8000)
    print("FlyOps Simulator metrics exposed on :8000/metrics")
    sim_thread = threading.Thread(target=run_simulation, daemon=True)
    sim_thread.start()

    while True:
        time.sleep(1)