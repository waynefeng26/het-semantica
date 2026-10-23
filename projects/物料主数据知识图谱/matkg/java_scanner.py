"""Java 源码扫描器：把 addcode 模块的源码解析成结构化“事实”。

只依赖正则（不引入 Java 解析器），覆盖本模块用到的 MyBatis-Plus / jeecg 约定：

* 实体类      ``@TableName`` + ``@ApiModelProperty`` / javadoc / ``@Dict``
* 控制器      ``@Api(tags)`` + ``@RequestMapping`` + ``@ApiOperation``
* 服务实现    ``ServiceImpl<Mapper, Entity>`` + 注入依赖 + 方法 javadoc / 注释 / 调用
* 定时任务    ``implements Job`` 的类级 javadoc
* MQ 监听器   ``@RabbitListener``
* Mapper XML  ``FROM/JOIN ... ON a.x = b.y`` → 表间外键证据

扫描结果既是“语料”的原料，也是后续校验时的“金标准事实”(gold facts)。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass
class JavaField:
    name: str
    java_type: str
    label: str = ""
    dict_table: str = ""
    dict_code: str = ""
    dict_text: str = ""
    is_pk: bool = False
    persistent: bool = True  # @TableField(exist = false) → False


@dataclass
class JavaEntity:
    class_name: str
    table: str
    description: str
    path: str
    fields: List[JavaField] = field(default_factory=list)
    package: str = ""


@dataclass
class JavaEndpoint:
    http: str
    path: str
    summary: str
    method_name: str = ""


@dataclass
class JavaController:
    class_name: str
    tag: str
    base_path: str
    path: str
    endpoints: List[JavaEndpoint] = field(default_factory=list)
    deps: List[Tuple[str, str]] = field(default_factory=list)  # (type, field)


@dataclass
class JavaMethod:
    name: str
    doc: str = ""
    comments: List[str] = field(default_factory=list)
    calls: List[Tuple[str, str]] = field(default_factory=list)  # (dep type, method)
    line: int = 0


@dataclass
class JavaService:
    class_name: str
    entity: str  # ServiceImpl<Mapper, Entity> 中的 Entity，可为空
    path: str
    doc: str = ""
    deps: List[Tuple[str, str]] = field(default_factory=list)  # (type, field)
    methods: List[JavaMethod] = field(default_factory=list)


@dataclass
class JavaComponent:
    """Job / Listener / Task / Processor 等非 Controller/Service 的组件。"""

    class_name: str
    kind: str  # job | listener | task | processor | config | util
    path: str
    doc: str = ""
    deps: List[Tuple[str, str]] = field(default_factory=list)
    extra: Dict[str, str] = field(default_factory=dict)


@dataclass
class TableJoin:
    left: str
    left_col: str
    right: str
    right_col: str
    mapper: str


@dataclass
class ScanResult:
    root: str
    entities: List[JavaEntity] = field(default_factory=list)
    controllers: List[JavaController] = field(default_factory=list)
    services: List[JavaService] = field(default_factory=list)
    components: List[JavaComponent] = field(default_factory=list)
    joins: List[TableJoin] = field(default_factory=list)
    readme: str = ""
    file_count: int = 0

    def table_to_entity(self) -> Dict[str, JavaEntity]:
        return {e.table: e for e in self.entities if e.table}

    def class_to_entity(self) -> Dict[str, JavaEntity]:
        return {e.class_name: e for e in self.entities}


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #

_DOC_RE = re.compile(r"/\*\*(.*?)\*/", re.S)
_LIST_MARK = re.compile(r"^(?:<li>\s*|[-•]\s+|\d+[.、)]\s+)")


def read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def clean_doc(raw: str) -> str:
    """把 javadoc 正文清洗成单行中文文本（去标签、{@code}、HTML）。"""
    lines: List[str] = []
    for line in raw.splitlines():
        line = line.strip().lstrip("*").strip()
        if not line:
            continue
        if line.startswith("@"):
            tag = line.split()[0]
            if tag in ("@Description:", "@Description"):
                line = line[len(tag):].strip(": ").strip()
            else:
                continue  # @author / @param / @return / @Date ...
        is_item = bool(_LIST_MARK.match(line))
        line = _LIST_MARK.sub("", line)
        if is_item and lines and not lines[-1].endswith(("。", "；", ";", ".", "：", ":")):
            lines[-1] += "。"
        lines.append(line)
    text = " ".join(lines)
    text = re.sub(r"\{@(?:code|link|linkplain)\s+#?([^}]*)\}", r"\1", text)
    text = re.sub(r"</?\w+[^>]*>", " ", text)
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


_BUILTIN_TYPES = {
    "String", "Integer", "Long", "Double", "Date", "Boolean", "BigDecimal", "Logger",
    "List", "Map", "Set", "Object", "RestTemplate", "ObjectMapper", "int", "long",
}
_DEP_SUFFIX = ("Service", "Mapper", "Util", "Handle", "Api", "API", "Properties", "ServiceImpl",
               "Config", "Handler", "Client", "Template")


def extract_deps(text: str) -> List[Tuple[str, str]]:
    deps: List[Tuple[str, str]] = []
    pattern = re.compile(
        r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*(?:private|protected|public)?\s*(?:final\s+)?"
        r"([A-Z][\w]*)(?:<[^>]*>)?\s+([a-z]\w*)\s*;",
        re.M,
    )
    for m in pattern.finditer(text):
        typ, name = m.group(1), m.group(2)
        if typ in _BUILTIN_TYPES:
            continue
        if typ.endswith(_DEP_SUFFIX) or re.match(r"^I[A-Z]", typ) or "Service" in typ:
            if (typ, name) not in deps:
                deps.append((typ, name))
    return deps


def class_doc(text: str, class_name: str) -> str:
    """类声明之前紧邻的 javadoc。"""
    m = re.search(rf"(/\*\*(?:(?!\*/).)*\*/)\s*(?:@[\w.]+(?:\([^)]*\))?\s*)*(?:public\s+)?(?:abstract\s+)?(?:class|interface)\s+{class_name}\b", text, re.S)
    return clean_doc(m.group(1)[3:-2]) if m else ""


def _find_block_end(text: str, open_idx: int) -> int:
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n - 1


_METHOD_RE = re.compile(
    r"^[ \t]*(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?(?:<[^>]+>\s+)?"
    r"[\w<>\[\],.? ]+?\s+(\w+)\s*\([^;{]*?\)\s*(?:throws\s+[\w., ]+)?\s*\{",
    re.M,
)
_LINE_COMMENT_RE = re.compile(r"^\s*//\s*(.+?)\s*$")


def extract_methods(text: str, deps: List[Tuple[str, str]]) -> List[JavaMethod]:
    dep_map = {name: typ for typ, name in deps}
    methods: List[JavaMethod] = []
    for m in _METHOD_RE.finditer(text):
        name = m.group(1)
        if name in ("if", "for", "while", "switch", "catch", "synchronized"):
            continue
        start = m.start()
        # javadoc：向上跳过注解行
        before = text[:start].rstrip()
        before = re.sub(r"(?:\s*@\w+(?:\([^)]*\))?)+\s*$", "", before).rstrip()
        doc = ""
        if before.endswith("*/"):
            d_start = before.rfind("/**")
            if d_start != -1 and "*/" not in before[d_start + 3:-2]:
                doc = clean_doc(before[d_start + 3:-2])
        open_idx = text.find("{", m.end() - 1)
        end_idx = _find_block_end(text, open_idx)
        body = text[open_idx:end_idx]
        comments: List[str] = []
        for line in body.splitlines():
            lm = _LINE_COMMENT_RE.match(line)
            if not lm:
                continue
            c = lm.group(1).strip("/ ")
            # 只保留含中文且不像被注释掉的代码
            if re.search(r"[\u4e00-\u9fa5]", c) and not re.search(r"[;{}]\s*$|\w+\(.*\)\s*;", c):
                comments.append(c)
        calls: List[Tuple[str, str]] = []
        for cm in re.finditer(r"\b([a-z]\w*)\.(\w+)\(", body):
            recv, meth = cm.group(1), cm.group(2)
            if recv in dep_map and (dep_map[recv], meth) not in calls:
                calls.append((dep_map[recv], meth))
        methods.append(
            JavaMethod(name=name, doc=doc, comments=comments, calls=calls,
                       line=text.count("\n", 0, start) + 1)
        )
    return methods


# --------------------------------------------------------------------------- #
# 实体
# --------------------------------------------------------------------------- #


def parse_entity(path: Path) -> Optional[JavaEntity]:
    text = read_text(path)
    cm = re.search(r"\bclass\s+(\w+)", text)
    if not cm:
        return None
    class_name = cm.group(1)
    tm = re.search(r'@TableName\(\s*(?:value\s*=\s*)?"(\w+)"', text)
    table = tm.group(1) if tm else ""
    desc = ""
    dm = re.search(r"@Description:\s*(.+)", text)
    if dm:
        desc = dm.group(1).strip()
    else:
        am = re.search(r'@ApiModel\([^)]*description\s*=\s*"([^"]+)"', text)
        if am:
            desc = am.group(1)
        else:
            desc = class_doc(text, class_name)
    if not table and not desc:
        return None
    pkg = re.search(r"^package\s+([\w.]+);", text, re.M)
    ent = JavaEntity(class_name=class_name, table=table, description=desc, path=str(path),
                     package=pkg.group(1) if pkg else "")
    lines = text.splitlines()
    pending: Dict[str, object] = {}
    for line in lines:
        s = line.strip()
        if s.startswith("/**") and s.endswith("*/"):
            pending["doc"] = s[3:-2].strip()
            continue
        if s.startswith("@ApiModelProperty"):
            vm = re.search(r'value\s*=\s*"([^"]*)"', s)
            if vm:
                pending["label"] = vm.group(1)
            continue
        if s.startswith("@Dict"):
            for key, k2 in (("dictTable", "dict_table"), ("dicCode", "dict_code"), ("dicText", "dict_text")):
                mm = re.search(rf'{key}\s*=\s*"([^"]*)"', s)
                if mm:
                    pending[k2] = mm.group(1)
            continue
        if s.startswith("@Excel") and "label" not in pending:
            nm = re.search(r'name\s*=\s*"([^"]*)"', s)
            if nm:
                pending["excel"] = nm.group(1)
            continue
        if s.startswith("@TableId"):
            pending["pk"] = True
            continue
        if s.startswith("@TableField") and "exist = false" in s.replace("  ", " "):
            pending["transient"] = True
            continue
        fm = re.match(r"private\s+(?:static\s+)?([\w.<>\[\], ?]+?)\s+(\w+)\s*(?:=.*)?;", s)
        if fm and "serialVersionUID" not in s and "static" not in s.split(fm.group(2))[0]:
            label = str(pending.get("label") or pending.get("excel") or pending.get("doc") or "").strip()
            ent.fields.append(
                JavaField(
                    name=fm.group(2),
                    java_type=fm.group(1).replace("java.lang.", "").replace("java.util.", ""),
                    label=label,
                    dict_table=str(pending.get("dict_table", "")),
                    dict_code=str(pending.get("dict_code", "")),
                    dict_text=str(pending.get("dict_text", "")),
                    is_pk=bool(pending.get("pk")),
                    persistent=not pending.get("transient"),
                )
            )
            pending = {}
        elif s and not s.startswith(("@", "//", "*", "/*")):
            # 遇到其它代码行就清空，避免注解串位
            if not s.startswith(("public", "private", "protected")):
                pending = {}
    return ent


# --------------------------------------------------------------------------- #
# 控制器 / 服务 / 组件
# --------------------------------------------------------------------------- #

_MAPPING_RE = re.compile(r"@(Get|Post|Put|Delete|Request|Patch)Mapping\(([^)]*)\)")


def parse_controller(path: Path) -> Optional[JavaController]:
    text = read_text(path)
    cm = re.search(r"\bclass\s+(\w+Controller)\b", text)
    if not cm:
        return None
    class_name = cm.group(1)
    tag_m = re.search(r'@Api\(\s*tags\s*=\s*"([^"]+)"', text)
    base_m = re.search(r'@RequestMapping\(\s*(?:value\s*=\s*)?"([^"]+)"\)\s*(?:@\w+\s*)*\s*(?:public\s+)?class', text, re.S)
    if not base_m:
        base_m = re.search(r'@RequestMapping\(\s*(?:value\s*=\s*)?"([^"]+)"\)', text)
    ctl = JavaController(
        class_name=class_name,
        tag=tag_m.group(1) if tag_m else class_name,
        base_path=base_m.group(1) if base_m else "",
        path=str(path),
        deps=extract_deps(text),
    )
    # 每个方法：向上收集注解块
    for m in _METHOD_RE.finditer(text):
        start = m.start()
        head = text[:start]
        ann_lines: List[str] = []
        for line in reversed(head.splitlines()):
            s = line.strip()
            if s.startswith("@") or s.startswith("//@") or (s and ann_lines and not s.startswith(("}", "{", "public", "private"))
                                                            and s.endswith(("\"", ")", ","))):
                ann_lines.append(s)
            elif s == "":
                if ann_lines:
                    break
            else:
                break
        block = "\n".join(reversed(ann_lines))
        if block.lstrip().startswith("//"):
            pass
        mm = _MAPPING_RE.search(re.sub(r"^//.*$", "", block, flags=re.M))
        if not mm:
            continue
        http = mm.group(1).upper()
        pm = re.search(r'"([^"]+)"', mm.group(2))
        sm = re.search(r'@ApiOperation\(\s*value\s*=\s*"([^"]+)"', re.sub(r"^//.*$", "", block, flags=re.M))
        if http == "REQUEST":
            http = "ANY"
        ctl.endpoints.append(
            JavaEndpoint(http=http, path=pm.group(1) if pm else "", summary=sm.group(1) if sm else "",
                         method_name=m.group(1))
        )
    return ctl


def parse_service(path: Path) -> Optional[JavaService]:
    text = read_text(path)
    cm = re.search(r"\bclass\s+(\w+)\s+extends\s+ServiceImpl<\s*\w+\s*,\s*(\w+)\s*>", text)
    if cm:
        class_name, entity = cm.group(1), cm.group(2)
    else:
        cm = re.search(r"\bclass\s+(\w+)\b", text)
        if not cm:
            return None
        class_name, entity = cm.group(1), ""
    deps = extract_deps(text)
    return JavaService(
        class_name=class_name,
        entity=entity,
        path=str(path),
        doc=class_doc(text, class_name),
        deps=deps,
        methods=extract_methods(text, deps),
    )


def parse_component(path: Path, kind: str) -> Optional[JavaComponent]:
    text = read_text(path)
    cm = re.search(r"\b(?:class|interface)\s+(\w+)\b", text)
    if not cm:
        return None
    class_name = cm.group(1)
    comp = JavaComponent(
        class_name=class_name, kind=kind, path=str(path), doc=class_doc(text, class_name),
        deps=extract_deps(text),
    )
    q = re.search(r"@RabbitListener\(queues\s*=\s*([\w.]+)", text)
    if q:
        comp.extra["queue"] = q.group(1)
        comp.extra["handles"] = ",".join(sorted(set(re.findall(r'"(\w+)"\.equals\(msgType\)', text))))
    if kind == "job":
        comp.extra["methods"] = ",".join(m.name for m in extract_methods(text, comp.deps))
    return comp


# --------------------------------------------------------------------------- #
# Mapper XML → 表间关联
# --------------------------------------------------------------------------- #

_STMT_RE = re.compile(r"<(select|update|insert|delete)\b[^>]*\bid=\"(\w+)\"[^>]*>(.*?)</\1>", re.S)
_ALIAS_RE = re.compile(r"\b(?:FROM|JOIN|UPDATE)\s+([a-z][a-z0-9_]*)(?:\s+(?:AS\s+)?([a-z]\w*))?", re.I)
_ON_RE = re.compile(r"\b([a-z]\w*)\.(\w+)\s*=\s*([a-z]\w*)\.(\w+)", re.I)
_SQL_KEYWORDS = {"left", "right", "inner", "join", "on", "where", "set", "as", "and", "or", "group", "order", "select", "from"}


def parse_mapper_xml(path: Path) -> List[TableJoin]:
    text = read_text(path)
    joins: List[TableJoin] = []
    for stmt in _STMT_RE.finditer(text):
        body = re.sub(r"<!\[CDATA\[|\]\]>", " ", stmt.group(3))
        alias: Dict[str, str] = {}
        for am in _ALIAS_RE.finditer(body):
            table, al = am.group(1), am.group(2)
            if "_" not in table:
                continue
            alias[table] = table
            if al and al.lower() not in _SQL_KEYWORDS:
                alias[al] = table
        for om in _ON_RE.finditer(body):
            a, ac, b, bc = om.groups()
            lt, rt = alias.get(a), alias.get(b)
            if lt and rt and lt != rt:
                joins.append(TableJoin(lt, ac, rt, bc, path.stem))
    return joins


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #

_KIND_BY_DIR = {"job": "job", "listener": "listener", "task": "task"}


def scan_module(root: str | Path) -> ScanResult:
    root = Path(root)
    result = ScanResult(root=str(root))
    seen_joins = set()
    java_files = sorted(root.rglob("*.java"))
    result.file_count = len(java_files) + len(list(root.rglob("*.xml")))
    for p in java_files:
        rel = p.relative_to(root).parts
        top = rel[0]
        if top == "entity" or (top == "es" and len(rel) > 1 and rel[1] == "entity"):
            ent = parse_entity(p)
            if ent and ent.table:
                result.entities.append(ent)
        elif p.name.endswith("Controller.java"):
            ctl = parse_controller(p)
            if ctl:
                result.controllers.append(ctl)
        elif top == "service" and rel[-2:-1] == ("impl",) or (top == "es" and "impl" in rel and p.name.endswith("Impl.java")):
            svc = parse_service(p)
            if svc:
                result.services.append(svc)
        elif top == "es" and len(rel) > 1 and rel[1] == "service" and not p.name.startswith("I"):
            svc = parse_service(p)
            if svc:
                result.services.append(svc)
        elif top in _KIND_BY_DIR or (top == "es" and len(rel) > 1 and rel[1] == "task"):
            kind = _KIND_BY_DIR.get(top, "task")
            comp = parse_component(p, kind)
            if comp:
                result.components.append(comp)
        elif top == "service" and p.name.endswith("Processor.java"):
            comp = parse_component(p, "processor")
            if comp:
                result.components.append(comp)
        elif top == "util":
            comp = parse_component(p, "util")
            if comp:
                result.components.append(comp)
    # impl 目录下的 Processor 也算组件
    result.services = [s for s in result.services if not s.class_name.endswith("Processor")]
    for p in sorted(root.rglob("*.xml")):
        for j in parse_mapper_xml(p):
            key = (j.left, j.left_col, j.right, j.right_col)
            if key not in seen_joins:
                seen_joins.add(key)
                result.joins.append(j)
    readme = root / "es" / "README.md"
    if readme.exists():
        result.readme = read_text(readme)
    return result
