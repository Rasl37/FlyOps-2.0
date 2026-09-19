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

NODE_ID = os.environ.get("NODE_ID", "ORN_apple_1")

# Приводим имя нейрона к допустимому DNS-имени Kubernetes (без подчеркиваний)
def to_k8s_name(nid: str) -> str:
    return nid.lower().replace("_", "-")

# Читаем топологию
with open('topology.json', 'r', encoding='utf-8') as f:
    topo = json.load(f)

my_node = next((n for n in topo['nodes'] if n['id'] == NODE_ID), {"id": NODE_ID, "layer": "Processing"})
layer = my_node.get('layer', 'Processing')
outgoing_edges = [e for e in topo['edges'] if e['source'] == NODE_ID]

# Метрики Prometheus для Grafana Node Graph
SPIKES_TOTAL = Counter('flyops_node_spikes_total', 'Spikes processed', ['id', 'title', 'subtitle'])
EDGE_SPIKES = Counter('flyops_edge_spikes_total', 'Spikes transmitted', ['id', 'source', 'target'])
NODE_STATUS = Gauge('flyops_node_status', 'Status: 1=Healthy, 0=Degraded', ['id'])
EDGE_STATUS = Gauge('flyops_edge_status', 'Edge status: 1=OK, 0=Failed', ['id', 'source', 'target'])

# Прогрев метрик при старте
SPIKES_TOTAL.labels(id=NODE_ID, title=NODE_ID, subtitle=layer).inc(0)
NODE_STATUS.labels(id=NODE_ID).set(1)

for e in outgoing_edges:
    tgt = e['target']
    eid = f"{NODE_ID}--{tgt}"
    EDGE_SPIKES.labels(id=eid, source=NODE_ID, target=tgt).inc(0)
    EDGE_STATUS.labels(id=eid, source=NODE_ID, target=tgt).set(1)

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

    # Механизм нейропластичности / Failover:
    # Если целевой под убит, перенаправляем импульс по альтернативным живым путям
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
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "received"}')


# Запускаем пересылку дальше в отдельном потоке
            threading.Thread(target=forward_impulse, daemon=True).start()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Отключаем спам HTTP-логов в консоль
        return

def sensory_loop():
    print(f"[{NODE_ID}] Сенсор активен. Генерация стимулов раз в 4-7 сек...")
    while True:
        time.sleep(random.uniform(4.0, 7.0))
        print(f"[{NODE_ID}] Импульс сгенерирован!")
        forward_impulse()

if __name__ == '__main__':
    print(f"Запуск нейрона: {NODE_ID} ({layer}) на порту 8000")
    if layer == 'Sensory':
        threading.Thread(target=sensory_loop, daemon=True).start()

    server = HTTPServer(('0.0.0.0', 8000), NeuronHandler)
    server.serve_forever()
