"""把 MySQL 里的物料主数据按本体写入 Neo4j。

图结构（两层）：

* **本体层**（标签 ``Ont`` + 类名）：来自 ``output/ontology.json`` 的个体和三元组，
  即“物料主数据 / 基础属性 / 私有属性 / 分类 / … 之间是什么关系、有哪些规则、枚举值、场景”。
  另有 ``OntClass`` / ``OntProperty`` 记录类与属性的 domain / range。
* **数据层**（标签用业务口径名）：
  ``MaterialMaster``（物料主数据）、``MaterialBasicAttribute``（物料基础属性）、``MaterialPrivateAttribute``（物料私有属性）、
  ``MaterialClassification``（物料分类）、``MaterialAttributeDef``（物料属性定义）、
  ``MaterialClassAttrTemplate``（物料分类属性模板）、``MaterialAttributeValue``（物料属性值库）、``MaterialCodeRange``（物料编码号段）。
  关系类型沿用本体谓词（``partOf`` / ``refersTo`` / ``hasValue``），关联字段写在关系的 ``via`` 上。
  节点属性名沿用 Java 字段名（本体里 Field 个体的 ``javaField``），例如 ``materialNo``、``classifyL4``。
* 桥接：基础属性行的取值命中枚举值时，``(MaterialBasicAttribute)-[:hasValue]->(:Ont:EnumValue)``。

数据量很大（物料主数据约 39 万、基础属性约 690 万非空行、私有属性约 210 万），所以：

* 只读取：申请状态 = 2 且 del_flag = 0 的物料主数据（业务规则“有效物料判定规则”）；入图前先做校验
  （``ingest_rules``），同一物料编码出现多条状态 2 的记录则直接中止；
* 属性行只写 **非空取值**；按物料主数据主键分批（keyset 分页），MySQL 预取与 Neo4j 写入并行；
* 每个事务只有几千行（Neo4j 堆只有 2G）；全新库用 ``CREATE``，续跑用 ``MERGE``（幂等）；
* 每批写完记录检查点（``:LoadState``），中断后可以接着跑。

连接信息只从环境变量 / 命令行读取，不写进仓库：

``MATKG_MYSQL_URL``（jdbc:mysql://host:port/db）、``MATKG_MYSQL_USER``、``MATKG_MYSQL_PASSWORD``、
``MATKG_NEO4J_URI``、``MATKG_NEO4J_USER``、``MATKG_NEO4J_PASSWORD``、``MATKG_NEO4J_DATABASE``。
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from . import lexicon as lx
from .ingest_rules import (
    DUPLICATE_EFFECTIVE,
    ECAR_MISMATCH,
    NON_EFFECTIVE,
    is_automotive,
    validate_material_rows,
)

log = logging.getLogger("matkg.neo4j")

# --------------------------------------------------------------------------- #
# 标签 / 常量
# --------------------------------------------------------------------------- #

# 节点标签：英文驼峰命名（业务口径名 → 英文标签；本体的 Entity 节点上用 nodeLabel 属性记录对应关系）
L_MATERIAL = "MaterialMaster"  # 物料主数据 AddCodeApply
L_BASIC = "MaterialBasicAttribute"  # 物料基础属性 AcAddCodeApplyAttr
L_PRIVATE = "MaterialPrivateAttribute"  # 物料私有属性 AcAddCodeApplyAttrp
L_CLASS = "MaterialClassification"  # 物料分类 ClassificationManagement
L_ATTR_DEF = "MaterialAttributeDef"  # 物料属性定义 AttributeManagement
L_TEMPLATE = "MaterialClassAttrTemplate"  # 物料分类属性模板 ClassificationAttributeRef
L_VALUE = "MaterialAttributeValue"  # 物料属性值库 AttributeValue
L_RANGE = "MaterialCodeRange"  # 物料编码号段 CodeRange

ENTITY_NODE_LABEL = {
    "物料主数据": L_MATERIAL, "物料基础属性": L_BASIC, "物料私有属性": L_PRIVATE, "物料分类": L_CLASS,
    "物料属性定义": L_ATTR_DEF, "物料分类属性模板": L_TEMPLATE, "物料属性值库": L_VALUE, "物料编码号段": L_RANGE,
}

# 第一版用中文标签入过库；重置时一并清理（并删掉旧的约束 / 索引）
LEGACY_LABELS = list(ENTITY_NODE_LABEL)
LEGACY_SCHEMA_NAMES = (
    [f"data_id_{i}" for i in range(8)]
    + ["ont_iri", "loadstate_name", "material_no", "class_four", "attrdef_code", "material_l4", "material_l1",
       "material_life", "material_mpn", "material_manu", "material_name", "template_four", "range_four",
       "material_short_desc"]
)

# 数据里不规范、业务上直接忽略的枚举取值（AVL 等级只认主力 / 合格 / 试用，其余都视为不及格）
IGNORED_ENUM_ATTRS = {"manufacturerAvlRating"}

DATA_LABELS = [L_MATERIAL, L_BASIC, L_PRIVATE, L_CLASS, L_ATTR_DEF, L_TEMPLATE, L_VALUE, L_RANGE]
META_LABELS = ["Ont", "OntClass", "OntProperty", "LoadState"]

# 物料主数据上冗余的“核心 / 常用筛选属性”（来自基础属性行，便于直接按物料检索）
MATERIAL_DENORM = {
    "materialName": "materialName",
    "manufacturerPartNumber": "manufacturerPartNumber",
    "manufacturersName": "manufacturersName",
    "lifeCyclePhase": "lifeCyclePhase",
    "preferredIdentification": "preferredIdentification",
    "manufacturerAvlRating": "manufacturerAvlRating",
    "notes": "customerCode",  # 专用客户属性：值是客户编码（A001 兰吉尔 / A002 京瓷）
}

AUDIT_COLUMNS = {"create_by", "create_time", "update_by", "update_time", "del_flag", "sys_org_code", "comparability_flag"}

MATERIAL_COLUMNS = [
    "id", "material_no", "old_material_no", "classify_l1", "classify_l2", "classify_l3", "classify_l4",
    "short_desc", "long_desc", "english_desc", "apply_status", "temp_code", "ecar", "version_num", "previous_id",
]
ATTR_COLUMNS = "id, add_code_id, attr_code, attr_value, attr_values, attr_desc, attr_type, required_falg, is_unique"

_NUM = re.compile(r"^[+-]?\d+(\.\d+)?$")


# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #


@dataclass
class Config:
    mysql_host: str
    mysql_port: int
    mysql_db: str
    mysql_user: str
    mysql_password: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str = "neo4j"

    @staticmethod
    def parse_jdbc(url: str) -> Tuple[str, int, str]:
        m = re.match(r"^(?:jdbc:)?mysql://([^:/]+)(?::(\d+))?/([^?]+)", url.strip())
        if not m:
            raise ValueError(f"无法解析 MySQL 地址：{url!r}")
        return m.group(1), int(m.group(2) or 3306), m.group(3)

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "Config":
        e = env if env is not None else os.environ
        missing = [k for k in ("MATKG_MYSQL_URL", "MATKG_MYSQL_USER", "MATKG_MYSQL_PASSWORD",
                               "MATKG_NEO4J_URI", "MATKG_NEO4J_USER", "MATKG_NEO4J_PASSWORD") if not e.get(k)]
        if missing:
            raise SystemExit("缺少环境变量：" + "、".join(missing))
        host, port, db = cls.parse_jdbc(e["MATKG_MYSQL_URL"])
        return cls(host, port, db, e["MATKG_MYSQL_USER"], e["MATKG_MYSQL_PASSWORD"],
                   e["MATKG_NEO4J_URI"], e["MATKG_NEO4J_USER"], e["MATKG_NEO4J_PASSWORD"],
                   e.get("MATKG_NEO4J_DATABASE", "neo4j"))


# --------------------------------------------------------------------------- #
# 纯函数（可单测）
# --------------------------------------------------------------------------- #


def camel(col: str) -> str:
    head, *rest = col.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest)


def clean_value(v: Any) -> Any:
    """转成 Neo4j 能存的类型；None 返回 None（调用方丢弃）。"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return v


