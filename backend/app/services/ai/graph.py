import logging
import re

from neo4j import GraphDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)

RELATIONSHIP_TYPES = {"INTRODUCES", "USES", "RELATED_TO", "WRITTEN_BY"}


def _driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def _key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _relationship_type(value: str | None) -> str:
    rel_type = (value or "RELATED_TO").upper()
    return rel_type if rel_type in RELATIONSHIP_TYPES else "RELATED_TO"


def write_paper_graph(
    *,
    user_id: str,
    paper_id: str,
    title: str,
    authors: list[str],
    concepts: list[dict],
    relationships: list[dict],
) -> None:
    if not concepts and not authors:
        return

    with _driver() as driver:
        with driver.session() as session:
            session.execute_write(
                _write_paper_graph_tx,
                user_id,
                paper_id,
                title,
                authors,
                concepts,
                relationships,
            )


def _write_paper_graph_tx(tx, user_id, paper_id, title, authors, concepts, relationships):
    tx.run(
        """
        MERGE (p:Paper {user_id: $user_id, id: $paper_id})
        SET p.title = $title
        """,
        user_id=user_id,
        paper_id=paper_id,
        title=title,
    )

    for author in authors:
        if not author.strip():
            continue
        tx.run(
            """
            MERGE (a:Author {user_id: $user_id, name_key: $name_key})
            SET a.name = $name
            WITH a
            MATCH (p:Paper {user_id: $user_id, id: $paper_id})
            MERGE (p)-[:WRITTEN_BY]->(a)
            """,
            user_id=user_id,
            paper_id=paper_id,
            name_key=_key(author),
            name=author.strip(),
        )

    for concept in concepts:
        name = str(concept.get("name", "")).strip()
        if not name:
            continue
        category = str(concept.get("category", "uses")).lower()
        rel_type = "INTRODUCES" if category in {"introduced", "contribution", "method"} else "USES"
        tx.run(
            f"""
            MERGE (c:Concept {{user_id: $user_id, name_key: $name_key}})
            SET c.name = $name,
                c.category = $category
            WITH c
            MATCH (p:Paper {{user_id: $user_id, id: $paper_id}})
            MERGE (p)-[:{rel_type}]->(c)
            """,
            user_id=user_id,
            paper_id=paper_id,
            name_key=_key(name),
            name=name,
            category=category,
        )

    for relationship in relationships:
        source = str(relationship.get("source", "")).strip()
        target = str(relationship.get("target", "")).strip()
        if not source or not target or _key(source) == _key(target):
            continue
        rel_type = _relationship_type(relationship.get("type"))
        tx.run(
            f"""
            MATCH (a:Concept {{user_id: $user_id, name_key: $source_key}})
            MATCH (b:Concept {{user_id: $user_id, name_key: $target_key}})
            MERGE (a)-[:{rel_type}]->(b)
            """,
            user_id=user_id,
            source_key=_key(source),
            target_key=_key(target),
        )


def get_paper_graph(user_id: str, paper_id: str) -> dict:
    with _driver() as driver:
        with driver.session() as session:
            result = session.execute_read(_get_paper_graph_tx, user_id, paper_id)
    return result


def _get_paper_graph_tx(tx, user_id: str, paper_id: str) -> dict:
    records = tx.run(
        """
        MATCH (p:Paper {user_id: $user_id, id: $paper_id})
        OPTIONAL MATCH (p)-[r]->(n)
        WHERE n:Concept OR n:Author
        RETURN p, collect({rel: type(r), node: n}) AS neighbors
        """,
        user_id=user_id,
        paper_id=paper_id,
    ).single()

    if not records:
        return {"nodes": [], "edges": []}

    paper = records["p"]
    nodes = [_node("paper", paper["id"], paper.get("title", "Untitled"))]
    edges = []
    seen_nodes = {paper["id"]}
    for item in records["neighbors"]:
        node = item.get("node")
        rel = item.get("rel")
        if not node or not rel:
            continue
        node_type = "author" if "Author" in node.labels else "concept"
        node_id = f"{node_type}:{node.get('name_key')}"
        if node_id not in seen_nodes:
            nodes.append(_node(node_type, node_id, node.get("name", "")))
            seen_nodes.add(node_id)
        edges.append(_edge(paper["id"], node_id, rel))

    return {"nodes": nodes, "edges": _dedupe_edges(edges)}


def get_knowledge_map(user_id: str, limit: int = 200) -> dict:
    with _driver() as driver:
        with driver.session() as session:
            return session.execute_read(_get_knowledge_map_tx, user_id, limit)


def _get_knowledge_map_tx(tx, user_id: str, limit: int) -> dict:
    records = tx.run(
        """
        MATCH (p:Paper {user_id: $user_id})-[r]->(n)
        WHERE n:Concept OR n:Author
        RETURN p, r, n
        LIMIT $limit
        """,
        user_id=user_id,
        limit=limit,
    )

    nodes_by_id = {}
    edges = []
    for record in records:
        paper = record["p"]
        target = record["n"]
        rel = record["r"]
        paper_id = paper["id"]
        nodes_by_id[paper_id] = _node("paper", paper_id, paper.get("title", "Untitled"))
        target_type = "author" if "Author" in target.labels else "concept"
        target_id = f"{target_type}:{target.get('name_key')}"
        nodes_by_id[target_id] = _node(target_type, target_id, target.get("name", ""))
        edges.append(_edge(paper_id, target_id, rel.type))

    concept_records = tx.run(
        """
        MATCH (a:Concept {user_id: $user_id})-[r:RELATED_TO|USES|INTRODUCES]->(b:Concept {user_id: $user_id})
        RETURN a, r, b
        LIMIT $limit
        """,
        user_id=user_id,
        limit=limit,
    )
    for record in concept_records:
        source = record["a"]
        target = record["b"]
        source_id = f"concept:{source.get('name_key')}"
        target_id = f"concept:{target.get('name_key')}"
        nodes_by_id[source_id] = _node("concept", source_id, source.get("name", ""))
        nodes_by_id[target_id] = _node("concept", target_id, target.get("name", ""))
        edges.append(_edge(source_id, target_id, record["r"].type))

    return {"nodes": list(nodes_by_id.values()), "edges": _dedupe_edges(edges)}


def _node(node_type: str, node_id: str, label: str) -> dict:
    return {"id": node_id, "type": node_type, "label": label or "Untitled"}


def _edge(source: str, target: str, rel_type: str) -> dict:
    return {"id": f"{source}->{target}:{rel_type}", "source": source, "target": target, "type": rel_type}


def _dedupe_edges(edges: list[dict]) -> list[dict]:
    return list({edge["id"]: edge for edge in edges}.values())
