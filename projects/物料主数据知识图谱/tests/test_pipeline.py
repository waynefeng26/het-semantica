"""三元组抽取 / 语义分析 / 语义网络抽取 的基本回归测试。

运行：``python -m pytest tests -q``（需能访问 Java 源码目录）。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from matkg import lexicon as lx  # noqa: E402
from matkg.pipeline import (  # noqa: E402
    prepare,
    run_semantic_analysis,
    run_semantic_network,
    run_triplets,
)
from matkg.ingest_rules import (  # noqa: E402
    BAD_CODE_PREFIX,
    DUPLICATE_EFFECTIVE,
    ECAR_MISMATCH,
    NON_EFFECTIVE,
    ensure_ingestable,
    validate_material_rows,
)
from matkg.zh_extract import ZhSemanticAnalyzer  # noqa: E402

JAVA_ROOT = Path(r"D:\workspace\jeecg-boot\het-module-main\het-main\src\main\java\com\het\modules\addcode")
pytestmark = pytest.mark.skipif(not JAVA_ROOT.exists(), reason="需要 Java 源码目录")


@pytest.fixture(scope="module")
def ctx():
    return prepare(str(JAVA_ROOT))


@pytest.fixture(scope="module")
def triplets(ctx):
    return run_triplets(ctx)


def _has(triplets, s, p, o):
    return any(t["subject"] == s and t["predicate"] == p and t["object"] == o for t in triplets)


def test_scope_has_eight_entities(ctx):
    assert set(ctx.model.entities) == set(lx.SCOPE_ENTITIES)


def test_entity_facts(triplets):
    assert _has(triplets, "物料分类属性模板", "mapsToTable", "ac_classification_attribute_ref")
    assert _has(triplets, "物料属性值库", "hasKeyField", "项次代码")
    assert _has(triplets, "物料编码号段", "hasKeyField", "汽车电子当前最大编码")


def test_entity_relations_with_via(triplets):
    t = next(x for x in triplets if x["subject"] == "物料属性值库" and x["object"] == "物料分类属性模板")
    assert t["predicate"] == "refersTo"
    assert set(t["via"]) == {"L4分类代码", "属性代码"}
    assert _has(triplets, "物料基础属性", "partOf", "物料主数据")


def test_common_attributes_and_rules(triplets):
    assert _has(triplets, "物料基础属性", "includesAttribute", "物料名称属性")
    assert _has(triplets, "物料名称属性", "derivesFrom", "物料子类L4")
    assert _has(triplets, "物料简称属性", "derivesFrom", "元器件物料简称")
    assert _has(triplets, "物料编码号段", "governedBy", "编码号段选取规则")
    assert _has(triplets, "物料主数据", "governedBy", "有效物料判定规则")
    n_attr = sum(1 for t in triplets if t["predicate"] == "includesAttribute")
    assert n_attr == len(lx.COMMON_ATTRS)


def test_scenario_support_matches_lexicon(ctx, triplets):
    sup = {(t["subject"], t["object"]): t["basis"] for t in triplets if t["predicate"] == "supports"}
    expected = {(ctx.model.node_label(x.subject), x.scenario): x.basis for x in lx.SUPPORTS}
    assert sup == expected
    assert sup[("物料主数据", "物料精确查找")] == "code"
    assert sup[("物料私有属性", "替代料推荐")] == "confirmed"
    assert "inferred" not in sup.values()  # 场景支撑已全部由业务方确认


def test_no_operation_layer(ctx, triplets):
    preds = {t["predicate"] for t in triplets}
    assert not preds & {"manages", "dependsOn", "providesOperation", "reads", "writes", "matchesBy", "generates"}
    assert not {"Service", "Operation"} & {t.label for t in ctx.model.gazetteer.terms()}


def test_enum_values_and_bg(triplets):
    assert _has(triplets, "申请状态", "hasValue", "申请状态-审批完成")
    assert _has(triplets, "申请状态", "hasValue", "申请状态-历史版本")
    assert _has(triplets, "生命周期阶段属性", "hasValue", "生命周期阶段-完全停产")
    assert _has(triplets, "制造商AVL等级属性", "hasValue", "制造商AVL等级-考察")
    assert _has(triplets, "制造商AVL等级属性", "hasValue", "制造商AVL等级-限制")
    expected = sum(len(g.values) for g in lx.ENUM_GROUPS)
    assert sum(1 for t in triplets if t["predicate"] == "hasValue") == expected
    assert _has(triplets, "优选标识-优选A", "preferredFor", "海外家电BG")
    assert _has(triplets, "优选标识-优选B", "preferredFor", "国内家电BG")
    assert _has(triplets, "优选标识-优选1(汽电)", "preferredFor", "汽车电子BG")


def test_business_rules_confirmed(triplets):
    for rule in ("有效物料判定规则", "物料升级规则", "物料状态口径规则", "物料编码BG前缀规则"):
        t = next(x for x in triplets if x["subject"] == "物料主数据" and x["object"] == rule)
        assert t["predicate"] == "governedBy" and t["basis"] == "confirmed"
    assert _has(triplets, "物料基础属性", "includesAttribute", "制造商AVL等级属性")
    assert _has(triplets, "物料基础属性", "includesAttribute", "专用客户属性")
    assert _has(triplets, "物料基础属性", "governedBy", "客户专用料规则")
    assert _has(triplets, "是否汽车电子", "indicatesBG", "汽车电子BG")


def test_core_attributes_and_customers(triplets):
    for a in ("物料名称属性", "制造商零件编号属性", "制造商名称属性"):
        assert _has(triplets, "物料基础属性", "hasCoreAttribute", a)
    assert sum(1 for t in triplets if t["predicate"] == "hasCoreAttribute") == len(lx.CORE_ATTRS)
    assert _has(triplets, "专用客户属性", "hasValue", "专用客户-兰吉尔")
    assert _has(triplets, "专用客户属性", "hasValue", "专用客户-京瓷")
    assert _has(triplets, "物料主数据", "governedBy", "物料查重规则")
    assert _has(triplets, "制造商零件编号属性", "supports", "物料精确查找")
    assert _has(triplets, "制造商零件编号属性", "supports", "物料相似查找")
    assert _has(triplets, "制造商零件编号属性", "supports", "替代料推荐")
    assert _has(triplets, "物料基础属性", "governedBy", "同MPN替代规则")
    assert _has(triplets, "物料基础属性", "governedBy", "MPN相近替代判断规则")
    assert _has(triplets, "物料私有属性", "governedBy", "替代料判断流程")
    assert _has(triplets, "物料分类属性模板", "governedBy", "核心技术属性判定规则")
    assert _has(triplets, "物料分类", "governedBy", "分类相近标准规则")
    assert _has(triplets, "是否必填", "supports", "替代料推荐")
    c = lx.SIMILARITY_CRITERIA[0]
    assert (c.scope_level, c.scope_code, c.tolerance, c.combine) == ("L1", "28", 5, "all")
    assert "长" in c.examples and c.applies_to == "尺寸类的数值属性"  # 不逐个属性写死
    assert c.identify_by == "attribute_name" and "直径" in c.name_hints
    assert not any("可比性" in t["subject"] or "可比性" in t["object"] for t in triplets)  # 该字段已忽略


def test_reasoning_paths_follow_existing_triplets(triplets):
    for pd in lx.SCENARIO_PATHS:
        for s, p, o in pd.steps:
            assert _has(triplets, s, p, o), (pd.name, s, p, o)


def test_material_status_field_dropped(ctx):
    assert "物料状态" not in {t.surface for t in ctx.model.gazetteer.terms() if t.label == "Field"}


def test_ingest_rules():
    ok = [{"material_no": "10000001", "apply_status": 2}, {"material_no": "20000001", "apply_status": 2}]
    assert validate_material_rows(ok) == []
    ensure_ingestable(ok)

    bad = ok + [
        {"material_no": "10000001", "apply_status": 2},  # 重复的有效记录
        {"material_no": "10000002", "apply_status": 5},  # 历史版本不应入图
        {"material_no": "30000001", "apply_status": 2},  # 编码首位不是 1/2
    ]
    bad.append({"material_no": "20000009", "apply_status": 2, "ecar": 0})  # 汽电编码但 ecar=0
    kinds = {p["type"] for p in validate_material_rows(bad)}
    assert kinds == {DUPLICATE_EFFECTIVE, NON_EFFECTIVE, BAD_CODE_PREFIX, ECAR_MISMATCH}
    with pytest.raises(ValueError):
        ensure_ingestable(bad)


def test_no_framework_english_fallback_noise(triplets):
    assert all(t["predicate"] in lx.PREDICATES for t in triplets)
    assert "related_to" not in {t["predicate"] for t in triplets}


def test_triplets_respect_ontology(triplets):
    for t in triplets:
        p = lx.PREDICATES[t["predicate"]]
        assert t["subject_type"] in p.domain, t
        assert t["object_type"] in p.range, t


def test_semantic_roles(ctx):
    analyzer = ZhSemanticAnalyzer(ctx.model)
    res = analyzer.analyze_semantics("物料名称属性取自物料子类L4。物料私有属性支持替代料推荐。", label_roles=True)
    roles = {(r["word"], r["role"]) for r in res["semantic_roles"]}
    assert ("物料名称属性", "agent") in roles
    assert ("物料子类L4", "source") in roles
    assert ("替代料推荐", "purpose") in roles
    assert ("支持", "predicate") in roles


def test_similarity_and_network(ctx):
    analysis = run_semantic_analysis(ctx)
    pair = next(p for p in analysis["entity_similarity"] if {p["a"], p["b"]} == {"物料基础属性", "物料私有属性"})
    assert pair["key_field_jaccard"] == 1.0
    net = run_semantic_network(ctx, similar_to=analysis["similar_to"])
    ids = {n["id"] for n in net["nodes"]}
    assert "Entity:物料主数据" in ids and "BusinessRule:编码号段选取规则" in ids
    assert "Scenario:替代料推荐" in ids and "CommonAttribute:物料名称属性" in ids
    assert not any(n["type"] in ("Service", "Operation") for n in net["nodes"])
    # 节点唯一：同一规范实体不重复建节点
    assert len(ids) == len(net["nodes"])
    assert any(e["label"] == "similarTo" and e["inferred"] for e in net["edges"])


def test_export_ontology(ctx, triplets, tmp_path):
    import json

    from rdflib import Graph
    from rdflib.namespace import OWL, RDF

    from matkg.export_ontology import MK, export_ontology

    analysis = run_semantic_analysis(ctx)
    net = run_semantic_network(ctx, similar_to=analysis["similar_to"])
    stats = export_ontology(ctx.model, triplets, net, tmp_path)

    onto = json.loads((tmp_path / "ontology.json").read_text(encoding="utf-8"))
    assert {c["name"] for c in onto["classes"]} == set(lx.CONCEPTS)
    assert {p["name"] for p in onto["object_properties"]} == set(lx.PREDICATES)
    n_similar = sum(1 for e in net["edges"] if e["label"] == "similarTo")
    assert len(onto["triples"]) == len(triplets) + n_similar
    assert len({i["iri"] for i in onto["individuals"]}) == len(onto["individuals"])

    g = Graph().parse(str(tmp_path / "ontology.ttl"), format="turtle")
    assert len(g) == stats["rdf_statements"]
    assert len(onto["reasoning_paths"]) == len(lx.SCENARIO_PATHS)
    assert len(list(g.subjects(RDF.type, OWL.Class))) >= len(lx.CONCEPTS)
    # 每条三元组都能在 RDF 里找到，并带依据标注
    for t in onto["triples"]:
        from rdflib import URIRef

        s, p, o = URIRef(t["subject_iri"]), MK[t["predicate"]], URIRef(t["object_iri"])
        assert (s, p, o) in g
    assert len(list(g.subjects(RDF.type, OWL.Axiom))) == len(onto["triples"])
