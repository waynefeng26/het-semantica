"""Semantica 的中文适配层（不修改 semantica 源码，只用它公开的扩展点）。

Semantica 默认的抽取/分析实现是面向英文的（正则 ``\\b``、按空格分词、英文代词表）。
这里通过以下扩展点做中文适配：

* ``method_registry.register("entity"|"relation"|"triplet", name, fn)``
    - ``zh_gazetteer``  实体：领域词表最长匹配（NER）
    - ``zh_rules``      关系 / 三元组：触发词 + 本体 domain/range 约束
* 子类化 :class:`semantica.semantic_extract.SemanticAnalyzer`，替换其
  ``role_labeler`` / ``similarity_analyzer`` / ``semantic_clusterer``：
    - :class:`ZhRoleLabeler`   语义角色（施事 / 受事 / 工具 / 约束 …）
    - :class:`ZhSimilarity`    “词表词 + 字二元组”的相似度
    - :class:`ZhClusterer`     基于上述相似度的语义聚类
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from semantica.semantic_extract import SemanticAnalyzer
from semantica.semantic_extract.registry import method_registry
from semantica.semantic_extract.semantic_analyzer import SemanticCluster, SemanticRole
from semantica.semantic_extract.types import Entity, Relation, Triplet

from . import lexicon as lx
from .domain_model import DomainModel

ZH_NER = "zh_gazetteer"
ZH_REL = "zh_rules"
MARK = "extraction_method"

_SENT_RE = re.compile(r"[^。；;\n]+[。；;]?")
_CUE_RES = [(pred, re.compile(rx)) for pred, rx in lx.RELATION_CUES]
_STOP_RE = re.compile(lx.OBJECT_STOP)
_MASK = "□"


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #


def split_sentences(text: str) -> List[Tuple[int, int]]:
    """按 。；; 换行 切句，返回 (start, end) 区间。"""
    return [(m.start(), m.end()) for m in _SENT_RE.finditer(text) if m.group(0).strip("。；; \n")]


@dataclass
class Binding:
    """一条触发词绑定：谓词 + 主语 + 宾语们（+ 关联字段）。"""

    predicate: str
    cue: str
    cue_start: int
    cue_end: int
    subject: Optional[Entity]
    objects: List[Entity]
    via: List[Entity]
    sentence: str
    sentence_start: int


def _concept_ok(entity: Entity, allowed: Sequence[str]) -> bool:
    return entity.label in allowed


def bind_sentence(text: str, span: Tuple[int, int], entities: List[Entity]) -> List[Binding]:
    """在一个句子里，按触发词把实体绑成 (主语, 谓词, 宾语们)。"""
    s0, s1 = span
    sent = text[s0:s1]
    ents = sorted(
        (e for e in entities if s0 <= e.start_char and e.end_char <= s1 and e.metadata.get(MARK) == ZH_NER),
        key=lambda e: e.start_char,
    )
    if not ents:
        return []

    # 把实体词面遮住，避免实体名里的“管理/生成/依赖…”被当作触发词
    masked = list(sent)
    for e in ents:
        for i in range(e.start_char - s0, e.end_char - s0):
            masked[i] = _MASK
    masked_s = "".join(masked)

    cues: List[Tuple[int, int, str]] = []
    for pred, rx in _CUE_RES:
        for m in rx.finditer(masked_s):
            cues.append((m.start(), m.end(), pred))
    cues.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    kept: List[Tuple[int, int, str]] = []
    for c in cues:
        if kept and c[0] < kept[-1][1]:
            continue
        kept.append(c)

    out: List[Binding] = []
    for idx, (cs, ce, pred) in enumerate(kept):
        pdef = lx.PREDICATES[pred]
        seg_end = kept[idx + 1][0] if idx + 1 < len(kept) else len(sent)
        stop = _STOP_RE.search(masked_s, ce, seg_end)
        obj_end = stop.start() if stop else seg_end

        subj: Optional[Entity] = None
        for e in reversed(ents):
            if e.end_char - s0 <= cs and _concept_ok(e, pdef.domain):
                subj = e
                break
        objs = [
            e for e in ents
            if e.start_char - s0 >= ce and e.end_char - s0 <= obj_end and _concept_ok(e, pdef.range)
        ]
        via: List[Entity] = []
        if stop and stop.group(0) == "关联字段":
            via = [e for e in ents if e.start_char - s0 >= stop.end() and e.label == "Field"]
        if subj is not None and objs:
            out.append(Binding(pred, sent[cs:ce], s0 + cs, s0 + ce, subj, objs, via, sent, s0))
    return out


# --------------------------------------------------------------------------- #
# 方法注册：实体 / 关系 / 三元组
# --------------------------------------------------------------------------- #


def register_methods(model: DomainModel) -> None:
    """向 Semantica 注册中文抽取方法（幂等）。"""
    gaz = model.gazetteer

    def zh_entities(text: str, **kwargs: Any) -> List[Entity]:
        out: List[Entity] = []
        for s, e, term in gaz.find(text):
            out.append(Entity(
                text=text[s:e], label=term.label, start_char=s, end_char=e, confidence=0.95,
                metadata={MARK: ZH_NER, "canonical": term.canonical, "source": term.source},
            ))
        return out

    def zh_relations(text: str, entities: List[Entity], **kwargs: Any) -> List[Relation]:
        rels: List[Relation] = []
        for span in split_sentences(text):
            for b in bind_sentence(text, span, entities):
                for obj in b.objects:
                    rels.append(Relation(
                        subject=b.subject, predicate=b.predicate, object=obj, confidence=0.9,
                        context=b.sentence,
                        metadata={
                            MARK: ZH_REL, "cue": b.cue, "sentence_start": b.sentence_start,
                            "via": [model.gazetteer.canonical_of(v.text) for v in b.via],
                        },
                    ))
        return rels

    def zh_triplets(text: str, entities: Optional[List[Entity]] = None,
                    relations: Optional[List[Relation]] = None, **kwargs: Any) -> List[Triplet]:
        if not entities:
            entities = zh_entities(text)
        if not relations:
            relations = zh_relations(text, entities)
        seen: Dict[Tuple[str, str, str], Triplet] = {}
        for r in relations:
            if r.metadata.get(MARK) != ZH_REL:  # 过滤框架的英文兜底关系
                continue
            s = gaz.canonical_of(r.subject.text)
            o = gaz.canonical_of(r.object.text)
            key = (s, r.predicate, o)
            if key in seen:
                continue
            seen[key] = Triplet(
                subject=s, predicate=r.predicate, object=o, confidence=r.confidence,
                metadata={
                    MARK: ZH_REL,
                    "subject_type": r.subject.label, "object_type": r.object.label,
                    "cue": r.metadata.get("cue"), "via": r.metadata.get("via", []),
                    "sentence": r.context,
                },
            )
        return list(seen.values())

    method_registry.register("entity", ZH_NER, zh_entities)
    method_registry.register("relation", ZH_REL, zh_relations)
    method_registry.register("triplet", ZH_REL, zh_triplets)


# --------------------------------------------------------------------------- #
# 语义分析：分词 / 相似度 / 角色 / 聚类
# --------------------------------------------------------------------------- #

_BOILER = re.compile(
    "|".join(rx for _, rx in lx.RELATION_CUES)
    + r"|关联字段为|处理说明|共有\d+个持久化字段|[，。；：、（）()\s]"
)


class ZhTokenizer:
    """领域词表词 + 字二元组。词表词作为整体 token（带概念前缀），其余文字切字二元组。"""

    def __init__(self, model: DomainModel) -> None:
        self.gaz = model.gazetteer

    def tokens(self, text: str) -> List[str]:
        toks: List[str] = []
        rest = list(text)
        for s, e, term in self.gaz.find(text):
            toks.append(f"{term.label}:{term.canonical}")
            for i in range(s, e):
                rest[i] = " "
        left = _BOILER.sub(" ", "".join(rest))
        for chunk in left.split():
            if len(chunk) == 1:
                toks.append(f"c:{chunk}")
            else:
                toks.extend(f"b:{chunk[i:i + 2]}" for i in range(len(chunk) - 1))
        return toks


class ZhSimilarity:
    """替换 SimilarityAnalyzer：Jaccard / 余弦（tf）。"""

    def __init__(self, tokenizer: ZhTokenizer, **config: Any) -> None:
        self.tk = tokenizer
        self.config = config

    def calculate_similarity(self, text1: str, text2: str, **options: Any) -> float:
        method = options.get("method", "cosine")
        a, b = self.tk.tokens(text1), self.tk.tokens(text2)
        if method == "jaccard":
            sa, sb = set(a), set(b)
            return len(sa & sb) / len(sa | sb) if sa | sb else 0.0
        ca, cb = Counter(a), Counter(b)
        dot = sum(ca[t] * cb[t] for t in ca.keys() & cb.keys())
        na = math.sqrt(sum(v * v for v in ca.values()))
        nb = math.sqrt(sum(v * v for v in cb.values()))
        return dot / (na * nb) if na and nb else 0.0


_ROLE_OF_PREDICATE: Dict[str, str] = {
    "mapsToTable": "location",
    "hasKeyField": "attribute",
    "partOf": "theme",
    "refersTo": "theme",
    "usesDictionary": "resource",
    "includesAttribute": "attribute",
    "hasCoreAttribute": "attribute",
    "derivesFrom": "source",
    "governedBy": "constraint",
    "supports": "purpose",
    "hasValue": "value",
    "preferredFor": "beneficiary",
    "indicatesBG": "indicator",
}


class ZhRoleLabeler:
    """替换 RoleLabeler：施事 / 受事 / 来源 / 目标 / 工具 / 结果 / 约束 …

    角色由“触发词 + 本体 domain/range”确定，因此只对能绑定到谓词的提及打角色。
    """

    def __init__(self, model: DomainModel, **config: Any) -> None:
        self.model = model
        self.config = config

    def label_roles(self, text: str, **options: Any) -> List[SemanticRole]:
        gaz = self.model.gazetteer
        entities = [
            Entity(text=text[s:e], label=t.label, start_char=s, end_char=e, confidence=0.95,
                   metadata={MARK: ZH_NER, "canonical": t.canonical})
            for s, e, t in gaz.find(text)
        ]
        roles: List[SemanticRole] = []
        for si, span in enumerate(split_sentences(text)):
            for b in bind_sentence(text, span, entities):
                common = {"predicate": b.predicate, "sentence_index": si}
                roles.append(SemanticRole(
                    word=b.cue, role="predicate", start_char=b.cue_start, end_char=b.cue_end,
                    confidence=0.9, metadata={**common, "predicate_zh": lx.PREDICATES[b.predicate].zh},
                ))
                s = b.subject
                roles.append(SemanticRole(
                    word=s.text, role="agent", start_char=s.start_char, end_char=s.end_char, confidence=0.85,
                    metadata={**common, "concept": s.label, "canonical": gaz.canonical_of(s.text)},
                ))
                orole = _ROLE_OF_PREDICATE[b.predicate]
                for o in b.objects:
                    roles.append(SemanticRole(
                        word=o.text, role=orole, start_char=o.start_char, end_char=o.end_char, confidence=0.85,
                        metadata={**common, "concept": o.label, "canonical": gaz.canonical_of(o.text)},
                    ))
                for v in b.via:
                    roles.append(SemanticRole(
                        word=v.text, role="key", start_char=v.start_char, end_char=v.end_char, confidence=0.8,
                        metadata={**common, "concept": v.label, "canonical": gaz.canonical_of(v.text)},
                    ))
        return roles


class ZhClusterer:
    """替换 SemanticClusterer：与框架同样的“种子 + 阈值”策略，但使用中文相似度。"""

    def __init__(self, similarity: ZhSimilarity, **config: Any) -> None:
        self.similarity = similarity
        self.config = config

    def cluster(self, texts: Sequence[Union[str, Dict[str, Any]]], **options: Any) -> List[SemanticCluster]:
        threshold = options.get("similarity_threshold", 0.5)
        method = options.get("method", "cosine")
        contents: List[str] = []
        ids: List[Optional[str]] = []
        for item in texts:
            if isinstance(item, dict):
                contents.append(item.get("content", str(item)))
                ids.append(item.get("id"))
            else:
                contents.append(str(item))
                ids.append(None)

        assigned: set = set()
        clusters: List[SemanticCluster] = []
        for i, ti in enumerate(contents):
            if i in assigned:
                continue
            members = [i]
            assigned.add(i)
            sims: List[float] = []
            for j in range(i + 1, len(contents)):
                if j in assigned:
                    continue
                s = self.similarity.calculate_similarity(ti, contents[j], method=method)
                if s >= threshold:
                    members.append(j)
                    assigned.add(j)
                    sims.append(s)
            clusters.append(SemanticCluster(
                texts=[contents[k] for k in members],
                cluster_id=len(clusters),
                centroid=contents[i],
                similarity_score=sum(sims) / len(sims) if sims else 1.0,
                metadata={"doc_ids": [ids[k] for k in members], "size": len(members), "seed": ids[i]},
            ))
        return clusters


class ZhSemanticAnalyzer(SemanticAnalyzer):
    """中文语义分析器：替换角色标注 / 相似度 / 聚类，并重写特征统计。"""

    def __init__(self, model: DomainModel, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.model = model
        self.tokenizer = ZhTokenizer(model)
        self.similarity_analyzer = ZhSimilarity(self.tokenizer)
        self.role_labeler = ZhRoleLabeler(model)
        self.semantic_clusterer = ZhClusterer(self.similarity_analyzer)

    def analyze_semantics(self, text: str, **options: Any) -> Dict[str, Any]:
        sentences = split_sentences(text)
        result: Dict[str, Any] = {
            "text": text,
            "length": len(text),
            "sentence_count": len(sentences),
        }
        if options.get("label_roles", False):
            result["semantic_roles"] = [r.__dict__ for r in self.label_semantic_roles(text, **options)]
        result["semantic_features"] = self._extract_features(text)
        return result

    def _extract_features(self, text: str) -> Dict[str, Any]:
        hits = self.model.gazetteer.find(text)
        by_concept = Counter(t.label for _, _, t in hits)
        canon = {t.canonical for _, _, t in hits}
        toks = self.tokenizer.tokens(text)
        return {
            "mention_count": len(hits),
            "unique_entities": len(canon),
            "mentions_by_concept": dict(by_concept),
            "token_count": len(toks),
            "unique_tokens": len(set(toks)),
        }