def row_props(row: Dict[str, Any], drop: Iterable[str] = AUDIT_COLUMNS) -> Dict[str, Any]:
    drop = set(drop)
    out = {}
    for k, v in row.items():
        if k in drop:
            continue
        v = clean_value(v)
        if v is not None:
            out[camel(k)] = v
    return out


def numeric_value(text: Any) -> Optional[float]:
    """纯数字的取值转成 float（私有属性按绝对差比较时用）；其余返回 None。"""
    if not isinstance(text, str):
        return None
    s = text.strip()
    if not _NUM.match(s):
        return None
    f = float(s)
    return f if math.isfinite(f) else None


def code_range_key(l1: Optional[str], l4: Optional[str]) -> Optional[str]:
    """物料用哪个号段（编码号段选取规则）：L1=38 或 L4=40120101 取自己的，其余取 L1+010101。"""
    if not l1 or not l4:
        return None
    return l4 if (l1 == "38" or l4 == "40120101") else l1 + "010101"


def is_core_technical(pub_pri: Optional[str], required_flag: Optional[str]) -> bool:
    """核心技术属性：私有属性且模板“是否必填”为 X。"""
    return pub_pri == "pri" and (required_flag or "").strip().upper() == "X"


def template_scope(four_code: str) -> Tuple[str, Optional[Tuple[int, int]]]:
    """模板的 four_code 有三种写法：L4 分类代码 / L1 分类代码 / 起-止 的 L1 范围。"""
    if "-" in four_code:
        lo, hi = four_code.split("-", 1)
        return "L1range", (int(lo), int(hi))
    if len(four_code) == 2:
        return "L1", None
    return "L4", None


_SCOPE_PRIORITY = {"L4": 3, "L1": 2, "L1range": 1}  # 范围越具体优先级越高


class TemplateIndex:
    """按（属性代码, 公有/私有）把物料的 L4 分类解析到最具体的分类属性模板。"""

    def __init__(self, templates: List[Dict[str, Any]]) -> None:
        self._by: Dict[Tuple[str, str], List[Tuple[int, Dict[str, Any], Tuple[str, Any]]]] = defaultdict(list)
        for t in templates:
            if not t.get("fourCode") or not t.get("attributeCode"):
                continue
            scope = template_scope(t["fourCode"])
            self._by[(t["attributeCode"], t.get("pubPri") or "")].append((_SCOPE_PRIORITY[scope[0]], t, scope))
        for lst in self._by.values():
            lst.sort(key=lambda x: (-x[0], x[1]["id"]))
        self._cache: Dict[Tuple[str, str, str], Optional[Dict[str, Any]]] = {}

    def resolve(self, l4: str, attr_code: str, pub_pri: str) -> Optional[Dict[str, Any]]:
        key = (l4, attr_code, pub_pri)
        if key in self._cache:
            return self._cache[key]
        found = None
        for _, t, (kind, rng) in self._by.get((attr_code, pub_pri), []):
            if kind == "L4" and t["fourCode"] == l4:
                found = t
            elif kind == "L1" and t["fourCode"] == l4[:2]:
                found = t
            elif kind == "L1range" and l4[:2].isdigit() and rng[0] <= int(l4[:2]) <= rng[1]:
                found = t
            if found:
                break
        self._cache[key] = found
        return found


