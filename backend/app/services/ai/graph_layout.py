import math
from collections import Counter

import networkx as nx


def _empty_graph() -> dict:
    return {"nodes": [], "edges": []}


def layout_graph(nodes: list[dict], edges: list[dict]) -> dict:
    if not nodes:
        return _empty_graph()

    graph = nx.Graph()
    for node in nodes:
        graph.add_node(node["id"])
    for edge in edges:
        if edge["source"] in graph and edge["target"] in graph:
            graph.add_edge(edge["source"], edge["target"])

    if graph.number_of_edges() == 0:
        count = max(len(nodes), 1)
        positions = {
            node["id"]: (
                0.5 + 0.35 * math.cos((2 * math.pi * index) / count),
                0.5 + 0.35 * math.sin((2 * math.pi * index) / count),
            )
            for index, node in enumerate(nodes)
        }
    else:
        raw_positions = nx.spring_layout(graph, seed=42, k=0.65, iterations=80)
        xs = [pos[0] for pos in raw_positions.values()]
        ys = [pos[1] for pos in raw_positions.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 0.001)
        span_y = max(max_y - min_y, 0.001)
        positions = {
            node_id: (
                0.08 + ((pos[0] - min_x) / span_x) * 0.84,
                0.08 + ((pos[1] - min_y) / span_y) * 0.84,
            )
            for node_id, pos in raw_positions.items()
        }

    centrality = nx.degree_centrality(graph) if graph.number_of_nodes() else {}
    positioned_nodes = []
    for node in nodes:
        x, y = positions.get(node["id"], (0.5, 0.5))
        positioned_nodes.append({
            **node,
            "x": round(float(x), 4),
            "y": round(float(y), 4),
            "centrality": round(float(centrality.get(node["id"], 0.0)), 4),
        })

    return {"nodes": positioned_nodes, "edges": edges}


def graph_summary(nodes: list[dict], edges: list[dict]) -> dict:
    graph = nx.Graph()
    for node in nodes:
        graph.add_node(node["id"], **node)
    for edge in edges:
        if edge["source"] in graph and edge["target"] in graph:
            graph.add_edge(edge["source"], edge["target"], type=edge.get("type"))

    centrality = nx.degree_centrality(graph) if graph.number_of_nodes() else {}
    concepts = [
        {
            "id": node_id,
            "label": data.get("label", ""),
            "centrality": round(float(centrality.get(node_id, 0.0)), 4),
        }
        for node_id, data in graph.nodes(data=True)
        if data.get("type") == "concept"
    ]
    concepts.sort(key=lambda item: item["centrality"], reverse=True)

    components = list(nx.connected_components(graph)) if graph.number_of_nodes() else []
    type_counts = Counter(node.get("type", "unknown") for node in nodes)

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "paper_count": type_counts.get("paper", 0),
        "concept_count": type_counts.get("concept", 0),
        "author_count": type_counts.get("author", 0),
        "research_thread_count": len(components),
        "density": round(float(nx.density(graph)), 4) if graph.number_of_nodes() > 1 else 0.0,
        "top_concepts": concepts[:5],
    }
