"""Neo4j 入库纯函数的单元测试（不连接任何数据库）。"""

import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from matkg.neo4j_loader import (  # noqa: E402
    Config,
    TemplateIndex,
    build_attr_row,
    camel,
    chunks,
    code_range_key,
    ENTITY_NODE_LABEL,
    L_MATERIAL,
    enum_iri_map,
    is_core_technical,
    numeric_value,
    row_props,
    template_class_targets,
    template_scope,
)


def test_camel_and_row_props():
    assert camel("classify_l4") == "classifyL4"
    assert camel("id") == "id"
    props = row_props({"id": "1", "material_no": "1001", "del_flag": 0, "create_time": None, "x": Decimal("1.5")})
    assert props == {"id": "1", "materialNo": "1001", "x": 1.5}


def test_numeric_value():
    assert numeric_value("12.5") == 12.5
    assert numeric_value(" -3 ") == -3.0
    assert numeric_value("12mm") is None
    assert numeric_value("nan") is None
    assert numeric_value(None) is None


def test_code_range_key():
    assert code_range_key("28", "28010101") == "28010101"
    assert code_range_key("40", "40120101") == "40120101"
    assert code_range_key("38", "38020202") == "38020202"
    assert code_range_key("10", "10010101") == "10010101"[:2] + "010101"
    assert code_range_key(None, "10010101") is None


def test_core_technical_only_private_with_x():
    assert is_core_technical("pri", "X")
    assert not is_core_technical("pub", "X")
    assert not is_core_technical("pri", "")
    assert not is_core_technical("pri", None)


def test_template_scope_and_resolution_priority():
    assert template_scope("10-33") == ("L1range", (10, 33))
    assert template_scope("28")[0] == "L1"
    assert template_scope("28010101")[0] == "L4"
    templates = [
        {"id": "a", "fourCode": "28", "attributeCode": "len", "pubPri": "pri"},
        {"id": "b", "fourCode": "28010101", "attributeCode": "len", "pubPri": "pri"},
        {"id": "c", "fourCode": "10-33", "attributeCode": "len", "pubPri": "pri"},
    ]
    idx = TemplateIndex(templates)
    assert idx.resolve("28010101", "len", "pri")["id"] == "b"  # L4 优先于 L1
    assert idx.resolve("28020101", "len", "pri")["id"] == "a"  # 退到 L1
    assert idx.resolve("20010101", "len", "pri")["id"] == "c"  # 只有 L1 范围能命中
    assert idx.resolve("50010101", "len", "pri") is None
    assert idx.resolve("28010101", "len", "pub") is None  # 公有 / 私有分开


def test_template_class_targets():
    classes = [{"fourCode": "28010101", "firstCode": "28"}, {"fourCode": "10010101", "firstCode": "10"}]
    assert template_class_targets({"fourCode": "28010101"}, classes) == [("28010101", "L4")]
    assert template_class_targets({"fourCode": "28"}, classes) == [("28010101", "L1")]
    assert template_class_targets({"fourCode": "10-33"}, classes) == [("28010101", "L1range"), ("10010101", "L1range")]


def test_enum_map_and_build_attr_row():
    onto = {
        "individuals": [
            {"iri": "a", "properties": {"attrCode": "lifeCyclePhase"}},
            {"iri": "e", "properties": {"enumCode": "AP"}},
        ],
        "triples": [{"predicate": "hasValue", "subject_iri": "a", "object_iri": "e"}],
    }
    em = enum_iri_map(onto)
    assert em[("lifeCyclePhase", "AP")] == "e" and "lifeCyclePhase" in em.codes
    idx = TemplateIndex([{"id": "t1", "fourCode": "28010101", "attributeCode": "lifeCyclePhase", "pubPri": "pub"}])
    stats = Counter()
    row = {"id": "r1", "add_code_id": "m1", "attr_code": "lifeCyclePhase", "attr_value": "AP", "attr_values": "[]",
           "attr_desc": "生命周期", "attr_type": None, "required_falg": None, "is_unique": None}
    out = build_attr_row(row, "basic", "28010101", idx, em, {}, stats)
    assert out["eiri"] == "e" and out["tid"] == "t1" and "attrValues" not in out["props"]
    row2 = dict(row, id="r2", attr_value="ZZ")
    out2 = build_attr_row(row2, "basic", "28010101", idx, em, {}, stats)
    assert out2["eiri"] is None and stats["enum_unmatched::lifeCyclePhase::ZZ"] == 1


def test_private_row_gets_numeric_and_core_flag():
    idx = TemplateIndex([{"id": "t", "fourCode": "28010101", "attributeCode": "length", "pubPri": "pri",
                          "requiredFalg": "X"}])
    row = {"id": "p1", "add_code_id": "m", "attr_code": "length", "attr_value": "120", "attr_values": None}
    out = build_attr_row(row, "private", "28010101", idx, {}, {}, Counter())
    assert out["props"]["attrValueNum"] == 120.0 and out["props"]["isCoreTechnical"] is True


def test_jdbc_url_and_chunks():
    assert Config.parse_jdbc("jdbc:mysql://10.0.0.1:3306/jeecg-boot?useSSL=false") == ("10.0.0.1", 3306, "jeecg-boot")
    assert list(chunks(list(range(5)), 2)) == [[0, 1], [2, 3], [4]]


def test_automotive_by_prefix_and_english_labels():
    from matkg.ingest_rules import is_automotive

    assert is_automotive("20100001") and not is_automotive("10100001") and not is_automotive("40880000029")
    assert L_MATERIAL == "MaterialMaster"
    assert all(v.isascii() for v in ENTITY_NODE_LABEL.values())  # 数据节点标签全部是英文


def test_ignored_avl_values_not_reported_as_unmatched():
    idx = TemplateIndex([])
    em = enum_iri_map({"individuals": [{"iri": "a", "properties": {"attrCode": "manufacturerAvlRating"}},
                                      {"iri": "e", "properties": {"enumCode": "主力"}}],
                       "triples": [{"predicate": "hasValue", "subject_iri": "a", "object_iri": "e"}]})
    stats = Counter()
    row = {"id": "r", "add_code_id": "m", "attr_code": "manufacturerAvlRating", "attr_value": "AVL-C", "attr_values": None}
    build_attr_row(row, "basic", "", idx, em, {}, stats)
    assert stats["enum_ignored"] == 1 and stats["enum_unmatched"] == 0