def template_class_targets(template: Dict[str, Any], classes: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """模板作用到哪些物料分类：[(L4 分类代码, 范围写法)]。"""
    kind, rng = template_scope(template["fourCode"])
    out = []
    for c in classes:
        if kind == "L4" and c["fourCode"] == template["fourCode"]:
            out.append((c["fourCode"], kind))
        elif kind == "L1" and c.get("firstCode") == template["fourCode"]:
            out.append((c["fourCode"], kind))
        elif kind == "L1range" and (c.get("firstCode") or "").isdigit() and rng[0] <= int(c["firstCode"]) <= rng[1]:
            out.append((c["fourCode"], kind))
    return out


class EnumMap(dict):
    """(attr_code, 取值) → 枚举值个体 IRI；``codes`` 是有枚举定义的属性代码集合。"""

    codes: set


def enum_iri_map(onto: Dict[str, Any]) -> "EnumMap":
    """由本体的 hasValue 三元组 + 个体的 attrCode / enumCode 得到。"""
    ind = {i["iri"]: i for i in onto["individuals"]}
    out = EnumMap()
    out.codes = set()
    for t in onto["triples"]:
        if t["predicate"] != "hasValue":
            continue
        subj, obj = ind[t["subject_iri"]], ind[t["object_iri"]]
        code = subj["properties"].get("attrCode")
        enum_code = obj["properties"].get("enumCode")
        if code and enum_code:
            out[(code, enum_code)] = obj["iri"]
            out.codes.add(code)
    return out


def build_attr_row(
    r: Dict[str, Any], table: str, l4: str, tindex: TemplateIndex, enum_map: Dict[Tuple[str, str], str],
    common_label: Dict[str, str], stats: Counter,
) -> Dict[str, Any]:
    """一行基础 / 私有属性 → 写入参数（props + 关联的材料 id / 模板 id / 枚举 IRI）。"""
    pub_pri = "pub" if table == "basic" else "pri"
    props: Dict[str, Any] = {
        "id": r["id"], "attrCode": r["attr_code"], "attrValue": r["attr_value"],
    }
    for src, dst in (("attr_desc", "attrDesc"), ("attr_type", "attrType"), ("required_falg", "requiredFalg"),
                     ("is_unique", "isUnique")):
        if r.get(src) not in (None, ""):
            props[dst] = clean_value(r[src])
    av = r.get("attr_values")
    if av not in (None, "", "[]"):
        props["attrValues"] = av
    num = numeric_value(r["attr_value"])
    if num is not None:
        props["attrValueNum"] = num

    t = tindex.resolve(l4, r["attr_code"], pub_pri) if l4 else None
    if t is not None:
        stats[f"{table}_template_resolved"] += 1
        if table == "private":
            props["isCoreTechnical"] = is_core_technical(t.get("pubPri"), t.get("requiredFalg"))
    else:
        stats[f"{table}_template_missing"] += 1
        if table == "private":
            props["isCoreTechnical"] = False
    if table == "basic" and r["attr_code"] in common_label:
        props["commonAttribute"] = common_label[r["attr_code"]]

    eiri = None
    if table == "basic":
        key = (r["attr_code"], r["attr_value"])
        eiri = enum_map.get(key)
        if r["attr_code"] in getattr(enum_map, "codes", ()):
            if eiri:
                stats["enum_matched"] += 1
            elif r["attr_code"] in IGNORED_ENUM_ATTRS:
                stats["enum_ignored"] += 1  # 业务方说明：不规范取值暂时忽略
            else:
                stats["enum_unmatched"] += 1
                stats[f"enum_unmatched::{r['attr_code']}::{r['attr_value']}"] += 1
    return {"id": r["id"], "mid": r["add_code_id"], "props": props, "tid": t["id"] if t else None, "eiri": eiri}


# --------------------------------------------------------------------------- #
# 数据库访问
# --------------------------------------------------------------------------- #


class MySQL:
    def __init__(self, cfg: Config) -> None:
        import pymysql

        self._pymysql = pymysql
        self.cfg = cfg
        self.conn = self._connect()

    def _connect(self):
        c = self.cfg
        return self._pymysql.connect(
            host=c.mysql_host, port=c.mysql_port, user=c.mysql_user, password=c.mysql_password, database=c.mysql_db,
            charset="utf8mb4", connect_timeout=15, read_timeout=600, cursorclass=self._pymysql.cursors.DictCursor,
        )

    def query(self, sql: str, args: Optional[tuple] = None) -> List[Dict[str, Any]]:
        self.conn.ping(reconnect=True)
        with self.conn.cursor() as cur:
            cur.execute(sql, args)
            return list(cur.fetchall())

    def close(self) -> None:
        self.conn.close()


@dataclass
class Batch:
    materials: List[Dict[str, Any]]
    basic: List[Dict[str, Any]]
    private: List[Dict[str, Any]]

    @property
    def last_id(self) -> Optional[str]:
        return self.materials[-1]["id"] if self.materials else None


def fetch_batch(db: MySQL, last_id: str, size: int) -> Batch:
    cols = ", ".join(MATERIAL_COLUMNS)
    mats = db.query(
        f"SELECT {cols} FROM ac_add_code_apply WHERE apply_status = 2 AND del_flag = 0 AND id > %s ORDER BY id LIMIT %s",
        (last_id, size),
    )
    if not mats:
        return Batch([], [], [])
    ids = [m["id"] for m in mats]
    marks = ",".join(["%s"] * len(ids))
    where = f"add_code_id IN ({marks}) AND attr_value IS NOT NULL AND attr_value <> ''"
    basic = db.query(f"SELECT {ATTR_COLUMNS} FROM ac_add_code_apply_attr WHERE {where}", tuple(ids))
    private = db.query(f"SELECT {ATTR_COLUMNS} FROM ac_add_code_apply_attrp WHERE {where}", tuple(ids))
    return Batch(mats, basic, private)


# --------------------------------------------------------------------------- #
# Neo4j 写入
# --------------------------------------------------------------------------- #


def chunks(rows: List[Any], n: int) -> Iterator[List[Any]]:
    for i in range(0, len(rows), n):
        yield rows[i:i + n]


def q(label: str) -> str:
    return f"`{label}`"


class Neo:
    def __init__(self, cfg: Config) -> None:
        from neo4j import GraphDatabase

        self.cfg = cfg
        self.driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
        self.driver.verify_connectivity()

    def session(self):
        return self.driver.session(database=self.cfg.neo4j_database)

    def run(self, cypher: str, **params: Any) -> List[Dict[str, Any]]:
        def work(tx):
            return [r.data() for r in tx.run(cypher, **params)]

        with self.session() as s:
            return s.execute_write(work)

    def run_auto(self, cypher: str, **params: Any) -> List[Dict[str, Any]]:
        """自动提交事务（CALL … IN TRANSACTIONS 需要）。"""
        with self.session() as s:
            return [r.data() for r in s.run(cypher, **params)]

    def close(self) -> None:
        self.driver.close()

    # ---- 结构 ----
    def schema_statements(self) -> List[Tuple[str, str]]:
        """(名称, 创建语句)。名称统一加 kg_ 前缀，与第一版（中文标签）的旧名称不冲突。"""
        m, c = q(L_MATERIAL), q(L_CLASS)
        stmts = [
            ("kg_ont_iri", "CONSTRAINT kg_ont_iri IF NOT EXISTS FOR (n:Ont) REQUIRE n.iri IS UNIQUE"),
            ("kg_loadstate_name", "CONSTRAINT kg_loadstate_name IF NOT EXISTS FOR (n:LoadState) REQUIRE n.name IS UNIQUE"),
        ]
        for lab in DATA_LABELS:
            stmts.append((f"kg_{lab}_id", f"CONSTRAINT kg_{lab}_id IF NOT EXISTS FOR (n:{q(lab)}) REQUIRE n.id IS UNIQUE"))
        stmts += [
            ("kg_material_no", f"CONSTRAINT kg_material_no IF NOT EXISTS FOR (n:{m}) REQUIRE n.materialNo IS UNIQUE"),
            ("kg_class_four", f"CONSTRAINT kg_class_four IF NOT EXISTS FOR (n:{c}) REQUIRE n.fourCode IS UNIQUE"),
            # 属性定义表里 attribute_code 有重复（configuration / outputCurrentUnit 各 2 条），只建普通索引
            ("kg_attrdef_code", f"INDEX kg_attrdef_code IF NOT EXISTS FOR (n:{q(L_ATTR_DEF)}) ON (n.attributeCode)"),
            ("kg_material_l4", f"INDEX kg_material_l4 IF NOT EXISTS FOR (n:{m}) ON (n.classifyL4)"),
            ("kg_material_l1", f"INDEX kg_material_l1 IF NOT EXISTS FOR (n:{m}) ON (n.classifyL1)"),
            ("kg_material_life", f"INDEX kg_material_life IF NOT EXISTS FOR (n:{m}) ON (n.lifeCyclePhase)"),
            ("kg_material_mpn", f"INDEX kg_material_mpn IF NOT EXISTS FOR (n:{m}) ON (n.manufacturerPartNumber)"),
            ("kg_material_manu", f"INDEX kg_material_manu IF NOT EXISTS FOR (n:{m}) ON (n.manufacturersName)"),
            ("kg_material_name", f"INDEX kg_material_name IF NOT EXISTS FOR (n:{m}) ON (n.materialName)"),
            ("kg_template_four", f"INDEX kg_template_four IF NOT EXISTS FOR (n:{q(L_TEMPLATE)}) ON (n.fourCode)"),
            ("kg_range_four", f"INDEX kg_range_four IF NOT EXISTS FOR (n:{q(L_RANGE)}) ON (n.fourCode)"),
            ("kg_material_short_desc", f"TEXT INDEX kg_material_short_desc IF NOT EXISTS FOR (n:{m}) ON (n.shortDesc)"),
        ]
        return [(n, "CREATE " + s) for n, s in stmts]

    def drop_schema(self) -> None:
        names = [n for n, _ in self.schema_statements()] + LEGACY_SCHEMA_NAMES
        for n in names:
            self.run_auto(f"DROP CONSTRAINT {n} IF EXISTS")
            self.run_auto(f"DROP INDEX {n} IF EXISTS")

    def ensure_schema(self) -> None:
        for _, stmt in self.schema_statements():
            self.run_auto(stmt)
        self.run_auto("CALL db.awaitIndexes(300)")

    def reset(self) -> None:
        """只删除本工具管理的标签（数据层 + 本体层 + 第一版的中文标签）和对应的约束 / 索引，不动库里其它数据。"""
        self.drop_schema()  # 先删约束 / 索引，删除节点更快
        for lab in DATA_LABELS + LEGACY_LABELS + META_LABELS:
            self.run_auto(f"MATCH (n:{q(lab)}) CALL (n) {{ DETACH DELETE n }} IN TRANSACTIONS OF 5000 ROWS")

    def count(self, label: str) -> int:
        return self.run(f"MATCH (n:{q(label)}) RETURN count(n) AS c")[0]["c"]

    def rel_count(self, rel: str) -> int:
        return self.run(f"MATCH ()-[r:{q(rel)}]->() RETURN count(r) AS c")[0]["c"]

    # ---- 本体层 ----
    def load_ontology(self, onto: Dict[str, Any]) -> Dict[str, int]:
        for c in onto["classes"]:
            self.run("MERGE (n:OntClass {name:$name}) SET n.label=$label, n.comment=$comment",
                     name=c["name"], label=c["label"], comment=c["comment"])
        for p in onto["object_properties"]:
            self.run("MERGE (n:OntProperty {name:$name}) SET n.label=$label, n.comment=$comment, "
                     "n.domain=$domain, n.range=$range, n.symmetric=$sym",
                     name=p["name"], label=p["label"], comment=p["comment"], domain=p["domain"],
                     range=p["range"], sym=p["symmetric"])

        extra: Dict[str, Dict[str, str]] = defaultdict(dict)  # 场景个体上挂推理路径 / 相近标准（JSON 字符串）
        for path in onto.get("reasoning_paths", []):
            extra[path["scenario_iri"]].setdefault("reasoningPaths", []).append(path)
        for iri, d in list(extra.items()):
            d["reasoningPaths"] = json.dumps(d["reasoningPaths"], ensure_ascii=False)
        crit = json.dumps(onto.get("similarity_criteria", {}), ensure_ascii=False)
        for i in onto["individuals"]:
            if i["type"] == "Scenario" and i["label"] in ("物料相似查找", "替代料推荐"):
                extra[i["iri"]]["similarityCriteria"] = crit

        by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for i in onto["individuals"]:
            props = {"name": i["label"], "layer": "ontology", **i["properties"], **extra.get(i["iri"], {})}
            if i["comment"]:
                props["comment"] = i["comment"]
            if i["altLabels"]:
                props["altLabels"] = i["altLabels"]
            if i["type"] == "Entity" and i["label"] in ENTITY_NODE_LABEL:
                props["nodeLabel"] = ENTITY_NODE_LABEL[i["label"]]  # 本体里的业务实体 → 图里数据节点的标签
            by_type[i["type"]].append({"iri": i["iri"], "props": props})
        n_nodes = 0
        for typ, rows in by_type.items():
            if typ not in lx.CONCEPTS:
                raise ValueError(f"未知的本体类 {typ}")
            for part in chunks(rows, 500):
                self.run(f"UNWIND $rows AS r MERGE (n:Ont {{iri:r.iri}}) SET n:{q(typ)}, n += r.props", rows=part)
            n_nodes += len(rows)

        by_pred: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for t in onto["triples"]:
            by_pred[t["predicate"]].append({
                "s": t["subject_iri"], "o": t["object_iri"], "basis": t["basis"],
                "via": "、".join(t["via"]) if t["via"] else None, "source": t["source"],
            })
        n_rels = 0
        for pred, rows in by_pred.items():
            if pred not in lx.PREDICATES:
                raise ValueError(f"未知的本体谓词 {pred}")
            for part in chunks(rows, 500):
                self.run(
                    f"UNWIND $rows AS r MATCH (a:Ont {{iri:r.s}}) MATCH (b:Ont {{iri:r.o}}) "
                    f"MERGE (a)-[x:{q(pred)}]->(b) SET x.basis=r.basis, x.via=r.via, x.source=r.source",
                    rows=part,
                )
            n_rels += len(rows)
        return {"ontology_nodes": n_nodes, "ontology_rels": n_rels}


# --------------------------------------------------------------------------- #
# 维度表（分类 / 属性定义 / 模板 / 值库 / 号段）
# --------------------------------------------------------------------------- #

DIM_SQL = {
    L_CLASS: "SELECT * FROM ac_classification_management WHERE del_flag = 0",
    L_ATTR_DEF: "SELECT * FROM ac_attribute_management WHERE del_flag = 0",
    L_TEMPLATE: "SELECT * FROM ac_classification_attribute_ref WHERE del_flag = 0",
    L_VALUE: "SELECT * FROM ac_attribute_value WHERE del_flag = 0",
    L_RANGE: "SELECT * FROM ac_code_range WHERE del_flag = 0",
}


def load_dimensions(db: MySQL, neo: Neo, merge: bool) -> Tuple[TemplateIndex, Dict[str, int]]:
    stats: Dict[str, int] = {}
    data: Dict[str, List[Dict[str, Any]]] = {}
    for label, sql in DIM_SQL.items():
        rows = [row_props(r) for r in db.query(sql)]
        if label == L_TEMPLATE:
            for r in rows:
                r["isCoreTechnical"] = is_core_technical(r.get("pubPri"), r.get("requiredFalg"))
        data[label] = rows
        verb = "MERGE" if merge else "CREATE"
        for part in chunks(rows, 1000):
            if merge:
                neo.run(f"UNWIND $rows AS r MERGE (n:{q(label)} {{id:r.id}}) SET n += r", rows=part)
            else:
                neo.run(f"UNWIND $rows AS r {verb} (n:{q(label)}) SET n = r", rows=part)
        stats[label] = len(rows)

    classes, templates = data[L_CLASS], data[L_TEMPLATE]
    tindex = TemplateIndex(templates)
    rel_merge = "MERGE" if merge else "CREATE"

    def rels(cypher: str, rows: List[Dict[str, Any]], name: str) -> None:
        for part in chunks(rows, 2000):
            neo.run(cypher, rows=part)
        stats[name] = len(rows)

    # 分类属性模板 → 物料分类（范围匹配：L4 / L1 / L1 范围）
    rows = [
        {"tid": t["id"], "four": four, "scope": scope}
        for t in templates for four, scope in template_class_targets(t, classes)
    ]
    rels(f"UNWIND $rows AS r MATCH (t:{q(L_TEMPLATE)} {{id:r.tid}}) MATCH (c:{q(L_CLASS)} {{fourCode:r.four}}) "
         f"{rel_merge} (t)-[:refersTo {{via:'fourCode', scope:r.scope}}]->(c)", rows, "template_to_class")
    # 分类属性模板 → 物料属性定义
    rows = [{"tid": t["id"], "code": t["attributeCode"]} for t in templates if t.get("attributeCode")]
    rels(f"UNWIND $rows AS r MATCH (t:{q(L_TEMPLATE)} {{id:r.tid}}) MATCH (a:{q(L_ATTR_DEF)} {{attributeCode:r.code}}) "
         f"{rel_merge} (t)-[:refersTo {{via:'attributeCode'}}]->(a)", rows, "template_to_attrdef")
    # 属性值库 → 模板（同 L4 分类代码写法 + 属性代码）、→ 属性定义
    tkey: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for t in templates:
        tkey[(t.get("fourCode"), t.get("attributeCode"))].append(t["id"])
    rows = [{"vid": v["id"], "tid": tid} for v in data[L_VALUE] for tid in tkey.get((v.get("fourCode"), v.get("attributeCode")), [])]
    rels(f"UNWIND $rows AS r MATCH (v:{q(L_VALUE)} {{id:r.vid}}) MATCH (t:{q(L_TEMPLATE)} {{id:r.tid}}) "
         f"{rel_merge} (v)-[:refersTo {{via:'fourCode+attributeCode'}}]->(t)", rows, "value_to_template")
    rows = [{"vid": v["id"], "code": v["attributeCode"]} for v in data[L_VALUE] if v.get("attributeCode")]
    rels(f"UNWIND $rows AS r MATCH (v:{q(L_VALUE)} {{id:r.vid}}) MATCH (a:{q(L_ATTR_DEF)} {{attributeCode:r.code}}) "
         f"{rel_merge} (v)-[:refersTo {{via:'attributeCode'}}]->(a)", rows, "value_to_attrdef")
    # 编码号段 → 物料分类
    rows = [{"gid": g["id"], "four": g["fourCode"]} for g in data[L_RANGE] if g.get("fourCode")]
    rels(f"UNWIND $rows AS r MATCH (g:{q(L_RANGE)} {{id:r.gid}}) MATCH (c:{q(L_CLASS)} {{fourCode:r.four}}) "
         f"{rel_merge} (g)-[:refersTo {{via:'fourCode'}}]->(c)", rows, "range_to_class")
    return tindex, stats


# --------------------------------------------------------------------------- #
# 物料主数据 + 基础 / 私有属性（大表）
# --------------------------------------------------------------------------- #


def validate_materials(db: MySQL) -> Dict[str, Any]:
    """入图前校验：有效物料判定规则（状态 2、编码唯一）、汽车电子标识与编码首位是否一致（只标记）。"""
    rows = db.query("SELECT id, material_no, apply_status, ecar FROM ac_add_code_apply "
                    "WHERE apply_status = 2 AND del_flag = 0")
    problems = validate_material_rows(rows)
    kinds = Counter(p["type"] for p in problems)
    hard = [p for p in problems if p["type"] in (NON_EFFECTIVE, DUPLICATE_EFFECTIVE)]
    if hard:
        raise ValueError("物料主数据校验失败（同一物料编码有多条申请状态为 2 的记录，或状态不是 2）：\n"
                         + "\n".join(p["message"] for p in hard[:20]))
    flags: Dict[str, List[str]] = defaultdict(list)
    for p in problems:
        flags[p["material_no"]].append(p["type"])
    deleted_status2 = db.query("SELECT COUNT(*) AS c FROM ac_add_code_apply WHERE apply_status = 2 AND del_flag = 1")[0]["c"]
    return {
        "checked": len(rows), "violations": dict(kinds), "flags": flags,
        "examples": {k: [p["message"] for p in problems if p["type"] == k][:5] for k in kinds},
        "excluded_logically_deleted_status2": deleted_status2,
    }


MATERIAL_CYPHER_CREATE = f"""
UNWIND $rows AS r
CREATE (m:{q(L_MATERIAL)}) SET m = r.props
WITH m, r
OPTIONAL MATCH (c:{q(L_CLASS)} {{fourCode:r.l4}})
FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END | CREATE (m)-[:refersTo {{via:'classifyL4'}}]->(c))
WITH m, r
OPTIONAL MATCH (g:{q(L_RANGE)} {{fourCode:r.rk}})
FOREACH (_ IN CASE WHEN g IS NULL THEN [] ELSE [1] END | CREATE (m)-[:refersTo {{via:'classifyL4+codeRangeRule'}}]->(g))
"""
MATERIAL_CYPHER_MERGE = MATERIAL_CYPHER_CREATE.replace(
    f"CREATE (m:{q(L_MATERIAL)}) SET m = r.props", f"MERGE (m:{q(L_MATERIAL)} {{id:r.id}}) SET m += r.props"
).replace("CREATE (m)-[:refersTo", "MERGE (m)-[:refersTo")


def attr_cypher(label: str, merge: bool, with_template_rel: bool) -> str:
    node = f"MERGE (a:{q(label)} {{id:r.id}}) SET a += r.props" if merge else f"CREATE (a:{q(label)}) SET a = r.props"
    rel = "MERGE" if merge else "CREATE"
    c = (
        f"UNWIND $rows AS r\n{node}\nWITH a, r\n"
        f"MATCH (m:{q(L_MATERIAL)} {{id:r.mid}})\n{rel} (a)-[:partOf {{via:'addCodeId'}}]->(m)\n"
    )
    if with_template_rel:
        c += (
            f"WITH a, r\nOPTIONAL MATCH (t:{q(L_TEMPLATE)} {{id:r.tid}})\n"
            f"FOREACH (_ IN CASE WHEN t IS NULL THEN [] ELSE [1] END | {rel} (a)-[:refersTo {{via:'attrCode'}}]->(t))\n"
        )
    if label == L_BASIC:
        c += (
            "WITH a, r\nOPTIONAL MATCH (e:Ont {iri:r.eiri})\n"
            f"FOREACH (_ IN CASE WHEN e IS NULL THEN [] ELSE [1] END | {rel} (a)-[:hasValue]->(e))\n"
        )
    return c


@dataclass
class LoadOptions:
    batch_size: int = 2000  # 每批物料主数据行数
    tx_rows: int = 4000  # 每个 Neo4j 事务的行数
    limit_materials: Optional[int] = None
    basic_template_rel: bool = True
    merge: bool = False


def load_materials(
    cfg: Config, neo: Neo, tindex: TemplateIndex, onto: Dict[str, Any], flags: Dict[str, List[str]],
    opts: LoadOptions, progress=print,
) -> Dict[str, Any]:
    enum_map = enum_iri_map(onto)
    common_label = {a.code: a.label for a in lx.COMMON_ATTRS}
    stats: Counter = Counter()

    state = neo.run("MATCH (s:LoadState {name:'materials'}) RETURN s.lastId AS lastId, s.loaded AS loaded")
    last_id = state[0]["lastId"] if state else ""
    stats["resumed_from_materials"] = state[0]["loaded"] if state else 0
    loaded = stats["resumed_from_materials"] or 0
    total_db = MySQL(cfg)
    expected = total_db.query("SELECT COUNT(*) AS c FROM ac_add_code_apply WHERE apply_status = 2 AND del_flag = 0")[0]["c"]
    total_db.close()
    target = min(expected, opts.limit_materials) if opts.limit_materials else expected

    mat_cypher = MATERIAL_CYPHER_MERGE if opts.merge else MATERIAL_CYPHER_CREATE
    basic_cypher = attr_cypher(L_BASIC, opts.merge, opts.basic_template_rel)
    priv_cypher = attr_cypher(L_PRIVATE, opts.merge, True)

    fetch_db = MySQL(cfg)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fetch_batch, fetch_db, last_id or "", opts.batch_size)
        while True:
            batch: Batch = fut.result()
            if not batch.materials:
                break
            if opts.limit_materials and loaded + len(batch.materials) > opts.limit_materials:
                batch.materials = batch.materials[: opts.limit_materials - loaded]
                ids = {m["id"] for m in batch.materials}
                batch.basic = [a for a in batch.basic if a["add_code_id"] in ids]
                batch.private = [a for a in batch.private if a["add_code_id"] in ids]
            next_last = batch.last_id
            stop = bool(opts.limit_materials) and loaded + len(batch.materials) >= opts.limit_materials
            if not stop:
                fut = ex.submit(fetch_batch, fetch_db, next_last, opts.batch_size)

            l4_of = {m["id"]: m["classify_l4"] for m in batch.materials}
            denorm: Dict[str, Dict[str, Any]] = defaultdict(dict)
            basic_rows = []
            for a in batch.basic:
                if a["attr_code"] in MATERIAL_DENORM:
                    denorm[a["add_code_id"]][MATERIAL_DENORM[a["attr_code"]]] = a["attr_value"]
                basic_rows.append(build_attr_row(a, "basic", l4_of[a["add_code_id"]], tindex, enum_map, common_label, stats))
            priv_rows = [build_attr_row(a, "private", l4_of[a["add_code_id"]], tindex, enum_map, common_label, stats)
                         for a in batch.private]

            mat_rows = []
            for m in batch.materials:
                props = row_props(m)
                props.update(denorm.get(m["id"], {}))
                props["isAutomotive"] = is_automotive(m["material_no"])  # 编码以 2 开头 = 汽车电子，其余非汽车电子
                f = flags.get(m["material_no"])
                if f:
                    props["qualityFlags"] = f
                    for k in f:
                        stats[f"quality::{k}"] += 1
                mat_rows.append({
                    "id": m["id"], "props": props, "l4": m["classify_l4"],
                    "rk": code_range_key(m["classify_l1"], m["classify_l4"]),
                })

            for part in chunks(mat_rows, opts.tx_rows):
                neo.run(mat_cypher, rows=part)
            for part in chunks(basic_rows, opts.tx_rows):
                neo.run(basic_cypher, rows=part)
            for part in chunks(priv_rows, opts.tx_rows):
                neo.run(priv_cypher, rows=part)

            loaded += len(batch.materials)
            stats["materials"] += len(batch.materials)
            stats["basic_rows"] += len(basic_rows)
            stats["private_rows"] += len(priv_rows)
            neo.run("MERGE (s:LoadState {name:'materials'}) SET s.lastId=$id, s.loaded=$n, s.updated=toString(datetime())",
                    id=next_last, n=loaded)
            el = time.time() - t0
            rate = stats["materials"] / el if el else 0
            eta = (target - loaded) / rate if rate else 0
            progress(f"  物料 {loaded:,}/{target:,}  基础属性 {stats['basic_rows']:,}  私有属性 {stats['private_rows']:,}  "
                     f"{rate:,.0f} 物料/秒  剩余约 {eta / 60:.1f} 分钟")
            if stop:
                break
    fetch_db.close()
    stats["seconds"] = round(time.time() - t0, 1)
    return dict(stats)


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #


