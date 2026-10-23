"""三个阶段：三元组抽取 → 语义分析 → 语义网络抽取。

（事件检测 / 指代消解 / LLM 增强 / 校验 / 导出不在当前范围，待确认后再做。）
"""

from __future__ import annotations

import itertools
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from semantica.semantic_extract import (
    NERExtractor,
    RelationExtractor,
    SemanticNetworkExtractor,
    TripletExtractor,
)
from semantica.semantic_extract.semantic_network_extractor import (
    SemanticEdge,
    SemanticNetwork,
    SemanticNode,
)
from semantica.semantic_extract.types import Entity, Relation

from . import lexicon as lx
from .corpus import Doc, build_corpus
from .domain_model import DomainModel, build_domain_model
from .export_ontology import export_ontology
from .java_scanner import scan_module
from .zh_extract import MARK, ZH_NER, ZH_REL, ZhSemanticAnalyzer, register_methods, split_sentences

log = logging.getLogger("matkg")

BASIS_ZH = {"confirmed": "业务方确认", "code": "源码", "inferred": "推断（待确认）"}


# --------------------------------------------------------------------------- #
# 通用
# --------------------------------------------------------------------------- #


@dataclass
class Context:
    model: DomainModel
    docs: List[Doc]
    ner: NERExtractor
    rel: RelationExtractor

    def extract(self, doc: Doc) -> Tuple[List[Entity], List[Relation]]:
        """单个文档：NER → 关系。过滤掉框架的英文兜底结果（只保留中文方法产出）。"""
        ents = [e for e in self.ner.extract_entities(doc.text) if e.metadata.get(MARK) == ZH_NER]
        rels: List[Relation] = []
        if ents:
            rels = [r for r in self.rel.extract_relations(doc.text, ents) if r.metadata.get(MARK) == ZH_REL]
        return ents, rels


def prepare(java_root: str) -> Context:
    scan = scan_module(java_root)
    model = build_domain_model(scan)
    register_methods(model)
    docs = build_corpus(model)
    return Context(
        model=model,
        docs=docs,
        ner=NERExtractor(method=ZH_NER),
        rel=RelationExtractor(method=ZH_REL),
    )


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
# 阶段 1：三元组抽取
# --------------------------------------------------------------------------- #


def run_triplets(ctx: Context) -> List[Dict[str, Any]]:
    gaz = ctx.model.gazetteer
    extractor = TripletExtractor(method=ZH_REL, include_provenance=True, min_confidence=0.5)
    merged: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for doc in ctx.docs:
        ents, rels = ctx.extract(doc)
        if not rels:
            continue
        triplets = extractor.extract_triplets(doc.text, entities=ents, relations=rels)
        for t in triplets:
            if t.metadata.get(MARK) != ZH_REL:
                continue
            key = (t.subject, t.predicate, t.object)
            item = merged.setdefault(key, {
                "subject": t.subject,
                "predicate": t.predicate,
                "object": t.object,
                "subject_type": t.metadata.get("subject_type"),
                "object_type": t.metadata.get("object_type"),
                "confidence": t.confidence,
                "via": [],
                "basis": doc.meta.get("basis", "code"),
                "evidence": [],
            })
            doc_basis = doc.meta.get("basis", "code")  # 多份证据取最强的依据
            if lx.BASIS_RANK[doc_basis] > lx.BASIS_RANK[item["basis"]]:
                item["basis"] = doc_basis
            item["confidence"] = max(item["confidence"], t.confidence)
            for v in t.metadata.get("via", []):
                if v not in item["via"]:
                    item["via"].append(v)
            item["evidence"].append({"doc": doc.id, "source": doc.source, "sentence": t.metadata.get("sentence")})

    order = {p: i for i, p in enumerate(lx.PREDICATES)}
    out = sorted(merged.values(), key=lambda x: (order.get(x["predicate"], 99), x["subject"], x["object"]))
    return out


