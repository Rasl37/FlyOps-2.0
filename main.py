import os
import sys
import json
import time
import random
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# ID текущего нейрона из env пода
NODE_ID = os.environ.get("NODE_ID", "neuron-4490")

def to_k8s_name(nid: str) -> str:
    """Приводит идентификатор нейрона к валидному DNS-имени Kubernetes."""
    return nid.lower().replace("_", "-")

# 1. Загрузка топологии
with open('topology.json', 'r', encoding='utf-8') as f:
    topo = json.load(f)

# 2. Автоматическое определение биологического слоя
all_sources = {e['source'] for e in topo['edges']}
all_targets = {e['target'] for e in topo['edges']}

if NODE_ID not in all_targets:
    layer = "Sensory"       # Входной рецептор (нет входящих связей)
elif NODE_ID not in all_sources:
    layer = "Motor"         # Исполнительный узел (нет исходящих связей)
else:
    layer = "Processing"    # Промежуточный узел обработки

outgoing_edges = [e for e in topo['edges'] if e['source'] == NODE_ID]

# 3. Метрики Prometheus
SPIKES_TOTAL = Counter(
    'flyops_node_spikes_total',
    'Total spikes processed by this neuron',
    ['id', 'title', 'subtitle']
)
EDGE_SPIKES = Counter(
    'flyops_edge_spikes_total',
    'Spikes transmitted across connectome edge',
    ['id', 'source', 'target']
)
NODE_STATUS = Gauge(
    'flyops_node_status',
    'Operational status: 1 Healthy, 0 Degraded',
    ['id']
)
EDGE_STATUS = Gauge(
    'flyops_edge_status',
    'Synaptic connection status: 1 OK, 0 Failed',
    ['id', 'source', 'target']
)

# Прогрев метрик
SPIKES_TOTAL.labels(id=NODE_ID, title=NODE_ID, subtitle=layer).inc(0)
NODE_STATUS.labels(id=NODE_ID).set(1)

for e in outgoing_edges:
    tgt = e['target']
    eid = f"{NODE_ID}--{tgt}"
    EDGE_SPIKES.labels(id=eid, source=NODE_ID, target=tgt).inc(0)
    EDGE_STATUS.labels(id=eid, source=NODE_ID, target=tgt).set(1)

# 4. Защита от шторма запросов (Биологический рефрактерный период)
LAST_SPIKE_TIME = 0.0
REFRACTORY_PERIOD = 0.4  # Минимальный интервал между спайками — 400 мс
spike_lock = threading.Lock()

# 5. Передача спайка по исходящим синапсам
def forward_impulse():
    SPIKES_TOTAL.labels(id=NODE_ID, title=NODE_ID, subtitle=layer).inc()
    if not outgoing_edges:
        return

    failed_edges = []
    success_count = 0

    for e in outgoing_edges:
        tgt = e['target']
        eid = f"{NODE_ID}--{tgt}"
        k8s_host = to_k8s_name(tgt)
        url = f"http://{k8s_host}:8000/fire"

        try:
            req = urllib.request.Request(
                url,
                data=b'{"impulse": 1}',
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    EDGE_SPIKES.labels(id=eid, source=NODE_ID, target=tgt).inc()
                    EDGE_STATUS.labels(id=eid, source=NODE_ID, target=tgt).set(1)
                    success_count += 1
        except Exception as err:
            print(f"[{NODE_ID}] Ошибка синапса к {tgt} ({k8s_host}): {err}")
            EDGE_STATUS.labels(id=eid, source=NODE_ID, target=tgt).set(0)
            failed_edges.append(e)

    # Failover / Нейропластичность: перенаправление на живые синапсы
    if failed_edges and success_count > 0:
        print(f"[{NODE_ID}] Резервный путь активирован: перенаправление импульса в обход сбоя!")
        for e in outgoing_edges:
            if e not in failed_edges:
                tgt = e['target']
                eid = f"{NODE_ID}--{tgt}"
                EDGE_SPIKES.labels(id=eid, source=NODE_ID, target=tgt).inc()

    if outgoing_edges and success_count == 0:
        NODE_STATUS.labels(id=NODE_ID).set(0)
    else:
        NODE_STATUS.labels(id=NODE_ID).set(1)

def handle_incoming_fire():
    """Фильтрует входящие спайки, отсекая эхо-запросы из биологических петел


ь."""
    global LAST_SPIKE_TIME
    with spike_lock:
        now = time.time()
        if now - LAST_SPIKE_TIME < REFRACTORY_PERIOD:
            return
        LAST_SPIKE_TIME = now
    forward_impulse()

# 6. HTTP Сервер
class NeuronHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/healthz':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        elif self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/fire':
            # Сразу закрываем HTTP 200, глуша обрывы сокетов
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "received"}')
            except (BrokenPipeError, ConnectionResetError):
                pass

            threading.Thread(target=handle_incoming_fire, daemon=True).start()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return

def sensory_loop():
    print(f"[{NODE_ID}] Входной сенсор запущен. Период стимуляции: 4-6 сек")
    while True:
        time.sleep(random.uniform(4.0, 6.0))
        print(f"[{NODE_ID}] Импульс сгенерирован!")
        forward_impulse()

if __name__ == '__main__':
    print(f"Запуск нейрона {NODE_ID} (Слой: {layer}) на порту 8000")

    if layer == "Sensory":
        print(f"[{NODE_ID}] Корневой узел топологии. Запуск генератора импульсов.")
        threading.Thread(target=sensory_loop, daemon=True).start()

    server = HTTPServer(('0.0.0.0', 8000), NeuronHandler)
    server.serve_forever()