def run_load(
    cfg: Config, onto_path: Path, out_dir: Path, opts: LoadOptions, reset: bool = False,
    skip_ontology: bool = False, skip_dimensions: bool = False, dry_run: bool = False, progress=print,
) -> Dict[str, Any]:
    onto = json.loads(onto_path.read_text(encoding="utf-8"))
    report: Dict[str, Any] = {"started": datetime.now().isoformat(timespec="seconds"), "options": opts.__dict__}

    db = MySQL(cfg)
    progress("校验物料主数据（申请状态 = 2、编码唯一）…")
    val = validate_materials(db)
    report["validation"] = {k: v for k, v in val.items() if k != "flags"}
    progress(f"  已检查 {val['checked']:,} 条，违规：{val['violations'] or '无'}；"
             f"逻辑删除(del_flag=1)的状态 2 记录 {val['excluded_logically_deleted_status2']:,} 条已排除")
    if dry_run:
        db.close()
        report["dry_run"] = True
        _write_report(out_dir, report)
        return report

    neo = Neo(cfg)
    try:
        if reset:
            progress("清理旧数据（仅本工具管理的标签）…")
            neo.reset()
        neo.ensure_schema()
        resumed = bool(neo.run("MATCH (s:LoadState {name:'materials'}) RETURN s LIMIT 1"))
        opts.merge = opts.merge or resumed or (neo.count(L_MATERIAL) > 0)
        progress(f"写入模式：{'MERGE（续跑 / 幂等）' if opts.merge else 'CREATE（全新库，最快）'}")

        if not skip_ontology:
            progress("写入本体层…")
            report["ontology"] = neo.load_ontology(onto)
        if skip_dimensions:
            rows = db.query("SELECT * FROM ac_classification_attribute_ref WHERE del_flag = 0")
            tindex = TemplateIndex([row_props(r) for r in rows])
        else:
            progress("写入分类 / 属性定义 / 分类属性模板 / 属性值库 / 编码号段…")
            tindex, report["dimensions"] = load_dimensions(db, neo, opts.merge)
        db.close()

        progress("写入物料主数据 + 基础属性 + 私有属性（大表，分批）…")
        report["materials"] = load_materials(cfg, neo, tindex, onto, val["flags"], opts, progress)

        counts = {lab: neo.count(lab) for lab in DATA_LABELS}
        rels = {r: neo.rel_count(r) for r in ("partOf", "refersTo", "hasValue")}
        report["neo4j_counts"] = {"nodes": counts, "relationships": rels}
    finally:
        neo.close()
    report["finished"] = datetime.now().isoformat(timespec="seconds")
    _write_report(out_dir, report)
    return report