def write_triplets(out_dir: Path, triplets: List[Dict[str, Any]]) -> None:
    _dump(out_dir / "triplets.json", triplets)
    by_pred: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in triplets:
        by_pred[t["predicate"]].append(t)
    lines = [f"# 三元组抽取结果\n\n共 {len(triplets)} 条（去重后），{len(by_pred)} 种谓词。\n"]
    for pred, items in by_pred.items():
        pdef = lx.PREDICATES[pred]
        lines.append(f"\n## {pred}（{pdef.zh}）· {len(items)} 条\n")
        lines.append("| 主语 | 宾语 | 关联字段 | 依据 | 出处 |\n|---|---|---|---|---|")
        for t in items:
            via = "、".join(t["via"]) or ""
            src = t["evidence"][0]["source"] if t["evidence"] else ""
            basis = BASIS_ZH[t["basis"]]
            lines.append(f"| {t['subject']} | {t['object']} | {via} | {basis} | {src} |")
    sup = [t for t in triplets if t["predicate"] == "supports"]
    if sup:
        lines.append("\n## 按应用场景汇总\n")
        for name, desc in lx.SCENARIOS:
            lines.append(f"### {name}\n\n{desc}\n")
            for basis, title in (("confirmed", "业务方确认"), ("code", "源码有直接依据"), ("inferred", "根据字段含义推断（待确认）")):
                subs = [t["subject"] for t in sup if t["object"] == name and t["basis"] == basis]
                if subs:
                    lines.append(f"- {title}：{'、'.join(subs)}")
            lines.append("")
    (out_dir / "triplets.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# 阶段 2：语义分析
# --------------------------------------------------------------------------- #


def _entity_profiles(ctx: Context) -> Dict[str, str]:
    """每个实体的“语义画像”：所有提到该实体的句子拼起来。"""
    gaz = ctx.model.gazetteer
    profiles: Dict[str, List[str]] = {ctx.model.label(c): [] for c in ctx.model.entities}
    for doc in ctx.docs:
        for s, e in split_sentences(doc.text):
            sent = doc.text[s:e]
            canon = {t.canonical for _, _, t in gaz.find(sent) if t.label == "Entity"}
            for c in canon:
                if c in profiles:
                    profiles[c].append(sent)
    return {k: "".join(v) for k, v in profiles.items()}


def run_semantic_analysis(
    ctx: Context, sim_threshold: float = 0.5, cluster_threshold: float = 0.35
) -> Dict[str, Any]:
    analyzer = ZhSemanticAnalyzer(ctx.model)

    # 1) 每个文档：语义角色 + 特征
    per_doc: List[Dict[str, Any]] = []
    role_counter: Counter = Counter()
    for doc in ctx.docs:
        res = analyzer.analyze_semantics(doc.text, label_roles=True)
        roles = res.get("semantic_roles", [])
        role_counter.update(r["role"] for r in roles)
        per_doc.append({
            "doc": doc.id,
            "kind": doc.kind,
            "title": doc.title,
            "features": res["semantic_features"],
            "sentence_count": res["sentence_count"],
            "roles": [
                {
                    "sentence": r["metadata"].get("sentence_index"),
                    "role": r["role"],
                    "word": r["word"],
                    "canonical": r["metadata"].get("canonical"),
                    "concept": r["metadata"].get("concept"),
                    "predicate": r["metadata"].get("predicate"),
                }
                for r in roles
            ],
        })

    # 2) 实体两两相似度（语义画像的余弦相似度 + 关键字段 Jaccard）
    profiles = _entity_profiles(ctx)
    labels = list(profiles)
    key_sets = {ctx.model.label(c): set(ctx.model.key_field_labels(c)) for c in ctx.model.entities}
    pairs: List[Dict[str, Any]] = []
    for a, b in itertools.combinations(labels, 2):
        cos = analyzer.calculate_similarity(profiles[a], profiles[b], method="cosine")
        ka, kb = key_sets[a], key_sets[b]
        jac = len(ka & kb) / len(ka | kb) if ka | kb else 0.0
        pairs.append({
            "a": a, "b": b,
            "text_cosine": round(cos, 4),
            "key_field_jaccard": round(jac, 4),
            "shared_key_fields": sorted(ka & kb),
        })
    pairs.sort(key=lambda p: -p["text_cosine"])

    # 3) 聚类：实体画像
    ent_items = [{"id": k, "content": v} for k, v in profiles.items()]
    ent_clusters = analyzer.cluster_semantically(ent_items, similarity_threshold=cluster_threshold)

    def cl(clusters) -> List[Dict[str, Any]]:
        return [
            {
                "cluster_id": c.cluster_id,
                "members": c.metadata["doc_ids"],
                "avg_similarity": round(c.similarity_score, 4),
            }
            for c in clusters
        ]

    return {
        "params": {"similar_edge_threshold": sim_threshold, "cluster_threshold": cluster_threshold},
        "role_distribution": dict(role_counter),
        "documents": per_doc,
        "entity_similarity": pairs,
        # 语义画像足够相近，或关键字段几乎一致（如基础属性 / 私有属性同构），都算“语义相近”
        "similar_to": [p for p in pairs if p["text_cosine"] >= sim_threshold or p["key_field_jaccard"] >= 0.8],
        "entity_clusters": cl(ent_clusters),
    }


def write_semantic_analysis(out_dir: Path, result: Dict[str, Any]) -> None:
    _dump(out_dir / "semantic_analysis.json", result)
    L: List[str] = ["# 语义分析结果\n"]
    L.append("## 语义角色分布\n")
    L.append("| 角色 | 数量 |\n|---|---|")
    for r, n in sorted(result["role_distribution"].items(), key=lambda x: -x[1]):
        L.append(f"| {r} | {n} |")
    L.append("\n## 实体语义相似度（降序）\n")
    L.append("| 实体 A | 实体 B | 文本余弦 | 关键字段 Jaccard | 共享关键字段 |\n|---|---|---|---|---|")
    for p in result["entity_similarity"]:
        L.append(f"| {p['a']} | {p['b']} | {p['text_cosine']} | {p['key_field_jaccard']} | {'、'.join(p['shared_key_fields'])} |")
    L.append(f"\n## 实体聚类（阈值 {result['params']['cluster_threshold']}）\n")
    for c in result["entity_clusters"]:
        L.append(f"- 簇 {c['cluster_id']}：{'、'.join(c['members'])}（平均相似度 {c['avg_similarity']}）")
    L.append("\n## 文档级语义特征\n")
    L.append("| 文档 | 类型 | 提及数 | 唯一实体 | 角色标注数 |\n|---|---|---|---|---|")
    for d in result["documents"]:
        f = d["features"]
        L.append(f"| {d['doc']} | {d['kind']} | {f['mention_count']} | {f['unique_entities']} | {len(d['roles'])} |")
    (out_dir / "semantic_analysis.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# 阶段 3：语义网络抽取
# --------------------------------------------------------------------------- #


def _canonicalize(ctx: Context, ents: List[Entity], rels: List[Relation]) -> Tuple[List[Entity], List[Relation]]:
    """同一规范实体只保留一个节点（框架按 entity.text 建节点映射，重复词面会冲突）。"""
    gaz = ctx.model.gazetteer
    nodes: Dict[str, Entity] = {}
    for e in sorted(ents, key=lambda x: x.start_char):
        c = gaz.canonical_of(e.text)
        if c not in nodes:
            nodes[c] = Entity(text=c, label=e.label, start_char=e.start_char, end_char=e.end_char,
                              confidence=e.confidence, metadata={**e.metadata, "canonical": c})
    out_rels = []
    seen = set()
    for r in rels:
        s, o = gaz.canonical_of(r.subject.text), gaz.canonical_of(r.object.text)
        if (s, r.predicate, o) in seen:
            continue
        seen.add((s, r.predicate, o))
        out_rels.append(Relation(subject=nodes[s], predicate=r.predicate, object=nodes[o],
                                 confidence=r.confidence, context=r.context, metadata=r.metadata))
    return list(nodes.values()), out_rels


def run_semantic_network(ctx: Context, similar_to: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    extractor = SemanticNetworkExtractor(ner_method=ZH_NER, relation_method=ZH_REL)
    gnodes: Dict[str, SemanticNode] = {}
    gedges: Dict[Tuple[str, str, str], SemanticEdge] = {}
    doc_basis = {d.id: d.meta.get("basis", "code") for d in ctx.docs}

    def nid(label: str, canonical: str) -> str:
        return f"{label}:{canonical}"

    for doc in ctx.docs:
        ents, rels = ctx.extract(doc)
        if not ents:
            continue
        ents, rels = _canonicalize(ctx, ents, rels)
        net: SemanticNetwork = extractor.extract_network(doc.text, entities=ents, relations=rels)
        local = {n.id: n for n in net.nodes}
        for n in net.nodes:
            gid = nid(n.type, n.label)
            g = gnodes.setdefault(gid, SemanticNode(
                id=gid, label=n.label, type=n.type,
                properties={"docs": [], "source": n.metadata.get("source", "")}, metadata={},
            ))
            if doc.id not in g.properties["docs"]:
                g.properties["docs"].append(doc.id)
        for e in net.edges:
            s, t = local[e.source], local[e.target]
            key = (nid(s.type, s.label), e.label, nid(t.type, t.label))
            ge = gedges.setdefault(key, SemanticEdge(
                source=key[0], target=key[2], label=e.label,
                properties={"confidence": e.properties.get("confidence"), "docs": [], "via": []},
                metadata={"inferred": False},
            ))
            if doc.id not in ge.properties["docs"]:
                ge.properties["docs"].append(doc.id)
            b = doc_basis[doc.id]
            if lx.BASIS_RANK[b] > lx.BASIS_RANK.get(ge.metadata.get("basis", "inferred"), -1) or "basis" not in ge.metadata:
                ge.metadata["basis"] = b
            for v in e.metadata.get("via", []):
                if v not in ge.properties["via"]:
                    ge.properties["via"].append(v)

    # 语义分析推断出的 similarTo 边（标记 inferred，便于和文本抽取的边区分）
    for p in similar_to or []:
        a, b = nid("Entity", p["a"]), nid("Entity", p["b"])
        if a in gnodes and b in gnodes:
            gedges[(a, "similarTo", b)] = SemanticEdge(
                source=a, target=b, label="similarTo",
                properties={"confidence": p["text_cosine"], "docs": [], "via": p["shared_key_fields"]},
                metadata={"inferred": True, "basis": "inferred", "method": "profile_cosine|key_field_jaccard"},
            )

    network = SemanticNetwork(
        nodes=list(gnodes.values()),
        edges=list(gedges.values()),
        metadata={
            "node_count": len(gnodes),
            "edge_count": len(gedges),
            "entity_types": sorted({n.type for n in gnodes.values()}),
            "relation_types": sorted({e.label for e in gedges.values()}),
        },
    )
    stats = extractor.analyze_network(network)

    # 度数（出/入）
    deg_out, deg_in = Counter(), Counter()
    for e in network.edges:
        deg_out[e.source] += 1
        deg_in[e.target] += 1
    nodes_json = [
        {"id": n.id, "label": n.label, "type": n.type, "docs": n.properties["docs"],
         "out_degree": deg_out[n.id], "in_degree": deg_in[n.id]}
        for n in network.nodes
    ]
    edges_json = [
        {"source": e.source, "target": e.target, "label": e.label,
         "confidence": e.properties.get("confidence"), "via": e.properties.get("via"),
         "docs": e.properties.get("docs"), "inferred": e.metadata.get("inferred", False),
         "basis": e.metadata.get("basis", "code")}
        for e in network.edges
    ]
    return {"stats": stats, "nodes": nodes_json, "edges": edges_json}


def write_semantic_network(out_dir: Path, net: Dict[str, Any]) -> None:
    _dump(out_dir / "semantic_network.json", net)
    st = net["stats"]
    L = ["# 语义网络抽取结果\n"]
    L.append(f"- 节点 {st['node_count']}，边 {st['edge_count']}，平均度 {st['average_degree']:.2f}（{st['connectivity']}）")
    L.append("- 节点类型：" + "，".join(f"{k} {v}" for k, v in st["node_types"].items()))
    L.append("- 关系类型：" + "，".join(f"{k} {v}" for k, v in st["relation_types"].items()))

    def short(i: str) -> str:
        return i.split(":", 1)[1]

    ent_ids = {n["id"] for n in net["nodes"] if n["type"] == "Entity"}
    scen_ids = {n["id"] for n in net["nodes"] if n["type"] == "Scenario"}
    enum_ids = {n["id"] for n in net["nodes"] if n["type"] in ("EnumValue", "BusinessGroup")}
    names: Dict[str, str] = {}

    def node(i: str) -> str:
        if i not in names:
            names[i] = f"n{len(names)}"
        return names[i]

    def arrow(e: Dict[str, Any]) -> str:
        return "-.->" if (e["inferred"] or e["basis"] == "inferred") else "-->"

    L.append("\n## 实体级关系图（虚线 = 推断）\n")
    L.append("```mermaid\ngraph LR")
    for e in net["edges"]:
        s, t = e["source"], e["target"]
        if s in ent_ids and t in ent_ids:
            L.append(f'    {node(s)}["{short(s)}"] {arrow(e)}|{e["label"]}| {node(t)}["{short(t)}"]')
    L.append("```")

    L.append("\n## 枚举值与优选BG\n")
    L.append("```mermaid\ngraph LR")
    for e in net["edges"]:
        s, t = e["source"], e["target"]
        if t in enum_ids and e["label"] == "preferredFor":
            L.append(f'    {node(s)}["{short(s)}"] --> {node(t)}["{short(t)}"]')
    L.append("```")

    L.append("\n## 应用场景图（谁支持哪个场景；虚线 = 根据字段含义推断，待确认）\n")
    L.append("```mermaid\ngraph LR")
    for e in net["edges"]:
        s, t = e["source"], e["target"]
        if t in scen_ids:
            L.append(f'    {node(s)}["{short(s)}"] {arrow(e)} {node(t)}["{short(t)}"]')
    L.append("```")

    L.append("\n## 节点\n")
    L.append("| 类型 | 节点 | 出度 | 入度 | 出现文档数 |\n|---|---|---|---|---|")
    for n in sorted(net["nodes"], key=lambda x: (x["type"], x["label"])):
        L.append(f"| {n['type']} | {n['label']} | {n['out_degree']} | {n['in_degree']} | {len(n['docs'])} |")
    L.append("\n## 边\n")
    L.append("| 起点 | 关系 | 终点 | 关联字段 | 依据 |\n|---|---|---|---|---|")
    for e in net["edges"]:
        basis = "语义分析推断" if e["inferred"] else BASIS_ZH[e["basis"]]
        L.append(f"| {short(e['source'])} | {e['label']} | {short(e['target'])} | {'、'.join(e['via'] or [])} | {basis} |")
    (out_dir / "semantic_network.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def write_corpus(out_dir: Path, docs: List[Doc]) -> None:
    L = ["# 抽取语料（由 Java 源码整理）\n"]
    for d in docs:
        L.append(f"\n## {d.id}\n\n- 类型：{d.kind}\n- 出处：{d.source}\n\n{d.text}\n")
    (out_dir / "corpus.md").write_text("\n".join(L), encoding="utf-8")
    _dump(out_dir / "corpus.json", [d.__dict__ for d in docs])


def write_glossary(out_dir: Path, model: DomainModel) -> None:
    """业务口径对照表：实体 / 常用属性 / 规则 / 应用场景。"""
    rows = []
    for cls, ent in model.entities.items():
        rows.append({
            "canonical": model.label(cls),
            "tech_name": model.tech_names[cls],
            "java_class": cls,
            "table": ent.table,
            "aliases": model.aliases.get(cls, []),
            "business_desc": lx.ENTITY_BUSINESS_DESC[cls],
            "confirmed_by_user": True,  # 前三项业务方直接给出，其余五项“同理”推出后已确认
        })
    attrs = [
        {"canonical": a.label, "attr_code": a.code, "desc": a.desc, "derives_from": a.derives_from, "source": a.source}
        for a in lx.COMMON_ATTRS
    ]
    rules = [{"name": r.name, "text": r.text, "source": r.source, "basis": r.basis} for r in lx.RULES]
    enums = [
        {"owner": g.owner, "value": g.label(v), "code": v.code, "name": v.name, "desc": v.desc, "bg": v.bg}
        for g in lx.ENUM_GROUPS for v in g.values
    ]
    scenarios = [{"name": n, "desc": d} for n, d in lx.SCENARIOS]
    _dump(out_dir / "glossary.json", {
        "entities": rows, "common_attributes": attrs, "enum_values": enums, "business_groups": lx.BUSINESS_GROUPS,
        "rules": rules, "scenarios": scenarios,
    })

    L = ["# 业务口径对照表\n", "## 实体\n",
         "| 规范名（节点名） | 源码叫法 | Java 类 | 表 | 别名 | 业务口径 | 来源 |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        src = "业务方确认" if r["confirmed_by_user"] else "待确认"
        L.append(f"| {r['canonical']} | {r['tech_name']} | {r['java_class']} | {r['table']} | {'、'.join(r['aliases'])} | {r['business_desc']} | {src} |")
    L += ["\n## 物料基础属性里的常用属性\n", "| 规范名 | attr_code | 说明 | 取自 | 出处 |", "|---|---|---|---|---|"]
    for a in attrs:
        L.append(f"| {a['canonical']} | {a['attr_code']} | {a['desc']} | {a['derives_from'] or ''} | {a['source']} |")
    L += ["\n## 枚举值\n", "| 所属 | 节点名 | 编码 | 说明 | 优选所属BG |", "|---|---|---|---|---|"]
    for en in enums:
        L.append(f"| {en['owner']} | {en['value']} | {en['code']} | {en['desc']} | {en['bg'] or ''} |")
    L += ["\n## 业务规则\n", "| 规则 | 内容 | 依据 | 出处 |", "|---|---|---|---|"]
    for r in rules:
        L.append(f"| {r['name']} | {r['text']} | {BASIS_ZH[r['basis']]} | {r['source']} |")
    L += ["\n## 应用场景\n", "| 场景 | 说明 |", "|---|---|"]
    for sc in scenarios:
        L.append(f"| {sc['name']} | {sc['desc']} |")
    (out_dir / "glossary.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def write_confirmation_list(out_dir: Path, model: DomainModel) -> None:
    """需要业务方确认的内容（推断出来的支撑关系 / 实体关系）；全部确认后只留一份说明。"""
    pending_sup = [s for s in lx.SUPPORTS if s.basis == "inferred"]
    pending_rel = [r for r in lx.ENTITY_RELATIONS if r.basis == "inferred"]
    L = ["# 待业务方确认清单\n"]
    if not pending_sup and not pending_rel:
        L.append("当前没有待确认项：应用场景支撑关系、实体关系、8 个实体的业务名均已由业务方确认。")
        (out_dir / "to_confirm.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        return
    L.append("在“确认”列填 是 / 否 即可；标“否”的条目将从 lexicon 中删除。\n")
    if pending_sup:
        L.append(f"## 推断出来的应用场景支撑关系（{len(pending_sup)} 条）\n")
        L.append("| # | 主语 | 支持的场景 | 推断理由 | 参考出处 | 确认 |\n|---|---|---|---|---|---|")
        for i, sp in enumerate(sorted(pending_sup, key=lambda x: (x.scenario, x.subject)), 1):
            L.append(f"| {i} | {model.node_label(sp.subject)} | {sp.scenario} | {sp.reason} | {sp.source} | |")
    if pending_rel:
        L.append(f"\n## 推断出来的实体关系（{len(pending_rel)} 条）\n")
        L.append("| 起点 | 关系 | 终点 | 关联字段 | 理由 | 确认 |\n|---|---|---|---|---|---|")
        for r in pending_rel:
            L.append(f"| {model.label(r.src)} | {r.predicate} | {model.label(r.dst)} | {'、'.join(r.via)} | {r.source} | |")
    (out_dir / "to_confirm.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def run_all(java_root: str, out_dir: str) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ctx = prepare(java_root)
    write_glossary(out, ctx.model)
    write_confirmation_list(out, ctx.model)
    write_corpus(out, ctx.docs)

    triplets = run_triplets(ctx)
    write_triplets(out, triplets)

    analysis = run_semantic_analysis(ctx)
    write_semantic_analysis(out, analysis)

    network = run_semantic_network(ctx, similar_to=analysis["similar_to"])
    write_semantic_network(out, network)

    onto_stats = export_ontology(ctx.model, triplets, network, out)

    summary = {
        "docs": len(ctx.docs),
        "gazetteer_terms": len(ctx.model.gazetteer),
        "triplets": len(triplets),
        "predicates": dict(Counter(t["predicate"] for t in triplets)),
        "network_nodes": len(network["nodes"]),
        "network_edges": len(network["edges"]),
        "ontology": onto_stats,
    }
    _dump(out / "run_summary.json", summary)
    return summary
