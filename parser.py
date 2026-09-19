import json
import pandas as pd

print("1. Читаем коннектом...")
df_conn = pd.read_csv(
    'connections_princeton.csv',
    usecols=['pre_root_id', 'post_root_id', 'syn_count']
)

# Фильтруем шум: берем связи с достаточным весом
df_strong = df_conn[df_conn['syn_count'] >= 50]

# Берем самый активный узел-источник как стартовую точку
start_node = df_strong['pre_root_id'].value_counts().index[0]

# Собираем цепочку в 3 шага (hops)
selected_nodes = {start_node}
chain_edges = []

current_layer = [start_node]
for step in range(3):
    # Ищем, куда идут сигналы от текущего слоя
    next_hops = df_strong[df_strong['pre_root_id'].isin(current_layer)]
    top_hops = next_hops.sort_values(by='syn_count', ascending=False).head(8)

    if top_hops.empty:
        break

    for _, row in top_hops.iterrows():
        chain_edges.append(row)
        selected_nodes.add(row['post_root_id'])

    current_layer = list(top_hops['post_root_id'].unique())

# Добавляем альтернативные/обходные связи между уже отобранными узлами
extra_edges = df_strong[
    df_strong['pre_root_id'].isin(selected_nodes) &
    df_strong['post_root_id'].isin(selected_nodes)
    ].sort_values(by='syn_count', ascending=False).head(20)

all_edges_df = pd.concat([pd.DataFrame(chain_edges), extra_edges]).drop_duplicates(
    subset=['pre_root_id', 'post_root_id'])

print(f"Отобрано узлов в контуре: {len(selected_nodes)}, связей: {len(all_edges_df)}")

# 2. Формируем граф
nodes = [{"id": f"neuron-{str(n)[-4:]}", "full_id": str(n)} for n in selected_nodes]
edges = [
    {
        "source": f"neuron-{str(r['pre_root_id'])[-4:]}",
        "target": f"neuron-{str(r['post_root_id'])[-4:]}",
        "weight": int(r['syn_count'])
    }
    for _, r in all_edges_df.iterrows()
]

topology = {"nodes": nodes, "edges": edges}

with open('topology.json', 'w', encoding='utf-8') as f:
    json.dump(topology, f, indent=2, ensure_ascii=False)

print("Готово! topology.json обновлен.")