def _write_report(out_dir: Path, report: Dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    mat = report.get("materials", {})
    enum_un = {k.split("::", 1)[1]: v for k, v in mat.items() if k.startswith("enum_unmatched::")}
    slim = {k: v for k, v in mat.items() if not k.startswith("enum_unmatched::")}
    report = {**report, "materials": slim, "enum_unmatched_values": dict(sorted(enum_un.items(), key=lambda x: -x[1]))}
    (out_dir / "neo4j_load_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    L = ["# Neo4j 入库报告\n"]
    L.append(f"- 开始：{report.get('started')}　结束：{report.get('finished', '（未完成 / 仅校验）')}")
    v = report.get("validation", {})
    L.append(f"\n## 入图前校验\n\n- 检查物料主数据 {v.get('checked', 0):,} 条（申请状态 = 2 且 del_flag = 0）")
    L.append(f"- 违规统计：{v.get('violations') or '无'}")
    L.append(f"- 因逻辑删除（del_flag=1）而排除的状态 2 记录：{v.get('excluded_logically_deleted_status2', 0):,} 条")
    for k, ex in (v.get("examples") or {}).items():
        L.append(f"  - {k} 示例：" + "；".join(ex[:3]))
    if "neo4j_counts" in report:
        nc = report["neo4j_counts"]
        L.append("\n## 写入结果\n\n| 标签 | 节点数 |\n|---|---|")
        for k, c in nc["nodes"].items():
            L.append(f"| {k} | {c:,} |")
        L.append("\n| 关系 | 数量 |\n|---|---|")
        for k, c in nc["relationships"].items():
            L.append(f"| {k} | {c:,} |")
    if mat:
        L.append("\n## 统计\n")
        for k, c in slim.items():
            L.append(f"- {k}：{c:,}" if isinstance(c, int) else f"- {k}：{c}")
    if enum_un:
        L.append("\n## 未命中本体枚举值的取值（仍保留原值，没有 hasValue 关系）\n\n| 属性代码 :: 取值 | 行数 |\n|---|---|")
        for k, c in list(report["enum_unmatched_values"].items())[:40]:
            L.append(f"| {k} | {c:,} |")
    (out_dir / "neo4j_load_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
