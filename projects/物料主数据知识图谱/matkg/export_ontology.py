"""导出本体：``ontology.ttl``（OWL / Turtle）和 ``ontology.json``。

内容（两个文件语义一致）：

* 类（TBox）：lexicon.CONCEPTS
* 对象属性：lexicon.PREDICATES（domain / range 多于一个类时用 ``owl:unionOf``）
* 个体（ABox）：语义网络里的节点（实体、字段、常用属性、枚举值、规则、场景 …）
* 推理路径：场景下沿图谱走的边（JSON 里是结构化的 ``reasoning_paths``，Turtle 里是场景个体的 ``skos:scopeNote``）
* 三元组：每条三元组直接写成 ``个体 属性 个体``；依据（confirmed / code / analysis）、
  关联字段、出处用 ``owl:Axiom`` 标注在三元组上（Turtle），JSON 里则直接挂在三元组上。

说明：Semantica 自带的 ``OWLExporter`` 只导出类 / 属性，且多 domain 会被当作交集；
这里需要把个体和三元组一起导出，并保证 domain / range 的并集语义，所以用 rdflib 直接生成。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

from . import lexicon as lx
from .domain_model import DomainModel

BASE = "https://terra.szhittech.com/ontology/material-master#"
MK = Namespace(BASE)
VERSION = "1.0"
NAME = "物料主数据知识图谱本体"
DESCRIPTION = (
    "和而泰物料主数据本体：描述物料主数据、基础属性、私有属性、分类、属性定义、分类属性模板、属性值库、"
    "编码号段之间的结构，以及常用属性、枚举值、业务规则和应用场景（物料精确查找、物料相似查找、替代料推荐）。"
)

CLASS_DESC = {
    "Entity": "物料主数据体系里的业务实体（对应一个 Java 实体 / 一张表）。",
    "DataTable": "数据库表。",
    "Field": "业务实体的字段。",
    "Dictionary": "字段使用的数据字典。",
    "CommonAttribute": "物料基础属性里常用的属性（以 attr_code 区分）。",
    "BusinessRule": "影响数据存储与查找的业务规则。",
    "Scenario": "图谱服务的应用场景。",
    "EnumValue": "字段或属性的枚举取值。",
    "BusinessGroup": "业务群（BG）。",
}

PREDICATE_DESC = {
    "mapsToTable": "业务实体对应的数据表。",
    "hasKeyField": "业务实体的关键字段。",
    "refersTo": "业务实体引用另一个业务实体（关联字段见三元组标注 via）。",
    "partOf": "业务实体从属于另一个业务实体（关联字段见三元组标注 via）。",
    "usesDictionary": "字段使用的数据字典。",
    "includesAttribute": "物料基础属性包含的常用属性。",
    "hasCoreAttribute": "物料基础属性的核心属性（业务方特别强调：识别、查找物料最重要的属性）。",
    "derivesFrom": "常用属性的默认取值来源字段。",
    "governedBy": "业务实体受业务规则约束。",
    "supports": "实体 / 字段 / 常用属性支持某个应用场景。",
    "hasValue": "字段或常用属性的枚举取值。",
    "preferredFor": "优选标识的枚举值标明哪个 BG 的优选物料。",
    "indicatesBG": "字段标明物料所属的 BG。",
    "similarTo": "语义相近（由语义分析推断，对称）。",
}

# 个体上的数据属性：名称 → (中文名, 适用类)
DATA_PROPS: Dict[str, Tuple[str, List[str]]] = {
    "javaClass": ("Java 类名", ["Entity"]),
    "techName": ("源码 / 技术侧叫法", ["Entity"]),
    "tableName": ("数据表名", ["Entity"]),
    "javaField": ("Java 字段名", ["Field"]),
    "ownerEntity": ("所属业务实体", ["Field"]),
    "dictCode": ("字典编码", ["Dictionary"]),
    "attrCode": ("属性代码（attr_code）", ["CommonAttribute"]),
    "enumCode": ("枚举编码", ["EnumValue"]),
    "ruleSource": ("规则出处", ["BusinessRule"]),
}
ANNOTATIONS = {"basis": "依据", "via": "关联字段", "source": "出处"}

_ILLEGAL = re.compile(r"[^\w]")


def _local(type_: str, label: str) -> str:
    return f"{type_}_{_ILLEGAL.sub('_', label)}"


def _basis_of(t: Dict[str, Any]) -> str:
    return t.get("basis", "code")


def build_ontology(
    model: DomainModel, triplets: List[Dict[str, Any]], network: Dict[str, Any]
) -> Dict[str, Any]:
    """整理成与格式无关的 dict（JSON 导出直接用它，Turtle 由它生成）。"""
    # ---- 类 / 属性 ----
    classes = [{"name": n, "label": zh, "comment": CLASS_DESC[n]} for n, zh in lx.CONCEPTS.items()]
    props = [
        {
            "name": p.name, "label": p.zh, "comment": PREDICATE_DESC[p.name],
            "domain": sorted(p.domain), "range": sorted(p.range),
            "symmetric": p.name == "similarTo",
        }
        for p in lx.PREDICATES.values()
    ]
    data_props = [
        {"name": n, "label": zh, "domain": doms, "range": "xsd:string"} for n, (zh, doms) in DATA_PROPS.items()
    ]

    # ---- 个体 ----
    field_info: Dict[str, Tuple[str, str]] = {}
    for cls, labels in model.field_labels.items():
        for jname, zh in labels.items():
            field_info.setdefault(zh, (cls, jname))
    ent_by_label = {model.label(c): c for c in model.entities}
    attrs = {a.label: a for a in lx.COMMON_ATTRS}
    rules = {r.name: r for r in lx.RULES}
    scenarios = dict(lx.SCENARIOS)
    enums = {g.label(v): (g, v) for g in lx.ENUM_GROUPS for v in g.values}

    individuals: List[Dict[str, Any]] = []
    seen_local: Dict[str, str] = {}
    for n in sorted(network["nodes"], key=lambda x: (x["type"], x["label"])):
        typ, label = n["type"], n["label"]
        local = _local(typ, label)
        assert local not in seen_local, f"个体 IRI 冲突：{local}"
        seen_local[local] = n["id"]
        props_: Dict[str, Any] = {}
        comment = None
        aliases: List[str] = []
        if typ == "Entity":
            cls = ent_by_label[label]
            props_ = {"javaClass": cls, "techName": model.tech_names[cls], "tableName": model.entities[cls].table}
            comment = lx.ENTITY_BUSINESS_DESC[cls]
            aliases = model.aliases.get(cls, [])
        elif typ == "Field":
            cls, jname = field_info[label]
            props_ = {"javaField": jname, "ownerEntity": model.label(cls)}
        elif typ == "Dictionary":
            props_ = {"dictCode": model.dictionaries[label][1]}
        elif typ == "CommonAttribute":
            a = attrs[label]
            props_ = {"attrCode": a.code}
            comment = a.desc
            aliases = [a.code, *a.aliases]
        elif typ == "EnumValue":
            g, v = enums[label]
            props_ = {"enumCode": v.code}
            comment = v.desc
            aliases = list(v.alt)
        elif typ == "BusinessRule":
            r = rules[label]
            props_ = {"ruleSource": r.source}
            comment = r.text
        elif typ == "Scenario":
            comment = scenarios[label]
        individuals.append({
            "id": n["id"], "iri": BASE + local, "type": typ, "label": label,
            "comment": comment, "altLabels": aliases, "properties": props_,
        })

    # ---- 三元组 ----
    id_of = {(i["type"], i["label"]): i["iri"] for i in individuals}
    triples: List[Dict[str, Any]] = []
    for t in triplets:
        triples.append({
            "subject": t["subject"], "predicate": t["predicate"], "object": t["object"],
            "subject_type": t["subject_type"], "object_type": t["object_type"],
            "subject_iri": id_of[(t["subject_type"], t["subject"])],
            "object_iri": id_of[(t["object_type"], t["object"])],
            "basis": _basis_of(t), "via": t.get("via", []),
            "source": t["evidence"][0]["source"] if t.get("evidence") else "",
        })
    for e in network["edges"]:
        if e["label"] != "similarTo":
            continue
        st, sl = e["source"].split(":", 1)
        tt, tl = e["target"].split(":", 1)
        triples.append({
            "subject": sl, "predicate": "similarTo", "object": tl, "subject_type": st, "object_type": tt,
            "subject_iri": id_of[(st, sl)], "object_iri": id_of[(tt, tl)],
            "basis": "analysis", "via": e.get("via") or [], "source": "semantic_analysis（语义画像余弦 / 关键字段 Jaccard）",
        })

    # ---- 推理路径：每一步都必须是已有三元组 ----
    by_key = {(t["subject"], t["predicate"], t["object"]): t for t in triples}
    paths: List[Dict[str, Any]] = []
    for pd in lx.SCENARIO_PATHS:
        steps = []
        for s_, p_, o_ in pd.steps:
            t = by_key.get((s_, p_, o_))
            if t is None:
                raise ValueError(f"推理路径 {pd.name!r} 的步骤 {s_} {p_} {o_} 不在三元组里")
            steps.append({"subject": s_, "predicate": p_, "object": o_,
                          "subject_iri": t["subject_iri"], "object_iri": t["object_iri"]})
        paths.append({
            "scenario": pd.scenario, "scenario_iri": id_of[("Scenario", pd.scenario)], "name": pd.name,
            "description": pd.description, "basis": pd.basis, "steps": steps,
        })

    return {
        "ontology": {
            "uri": BASE.rstrip("#"), "namespace": BASE, "name": NAME, "version": VERSION, "description": DESCRIPTION,
            "basis_values": {
                "confirmed": "业务方确认", "code": "源码有直接证据", "analysis": "语义分析推断",
            },
        },
        "classes": classes,
        "object_properties": props,
        "data_properties": data_props,
        "individuals": individuals,
        "triples": triples,
        "reasoning_paths": paths,
        "similarity_criteria": {
            "note": "相近没有统一标准，各分类不同；未列出的分类暂无标准。规则按“分类范围 + 属性类别”配置，不逐个属性写死。",
            "items": [
                {"scope": {"level": c.scope_level, "code": c.scope_code, "name": c.scope_name},
                 "kind": c.kind, "tolerance": c.tolerance, "applies_to": c.applies_to, "examples": c.examples,
                 "identify_by": c.identify_by, "name_hints": c.name_hints,
                 "combine": c.combine, "unit_note": c.unit_note, "meaning": c.meaning, "source": c.source,
                 "note": "只比较该分类核心技术属性里属于 applies_to 的属性，分类没有的属性不参与比较；"
                         "目前按属性名称判断（identify_by=attribute_name，name_hints 为参考词，可增补），examples 不是穷举"}
                for c in lx.SIMILARITY_CRITERIA
            ],
        },
    }


def to_graph(onto: Dict[str, Any]) -> Graph:
    g = Graph()
    for prefix, ns in (("mk", MK), ("owl", OWL), ("rdfs", RDFS), ("skos", SKOS), ("xsd", XSD)):
        g.bind(prefix, ns)
    meta = onto["ontology"]
    root = URIRef(meta["uri"])
    g.add((root, RDF.type, OWL.Ontology))
    g.add((root, RDFS.label, Literal(meta["name"], lang="zh")))
    g.add((root, RDFS.comment, Literal(meta["description"], lang="zh")))
    g.add((root, OWL.versionInfo, Literal(meta["version"])))

    def class_ref(names: List[str]):
        if len(names) == 1:
            return MK[names[0]]
        node = BNode()
        lst = BNode()
        g.add((node, RDF.type, OWL.Class))
        Collection(g, lst, [MK[n] for n in names])
        g.add((node, OWL.unionOf, lst))
        return node

    for c in onto["classes"]:
        u = MK[c["name"]]
        g.add((u, RDF.type, OWL.Class))
        g.add((u, RDFS.label, Literal(c["label"], lang="zh")))
        g.add((u, RDFS.comment, Literal(c["comment"], lang="zh")))

    for p in onto["object_properties"]:
        u = MK[p["name"]]
        g.add((u, RDF.type, OWL.ObjectProperty))
        if p["symmetric"]:
            g.add((u, RDF.type, OWL.SymmetricProperty))
        g.add((u, RDFS.label, Literal(p["label"], lang="zh")))
        g.add((u, RDFS.comment, Literal(p["comment"], lang="zh")))
        g.add((u, RDFS.domain, class_ref(p["domain"])))
        g.add((u, RDFS.range, class_ref(p["range"])))

    for d in onto["data_properties"]:
        u = MK[d["name"]]
        g.add((u, RDF.type, OWL.DatatypeProperty))
        g.add((u, RDFS.label, Literal(d["label"], lang="zh")))
        g.add((u, RDFS.domain, class_ref(d["domain"])))
        g.add((u, RDFS.range, XSD.string))
    for name, zh in ANNOTATIONS.items():
        g.add((MK[name], RDF.type, OWL.AnnotationProperty))
        g.add((MK[name], RDFS.label, Literal(zh, lang="zh")))

    for i in onto["individuals"]:
        u = URIRef(i["iri"])
        g.add((u, RDF.type, OWL.NamedIndividual))
        g.add((u, RDF.type, MK[i["type"]]))
        g.add((u, RDFS.label, Literal(i["label"], lang="zh")))
        if i["comment"]:
            g.add((u, RDFS.comment, Literal(i["comment"], lang="zh")))
        for alt in i["altLabels"]:
            g.add((u, SKOS.altLabel, Literal(alt, lang="zh")))
        for k, v in i["properties"].items():
            g.add((u, MK[k], Literal(v)))

    for path in onto["reasoning_paths"]:  # TTL 里用 skos:scopeNote 记录路径（结构化版本见 JSON）
        chain = "；".join(f"{s['subject']} -{s['predicate']}-> {s['object']}" for s in path["steps"])
        g.add((URIRef(path["scenario_iri"]), SKOS.scopeNote,
               Literal(f"{path['name']}：{path['description']}路径：{chain}", lang="zh")))

    crit = "；".join(
        f"{c['scope']['level']}分类={c['scope']['code']}（{c['scope']['name']}）：核心技术属性里的{c['applies_to']}"
        f"（如{'、'.join(c['examples'])}，按属性名称判断，分类有哪些就比较哪些）"
        f"{'每一项' if c['combine'] == 'all' else '任一项'}的取值之差（绝对值，{c['unit_note']}）在±{c['tolerance']:g}以内表示{c['meaning']}"
        for c in onto["similarity_criteria"]["items"]
    )
    for iri in {i["iri"] for i in onto["individuals"] if i["type"] == "Scenario" and i["label"] in ("物料相似查找", "替代料推荐")}:
        g.add((URIRef(iri), SKOS.scopeNote,
               Literal(f"相近标准因分类而异，没有统一标准。{crit}；其他分类暂无标准。", lang="zh")))

    for t in onto["triples"]:
        s, p, o = URIRef(t["subject_iri"]), MK[t["predicate"]], URIRef(t["object_iri"])
        g.add((s, p, o))
        ax = BNode()  # 三元组标注：依据 / 关联字段 / 出处
        g.add((ax, RDF.type, OWL.Axiom))
        g.add((ax, OWL.annotatedSource, s))
        g.add((ax, OWL.annotatedProperty, p))
        g.add((ax, OWL.annotatedTarget, o))
        g.add((ax, MK.basis, Literal(t["basis"])))
        if t["via"]:
            g.add((ax, MK.via, Literal("、".join(t["via"]), lang="zh")))
        if t["source"]:
            g.add((ax, MK.source, Literal(t["source"])))
    return g


def export_ontology(
    model: DomainModel, triplets: List[Dict[str, Any]], network: Dict[str, Any], out_dir: Path
) -> Dict[str, Any]:
    onto = build_ontology(model, triplets, network)
    (out_dir / "ontology.json").write_text(json.dumps(onto, ensure_ascii=False, indent=2), encoding="utf-8")
    graph = to_graph(onto)
    graph.serialize(destination=str(out_dir / "ontology.ttl"), format="turtle")
    return {
        "classes": len(onto["classes"]),
        "object_properties": len(onto["object_properties"]),
        "individuals": len(onto["individuals"]),
        "triples": len(onto["triples"]),
        "rdf_statements": len(graph),
    }
