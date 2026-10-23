"""把范围内的 Java 源码事实写成中文叙述语料，供 Semantica 的抽取器“阅读”。

语料来源：
* 实体：@TableName / @ApiModelProperty / @Dict（由 java_scanner 解析）
* 实体关系、常用属性、业务规则、应用场景：service 层 / Mapper XML 阅读结果（lexicon.py，带出处）

每个 :class:`Doc` 的 ``meta['source']`` 指向源码出处，便于回溯。
为避免触发词误伤，叙述句式是固定的（“X对应数据表Y”“X包含常用属性Y”“X受Z约束”“X支持场景”等），
这也是抽取规则 (lexicon.RELATION_CUES) 所依据的句式。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from . import lexicon as lx
from .domain_model import DomainModel


@dataclass
class Doc:
    id: str
    kind: str  # entity | relation | attribute | enum | rule | scenario | support
    title: str
    text: str
    source: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def as_item(self) -> Dict[str, Any]:
        """Semantica 批处理接口接受的 {"id", "content"} 形式。"""
        return {"id": self.id, "content": self.text}


def _join(items: List[str]) -> str:
    return "、".join(items)


# --------------------------------------------------------------------------- #
# 实体
# --------------------------------------------------------------------------- #


def _entity_docs(model: DomainModel) -> List[Doc]:
    docs: List[Doc] = []
    for cls, ent in model.entities.items():
        label = model.label(cls)
        persistent = [f for f in ent.fields if f.persistent]
        sents = [
            f"{label}的业务口径：{lx.ENTITY_BUSINESS_DESC[cls]}",
            f"{label}（{cls}）对应数据表{ent.table}。",
            f"{label}的关键字段包括{_join(model.key_field_labels(cls))}。",
            f"{label}共有{len(persistent)}个持久化字段。",
        ]
        for dcls, name, code in lx.FIELD_DICTIONARIES:
            if dcls == cls:
                sents.append(f"{label}的{model.field_labels[cls][name]}使用{code}字典。")
        docs.append(Doc(
            id=f"entity:{cls}", kind="entity", title=label, text="".join(sents),
            source=f"{cls}.java", meta={"entity_class": cls},
        ))
    return docs


# --------------------------------------------------------------------------- #
# 实体之间的关系
# --------------------------------------------------------------------------- #

_REL_VERB = {"partOf": "属于", "refersTo": "引用"}


def _relation_docs(model: DomainModel) -> List[Doc]:
    docs: List[Doc] = []
    for rel in lx.ENTITY_RELATIONS:
        a, b = model.label(rel.src), model.label(rel.dst)
        text = f"{a}{_REL_VERB[rel.predicate]}{b}，关联字段为{_join(rel.via)}。"
        docs.append(Doc(
            id=f"relation:{rel.src}-{rel.predicate}-{rel.dst}", kind="relation", title=f"{a}→{b}",
            text=text, source=rel.source, meta={"predicate": rel.predicate, "basis": rel.basis},
        ))
    return docs


# --------------------------------------------------------------------------- #
# 常用属性
# --------------------------------------------------------------------------- #


def _attribute_docs(model: DomainModel) -> List[Doc]:
    docs: List[Doc] = []
    basic = model.label("AcAddCodeApplyAttr")
    for a in lx.COMMON_ATTRS:
        sents = [f"{basic}包含常用属性{a.label}。", f"{a.label}（{a.code}）：{a.desc}"]
        if a.derives_from:
            sents.append(f"{a.label}取自{a.derives_from}。")
        docs.append(Doc(
            id=f"attr:{a.code}", kind="attribute", title=a.label, text="".join(sents),
            source=a.source, meta={"attr_code": a.code, "basis": a.basis},
        ))
    docs.append(Doc(
        id="attrs:core", kind="attribute", title=f"{basic}的核心属性",
        text=f"{basic}的核心属性包括{_join(lx.CORE_ATTRS)}。", source=lx.BIZ, meta={"basis": "confirmed"},
    ))
    return docs


# --------------------------------------------------------------------------- #
# 枚举值
# --------------------------------------------------------------------------- #


def _enum_docs(model: DomainModel) -> List[Doc]:
    docs: List[Doc] = []
    for g in lx.ENUM_GROUPS:
        labels = [g.label(v) for v in g.values]
        docs.append(Doc(
            id=f"enum:{g.prefix}", kind="enum", title=f"{g.owner}的枚举值",
            text=f"{g.owner}的枚举值包括{_join(labels)}。", source=g.source, meta={"basis": "confirmed"},
        ))
        for v in g.values:
            label = g.label(v)
            code = f"（{v.code}）" if v.code != v.name else ""
            text = f"{label}{code}：{v.desc}"
            if v.bg:
                text += f"{label}标识{v.bg}的优选物料。"
            docs.append(Doc(
                id=f"enumval:{label}", kind="enum", title=label, text=text, source=g.source,
                meta={"basis": "confirmed", "code": v.code},
            ))
    return docs


def _bg_docs(model: DomainModel) -> List[Doc]:
    return [
        Doc(id=f"bg:{fld}:{bg}", kind="enum", title=f"{fld}→{bg}", text=f"{fld}标明{bg}的物料。",
            source=src, meta={"basis": "confirmed"})
        for fld, bg, src in lx.BG_INDICATORS
    ]


# --------------------------------------------------------------------------- #
# 业务规则
# --------------------------------------------------------------------------- #


def _rule_docs(model: DomainModel) -> List[Doc]:
    docs = [
        Doc(id=f"rule:{r.name}", kind="rule", title=r.name, text=f"{r.name}：{r.text}", source=r.source,
            meta={"basis": r.basis})
        for r in lx.RULES
    ]
    by_name = {r.name: r for r in lx.RULES}
    for cls, names in lx.ENTITY_RULES.items():
        label = model.label(cls)
        for n in names:  # 一条规则一份文档，出处才精确
            docs.append(Doc(
                id=f"governed:{cls}:{n}", kind="rule", title=f"{label}→{n}",
                text=f"{label}受{n}约束。", source=by_name[n].source,
                meta={"entity_class": cls, "basis": by_name[n].basis},
            ))
    return docs


# --------------------------------------------------------------------------- #
# 应用场景
# --------------------------------------------------------------------------- #


def _scenario_docs(model: DomainModel) -> List[Doc]:
    docs: List[Doc] = [
        Doc(id=f"scenario:{n}", kind="scenario", title=n, text=f"{n}：{desc}", source="lexicon.SCENARIOS")
        for n, desc in lx.SCENARIOS
    ]
    for s in lx.SUPPORTS:
        subj = model.node_label(s.subject)
        docs.append(Doc(
            id=f"support:{s.subject}:{s.scenario}", kind="support", title=f"{subj}→{s.scenario}",
            text=f"{subj}支持{s.scenario}。{s.reason}", source=s.source or "lexicon.SUPPORTS",
            meta={"basis": s.basis, "subject": subj, "scenario": s.scenario},
        ))
    return docs


def build_corpus(model: DomainModel) -> List[Doc]:
    docs = (
        _entity_docs(model) + _relation_docs(model) + _attribute_docs(model)
        + _enum_docs(model) + _bg_docs(model) + _rule_docs(model) + _scenario_docs(model)
    )
    ids = [d.id for d in docs]
    assert len(ids) == len(set(ids)), "语料 doc id 重复"
    return docs
