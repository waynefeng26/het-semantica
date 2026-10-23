"""领域模型：把扫描结果 + 人工整理的领域知识，整理成统一的“规范实体表”(gazetteer)。

* :class:`Gazetteer`   词面 → 规范实体，用于中文 NER / 角色标注 / 相似度分词
* :class:`DomainModel` 范围内的实体、字段、常用属性、规则、场景
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from . import lexicon as lx
from .java_scanner import JavaEntity, ScanResult


@dataclass(frozen=True)
class Term:
    surface: str
    canonical: str
    label: str  # 本体概念名
    source: str = ""


class Gazetteer:
    """最长匹配、不重叠的词面匹配器。"""

    def __init__(self) -> None:
        self._terms: Dict[str, Term] = {}
        self._regex: Optional[re.Pattern] = None
        self._lower_index: Dict[str, Term] = {}

    def add(self, surface: str, canonical: str, label: str, source: str = "") -> bool:
        surface = surface.strip()
        if len(surface) < 2 or surface in self._terms:
            return False
        self._terms[surface] = Term(surface, canonical, label, source)
        self._regex = None
        return True

    def __len__(self) -> int:
        return len(self._terms)

    def terms(self) -> List[Term]:
        return list(self._terms.values())

    def canonical_terms(self) -> Dict[str, Term]:
        out: Dict[str, Term] = {}
        for t in self._terms.values():
            out.setdefault(t.canonical, t)
        return out

    @staticmethod
    def _surface_pattern(surface: str) -> str:
        esc = re.escape(surface)
        if re.fullmatch(r"[A-Za-z0-9_]+", surface):
            return rf"(?<![A-Za-z0-9_])(?i:{esc})(?![A-Za-z0-9_])"
        return esc

    def _compile(self) -> re.Pattern:
        if self._regex is None:
            surfaces = sorted(self._terms, key=len, reverse=True)
            self._lower_index = {s.lower(): self._terms[s] for s in surfaces}
            self._regex = re.compile("|".join(self._surface_pattern(s) for s in surfaces))
        return self._regex

    def lookup(self, surface: str) -> Optional[Term]:
        t = self._terms.get(surface)
        if t is not None:
            return t
        self._compile()
        return self._lower_index.get(surface.lower())

    def find(self, text: str) -> List[Tuple[int, int, Term]]:
        if not self._terms:
            return []
        out: List[Tuple[int, int, Term]] = []
        for m in self._compile().finditer(text):
            term = self.lookup(m.group(0))
            if term:
                out.append((m.start(), m.end(), term))
        return out

    def canonical_of(self, surface: str) -> str:
        t = self.lookup(surface)
        return t.canonical if t else surface

    def label_of(self, surface: str) -> Optional[str]:
        t = self.lookup(surface)
        return t.label if t else None


@dataclass
class DomainModel:
    scan: ScanResult
    gazetteer: Gazetteer = field(default_factory=Gazetteer)
    entities: Dict[str, JavaEntity] = field(default_factory=dict)  # 类名 → 实体
    entity_labels: Dict[str, str] = field(default_factory=dict)  # 类名 → 业务规范名
    tech_names: Dict[str, str] = field(default_factory=dict)  # 类名 → 源码/技术侧叫法
    aliases: Dict[str, List[str]] = field(default_factory=dict)  # 类名 → 别名（均归并到规范名）
    field_labels: Dict[str, Dict[str, str]] = field(default_factory=dict)  # 类名 → {java 字段名: 中文名}
    dictionaries: Dict[str, Tuple[str, str]] = field(default_factory=dict)  # 字典标签 → (字段中文名, 字典编码)

    def label(self, entity_class: str) -> str:
        return self.entity_labels[entity_class]

    def node_label(self, subject: str) -> str:
        """支撑关系的主语：实体类名 → 业务规范名；字段 / 常用属性本身就是规范名。"""
        return self.entity_labels.get(subject, subject)

    def key_field_labels(self, entity_class: str) -> List[str]:
        labels = self.field_labels[entity_class]
        return [labels[n] for n in lx.KEY_FIELDS[entity_class] if n in labels]


def _find_field_label(model: DomainModel, label: str) -> bool:
    return any(label in labels.values() for labels in model.field_labels.values())


def build_domain_model(scan: ScanResult) -> DomainModel:
    model = DomainModel(scan=scan)
    gaz = model.gazetteer

    # ---- 实体 -------------------------------------------------------------
    by_class = {e.class_name: e for e in scan.entities}
    for cls in lx.SCOPE_ENTITIES:
        ent = by_class.get(cls)
        if ent is None:
            raise ValueError(f"源码中未找到范围内实体 {cls}")
        model.entities[cls] = ent
        model.entity_labels[cls] = lx.ENTITY_LABELS[cls]
        model.tech_names[cls] = lx.ENTITY_TECH_NAMES[cls]
        model.field_labels[cls] = {f.name: f.label for f in ent.fields if f.persistent and f.label}

    for cls, ent in model.entities.items():
        label = model.entity_labels[cls]
        aliases = [model.tech_names[cls], cls, *lx.ENTITY_ALIASES.get(cls, [])]
        if ent.description:
            aliases.append(ent.description)
        gaz.add(label, label, "Entity", f"{cls}.java")
        for alias in aliases:
            if alias != label and gaz.add(alias, label, "Entity", f"{cls}.java(别名)"):
                model.aliases.setdefault(cls, []).append(alias)
        gaz.add(ent.table, ent.table, "DataTable", f"{cls}.java @TableName")

    # ---- 字段（仅收录“关键字段”与规则/操作里引用到的字段）--------------------
    wanted: Set[str] = set()
    for cls in lx.SCOPE_ENTITIES:
        for name in lx.KEY_FIELDS.get(cls, []):
            if name not in model.field_labels[cls]:
                raise ValueError(f"{cls} 没有字段 {name}（或缺少 @ApiModelProperty 中文名）")
            wanted.add(model.field_labels[cls][name])
    for rel in lx.ENTITY_RELATIONS:
        wanted.update(rel.via)
    common_labels = {a.label for a in lx.COMMON_ATTRS}
    for a in lx.COMMON_ATTRS:
        if a.derives_from:
            wanted.add(a.derives_from)
    for s in lx.SUPPORTS:
        if s.subject not in lx.SCOPE_ENTITIES and s.subject not in common_labels:
            wanted.add(s.subject)
    for g in lx.ENUM_GROUPS:
        if g.owner not in common_labels:
            wanted.add(g.owner)
    for fld, _bg, _src in lx.BG_INDICATORS:
        wanted.add(fld)
    for cls, name, _ in lx.FIELD_DICTIONARIES:
        wanted.add(model.field_labels[cls][name])
    for label in sorted(wanted):
        if not _find_field_label(model, label):
            raise ValueError(f"字段中文名 {label!r} 在范围内实体里不存在")
        owner = next(c for c, ls in model.field_labels.items() if label in ls.values())
        gaz.add(label, label, "Field", f"{owner}.java")

    # ---- 字典 ---------------------------------------------------------------
    for cls, name, code in lx.FIELD_DICTIONARIES:
        dlabel = f"{code}字典"
        model.dictionaries[dlabel] = (model.field_labels[cls][name], code)
        gaz.add(dlabel, dlabel, "Dictionary", f"{cls}.{name} @Dict(dicCode={code})")

    # ---- 规则 / 常用属性 / 场景 ----------------------------------------------
    rule_names = {r.name for r in lx.RULES}
    for cls, names in lx.ENTITY_RULES.items():
        for n in names:
            if n not in rule_names:
                raise ValueError(f"{cls} 引用了未定义的规则 {n}")
    for r in lx.RULES:
        gaz.add(r.name, r.name, "BusinessRule", r.source)
    for a in lx.COMMON_ATTRS:
        gaz.add(a.label, a.label, "CommonAttribute", a.source)
        gaz.add(a.code, a.label, "CommonAttribute", a.source)
    for g in lx.ENUM_GROUPS:
        if gaz.lookup(g.owner) is None:
            raise ValueError(f"枚举所属 {g.owner!r} 不在实体表里")
        for v in g.values:
            gaz.add(g.label(v), g.label(v), "EnumValue", g.source)
            if v.bg and v.bg not in lx.BUSINESS_GROUPS:
                raise ValueError(f"未定义的BG {v.bg}")
    for bg in lx.BUSINESS_GROUPS:
        gaz.add(bg, bg, "BusinessGroup", lx.BIZ)
    for fld, bg, _src in lx.BG_INDICATORS:
        if bg not in lx.BUSINESS_GROUPS:
            raise ValueError(f"未定义的BG {bg}")
    scenario_names = {n for n, _ in lx.SCENARIOS}
    for n, _ in lx.SCENARIOS:
        gaz.add(n, n, "Scenario", "lexicon.SCENARIOS")
    for s_ in lx.SUPPORTS:
        if s_.scenario not in scenario_names:
            raise ValueError(f"未定义的场景 {s_.scenario}")
        if gaz.lookup(model.node_label(s_.subject)) is None:
            raise ValueError(f"支撑关系主语 {s_.subject!r} 不在实体表里")

    return model
