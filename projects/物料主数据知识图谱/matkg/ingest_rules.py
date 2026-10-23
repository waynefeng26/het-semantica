"""入图前的数据约束（供后续“校验 / 导出”阶段使用）。

业务口径（见 ``lexicon`` 里的“有效物料判定规则”“物料升级规则”“物料编码BG前缀规则”）：

* 申请状态 0草稿 / 1标准化审批中 / 2审批完成 / 3SCM采购审批中 / 4退回 / 5历史版本
* 物料升级会新建一条记录，物料编码不变；新记录审批通过后改为 2，原来为 2 的改为 5
  → 同一物料编码，申请状态为 2 的记录**有且只有一条**
* 进入图数据库的物料主数据，申请状态必须始终为 2
* 汽车电子BG的物料编码以 2 开头，其他BG以 1 开头；是否汽车电子为是 ⇔ 汽车电子BG（行里带 ``ecar`` 时一并校验）

这里只做规则本身（纯函数，不连数据库），当前三个阶段的语料来自源码，不涉及物料行数据，
所以暂不接入流水线；等有真实物料数据时由“校验”阶段调用。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping

from . import lexicon as lx

NON_EFFECTIVE = "non_effective_status"  # 申请状态不是 2，不应入图
DUPLICATE_EFFECTIVE = "duplicate_effective"  # 同一物料编码有多条状态为 2 的记录
BAD_CODE_PREFIX = "bad_code_prefix"  # 物料编码首位不是 1 / 2
ECAR_MISMATCH = "ecar_mismatch"  # 是否汽车电子与编码首位不一致（汽电 ⇔ 以 2 开头）


def _status(row: Mapping[str, Any]) -> Any:
    v = row.get("apply_status", row.get("applyStatus"))
    try:
        return int(v)
    except (TypeError, ValueError):
        return v


def _no(row: Mapping[str, Any]) -> str:
    return str(row.get("material_no", row.get("materialNo", "")) or "")


def validate_material_rows(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """检查待入图的物料主数据行，返回违规项（空列表 = 通过）。

    行里需要 ``material_no`` / ``apply_status``（也接受驼峰的 ``materialNo`` / ``applyStatus``）。
    """
    rows = list(rows)
    out: List[Dict[str, Any]] = []
    effective: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)

    for r in rows:
        no, st = _no(r), _status(r)
        if st != lx.APPLY_STATUS_EFFECTIVE:
            out.append({"type": NON_EFFECTIVE, "material_no": no, "apply_status": st,
                        "message": f"物料 {no} 的申请状态为 {st}，入图数据必须为 {lx.APPLY_STATUS_EFFECTIVE}"})
            continue
        effective[no].append(r)
        if not no or no[0] not in "12":
            out.append({"type": BAD_CODE_PREFIX, "material_no": no,
                        "message": f"物料编码 {no!r} 首位应为 1（非汽车电子BG）或 2（汽车电子BG）"})
        elif "ecar" in r and r["ecar"] is not None and (str(r["ecar"]) == "1") != (no[0] == "2"):
            out.append({"type": ECAR_MISMATCH, "material_no": no, "ecar": r["ecar"],
                        "message": f"物料 {no} 的是否汽车电子为 {r['ecar']}，与编码首位 {no[0]} 不一致"})

    for no, items in effective.items():
        if len(items) > 1:
            out.append({"type": DUPLICATE_EFFECTIVE, "material_no": no, "count": len(items),
                        "message": f"物料编码 {no} 有 {len(items)} 条申请状态为 2 的记录，应只有 1 条"})
    return out


def ensure_ingestable(rows: Iterable[Mapping[str, Any]]) -> None:
    """有违规项就抛 ValueError（供入图前强制校验）。"""
    problems = validate_material_rows(rows)
    if problems:
        raise ValueError("物料主数据不满足入图条件：\n" + "\n".join(p["message"] for p in problems))
