import json

def to_k8s_name(nid: str) -> str:
    return nid.lower().replace("_", "-")

with open('topology.json', 'r', encoding='utf-8') as f:
    topo = json.load(f)

manifests = []

for n in topo['nodes']:
    nid = n['id']
    kname = to_k8s_name(nid)
    layer = n.get('layer', 'Processing')

    item = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {kname}
  labels:
    app: {kname}
    role: neuron
    layer: {layer.lower()}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {kname}
  template:
    metadata:
      labels:
        app: {kname}
        role: neuron
        layer: {layer.lower()}
    spec:
      containers:
      - name: neuron
        image: flyops-neuron:latest
        imagePullPolicy: Never
        env:
        - name: NODE_ID
          value: "{nid}"
        ports:
        - name: http
          containerPort: 8000
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 2
          periodSeconds: 4
        resources:
          requests:
            cpu: 10m
            memory: 20Mi
          limits:
            cpu: 50m
            memory: 40Mi
---
apiVersion: v1
kind: Service
metadata:
  name: {kname}
  labels:
    app: {kname}
    role: neuron
spec:
  selector:
    app: {kname}
  ports:
  - name: http
    port: 8000
    targetPort: 8000
---"""
    manifests.append(item)

# Единый ServiceMonitor, который отслеживает все 19 подов по метке role: neuron
monitor = """apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: flyops-neurons-monitor
  labels:
    release: monitoring-stack
spec:
  selector:
    matchLabels:
      role: neuron
  endpoints:
  - port: http
    interval: 5s
    path: /metrics
"""
manifests.append(monitor)

with open('k8s.yaml', 'w', encoding='utf-8') as f:
    f.write("\n".join(manifests))

print("Успешно сгенерирован k8s.yaml для 19 микросервисов-нейронов!")
