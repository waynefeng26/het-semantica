"""领域知识：本体 + 范围内实体的业务口径、关联、规则、常用属性、应用场景。

目标：让 agent 理解公司物料主数据的结构，从而更准确地 **查找物料、推荐替代料、查找相似物料**。
因此只保留“数据结构 / 数据语义”层面的知识；service 层的调用关系、读写关系不进图谱，
只作为阅读源码、整理规则时的参考（出处写在 ``source`` 里）。

每条人工整理的内容都带 ``source``（Java 类#方法 / Mapper XML）；
“应用场景”相关的支撑关系带 ``basis``：
    confirmed 业务方明确说明
    code      源码里有直接证据
    inferred  根据字段含义推断，源码未直接使用 —— 需要业务方确认
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 1. 本体
# --------------------------------------------------------------------------- #

CONCEPTS: Dict[str, str] = {
    "Entity": "业务实体",
    "DataTable": "数据表",
    "Field": "字段",
    "Dictionary": "数据字典",
    "CommonAttribute": "常用属性",
    "BusinessRule": "业务规则",
    "Scenario": "应用场景",
    "EnumValue": "枚举值",
    "BusinessGroup": "业务群(BG)",
}


@dataclass(frozen=True)
class PredicateDef:
    name: str
    zh: str
    domain: FrozenSet[str]
    range: FrozenSet[str]


def _p(name: str, zh: str, domain: List[str], rng: List[str]) -> PredicateDef:
    return PredicateDef(name, zh, frozenset(domain), frozenset(rng))


PREDICATES: Dict[str, PredicateDef] = {
    p.name: p
    for p in [
        # 结构
        _p("mapsToTable", "映射到数据表", ["Entity"], ["DataTable"]),
        _p("hasKeyField", "包含关键字段", ["Entity"], ["Field"]),
        _p("refersTo", "引用", ["Entity"], ["Entity"]),
        _p("partOf", "属于", ["Entity"], ["Entity"]),
        _p("usesDictionary", "使用字典", ["Field"], ["Dictionary"]),
        # 语义
        _p("includesAttribute", "包含常用属性", ["Entity"], ["CommonAttribute"]),
        _p("derivesFrom", "取自", ["CommonAttribute"], ["Field"]),
        _p("governedBy", "受规则约束", ["Entity"], ["BusinessRule"]),
        _p("supports", "支持场景", ["Entity", "Field", "CommonAttribute"], ["Scenario"]),
        _p("hasValue", "枚举值", ["Field", "CommonAttribute"], ["EnumValue"]),
        _p("preferredFor", "标识优选物料所属BG", ["EnumValue"], ["BusinessGroup"]),
        _p("indicatesBG", "标明所属BG", ["Field"], ["BusinessGroup"]),
        _p("similarTo", "语义相近", ["Entity"], ["Entity"]),  # 仅由语义分析推断，不来自文本
    ]
}


def ontology_dict() -> Dict[str, list]:
    """转换成 ``ExtractionSchema.from_ontology`` 认可的 dict（后续“校验”阶段使用）。"""
    return {
        "classes": [{"name": n, "label": zh} for n, zh in CONCEPTS.items()],
        "properties": [
            {"name": p.name, "label": p.zh, "domain": sorted(p.domain), "range": sorted(p.range)}
            for p in PREDICATES.values()
        ],
    }


# --------------------------------------------------------------------------- #
# 2. 范围内的实体
# --------------------------------------------------------------------------- #

SCOPE_ENTITIES: List[str] = [
    "AddCodeApply",
    "AcAddCodeApplyAttr",
    "AcAddCodeApplyAttrp",
    "ClassificationManagement",
    "AttributeManagement",
    "ClassificationAttributeRef",
    "AttributeValue",
    "CodeRange",
]

# 业务口径的规范名（节点名）。前三项由业务方明确给出：
#   加码申请表 = 物料主数据表；加码申请基础属性 = 物料基础属性；
#   加码申请私有属性 = 物料私有属性（也叫物料技术属性）。
# 其余五项按“同理”推出，待业务方确认。
ENTITY_LABELS: Dict[str, str] = {
    "AddCodeApply": "物料主数据",
    "AcAddCodeApplyAttr": "物料基础属性",
    "AcAddCodeApplyAttrp": "物料私有属性",
    "ClassificationManagement": "物料分类",
    "AttributeManagement": "物料属性定义",
    "ClassificationAttributeRef": "物料分类属性模板",
    "AttributeValue": "物料属性值库",
    "CodeRange": "物料编码号段",
}

# 源码 / 技术侧的叫法，都归并到上面的规范名
ENTITY_TECH_NAMES: Dict[str, str] = {
    "AddCodeApply": "加码申请",
    "AcAddCodeApplyAttr": "加码申请基础属性",
    "AcAddCodeApplyAttrp": "加码申请私有属性",
    "ClassificationManagement": "分类维护",
    "AttributeManagement": "属性维护",
    "ClassificationAttributeRef": "分类属性维护",
    "AttributeValue": "属性值库维护",
    "CodeRange": "编码范围",
}

ENTITY_ALIASES: Dict[str, List[str]] = {
    "AddCodeApply": ["加码申请表", "物料主数据表"],
    "AcAddCodeApplyAttr": ["基础属性", "公有属性", "物料公有属性"],
    "AcAddCodeApplyAttrp": ["私有属性", "物料技术属性", "技术属性"],
    "ClassificationManagement": ["物料分类维护"],
    "ClassificationAttributeRef": ["分类属性模板", "属性模板"],
    "CodeRange": ["编码号段"],
}

# 业务口径说明（写进语料；不要出现抽取触发词：属于/引用/使用/取自/支持/受…约束/包含常用属性）
ENTITY_BUSINESS_DESC: Dict[str, str] = {
    "AddCodeApply": "即加码申请表，业务上是物料主数据表，一行对应一个物料，记录物料编码、L1至L4分类、物料描述和申请状态。",
    "AcAddCodeApplyAttr": "即加码申请基础属性，业务上是物料基础属性，也叫公有属性，是同一分类下物料共有的属性取值。",
    "AcAddCodeApplyAttrp": "即加码申请私有属性，业务上是物料私有属性，也叫物料技术属性，是各分类自己特有的技术参数取值。",
    "ClassificationManagement": "即分类维护，业务上是物料分类体系，分为L1至L4四级，L4是最末级分类。",
    "AttributeManagement": "即属性维护，业务上是物料属性的定义清单，每个属性有属性代码和属性名称。",
    "ClassificationAttributeRef": "即分类属性维护，业务上是物料分类属性模板，规定某个分类下有哪些属性、公有还是私有、必填与否、描述拼接顺序。",
    "AttributeValue": "即属性值库维护，业务上是物料属性值库，保存单选、多选类属性的可选值及其描述。",
    "CodeRange": "即编码范围，业务上是物料编码号段，按L4分类划分起止号段并记录当前最大编码，用于顺序分配物料编码。",
}

# 每个实体的“关键字段”（Java 字段名；中文名取自 @ApiModelProperty）
KEY_FIELDS: Dict[str, List[str]] = {
    "AddCodeApply": [
        "classifyL1", "classifyL2", "classifyL3", "classifyL4", "materialNo", "oldMaterialNo",
        "shortDesc", "longDesc", "englishDesc", "applyStatus", "tempCode", "ecar",
    ],
    "AcAddCodeApplyAttr": ["addCodeId", "attrCode", "attrValue", "attrDesc", "attrType"],
    "AcAddCodeApplyAttrp": ["addCodeId", "attrCode", "attrValue", "attrDesc", "attrType"],
    "ClassificationManagement": [
        "firstCode", "secondCode", "thirdCode", "fourCode", "fourName", "compMeterialShort", "preferred", "standardType",
    ],
    "AttributeManagement": ["attributeCode", "attributeName"],
    "ClassificationAttributeRef": [
        "fourCode", "attributeCode", "pubPri", "attributeType", "comparabilityFlag", "uniqueFlag",
        "phraseDescOrder", "erpPhraseDescFlag", "groupAttribute", "groupAttributeJoin", "requiredFalg", "defaultValue",
    ],
    "AttributeValue": ["fourCode", "attributeCode", "itemCode", "value", "valueDesc"],
    "CodeRange": [
        "fourCode", "startNumber", "endNumber", "currentNumber",
        "startNumberCars", "endNumberCars", "currentNumberCars", "materialType",
    ],
}

# 字段 → 字典（来自 @Dict(dicCode=...)）
FIELD_DICTIONARIES: List[Tuple[str, str, str]] = [
    # (实体类, Java 字段名, 字典编码)
    ("ClassificationAttributeRef", "pubPri", "pubOrPri"),
    ("ClassificationAttributeRef", "attributeType", "attrType"),
    ("ClassificationAttributeRef", "smc", "smc"),
    ("AddCodeApply", "ecar", "yn"),
    ("AddCodeApply", "tempCode", "yn"),
]


# --------------------------------------------------------------------------- #
# 3. 实体之间的关系（带证据）
# --------------------------------------------------------------------------- #


@dataclass
class EntityRelation:
    src: str  # 实体类
    predicate: str  # refersTo | partOf
    dst: str
    via: List[str]  # 关联字段（中文名，需在 gazetteer 里存在）
    source: str  # 证据出处
    basis: str = "code"


ENTITY_RELATIONS: List[EntityRelation] = [
    EntityRelation("AcAddCodeApplyAttr", "partOf", "AddCodeApply", ["加码id"],
                   "AcAddCodeApplyAttrMapper.xml#selectByMainId (add_code_id = #{mainId})"),
    EntityRelation("AcAddCodeApplyAttrp", "partOf", "AddCodeApply", ["加码id"],
                   "AcAddCodeApplyAttrpMapper.xml#selectByMainId (add_code_id = #{mainId})"),
    EntityRelation("AddCodeApply", "refersTo", "ClassificationManagement", ["L1分类", "L2分类", "L3分类", "L4分类"],
                   "AddCodeApply.java @Dict(dictTable=ac_classification_management)"),
    EntityRelation("AddCodeApply", "refersTo", "CodeRange", ["L4分类"],
                   "CodeRangeServiceImpl#getCodeAndCommit (four_code = classifyL4 或 classifyL1+010101)"),
    EntityRelation("ClassificationAttributeRef", "refersTo", "ClassificationManagement", ["L4分类代码"],
                   "ClassificationAttributeRefController#queryById (classificationManagementService.queryByFourCode)"),
    EntityRelation("ClassificationAttributeRef", "refersTo", "AttributeManagement", ["属性代码"],
                   "ClassificationAttributeRef.attributeCode 与 AttributeManagement.attributeCode 同名同义（未见显式 JOIN）",
                   basis="inferred"),
    EntityRelation("AttributeValue", "refersTo", "ClassificationAttributeRef", ["L4分类代码", "属性代码"],
                   "ClassificationAttributeRefServiceImpl#getParsedValue (queryRangeByFourCode(ref.fourCode, ref.attributeCode))"),
    EntityRelation("AttributeValue", "refersTo", "AttributeManagement", ["属性代码"],
                   "AttributeValueServiceImpl#getSubdivisionDesc (attribute_code 过滤)"),
    EntityRelation("CodeRange", "refersTo", "ClassificationManagement", ["L4分类代码"],
                   "ClassificationManagementController#page (codeRangeService.getByFourcode(record.fourCode))"),
    EntityRelation("AcAddCodeApplyAttr", "refersTo", "ClassificationAttributeRef", ["属性代码"],
                   "AddCodeApplyServiceImpl#buildAttrList (attr.setAttrCode(ref.getAttributeCode()))"),
    EntityRelation("AcAddCodeApplyAttrp", "refersTo", "ClassificationAttributeRef", ["属性代码"],
                   "AddCodeApplyServiceImpl#buildAttrpList (attrp.setAttrCode(ref.getAttributeCode()))"),
]


# --------------------------------------------------------------------------- #
# 4. 业务规则（只保留影响“数据怎么存、怎么找”的规则）
# --------------------------------------------------------------------------- #

BIZ = "业务方说明"

# 依据等级：confirmed（业务方说明）> code（源码）> inferred（推断）
BASIS_RANK = {"confirmed": 2, "code": 1, "inferred": 0}

# 申请状态：物料升级时同一物料编码会有多条记录，只有这个状态的记录才是“当前有效”的数据
APPLY_STATUS_EFFECTIVE = 2
APPLY_STATUS_HISTORY = 5


@dataclass
class RuleDef:
    name: str
    text: str
    source: str
    basis: str = "code"


RULES: List[RuleDef] = [
    RuleDef(
        "有效物料判定规则",
        "物料主数据的申请状态表示申请审批状态，申请状态为2即审批完成的记录才是有效物料。"
        "同一个物料编码，申请状态为2的记录只有一条，进入图数据库的物料主数据只取申请状态为2的记录。",
        BIZ, "confirmed",
    ),
    RuleDef(
        "物料升级规则",
        "物料升级时会新建一条物料主数据，物料编码保持不变；"
        "新建的升级记录审批通过后，申请状态改为2，原来申请状态为2的记录改为5即历史版本，"
        "因此同一物料编码始终只有一条有效记录。",
        BIZ, "confirmed",
    ),
    RuleDef(
        "物料状态口径规则",
        "物料在业务上的物料状态以生命周期阶段属性为准。",
        BIZ, "confirmed",
    ),
    RuleDef(
        "物料编码BG前缀规则",
        "汽车电子BG的物料编码以2开头，其他BG的物料编码以1开头；汽车电子BG的物料，其是否汽车电子为是。",
        BIZ, "confirmed",
    ),
    RuleDef(
        "客户专用料规则",
        "专用客户属性有值的物料是客户专用料。属性值与客户名称、客户编码并不相等，但从字面上能看出是哪个客户，"
        "目前可选的客户只有两个。研发查找物料时可以过滤掉客户专用料。",
        BIZ, "confirmed",
    ),
    RuleDef(
        "分类代码层级规则",
        "L4分类代码的前两位就是L1分类代码；物料主数据的L1分类、L2分类、L3分类、L4分类，"
        "分别对应物料分类里的L1分类代码、L2分类代码、L3分类代码、L4分类代码。",
        "ClassificationAttributeRefServiceImpl#queryrangeCodeByfourCode (fourCode.substring(0, 2)); AddCodeApply.java @Dict",
    ),
    RuleDef(
        "分类属性范围匹配规则",
        "物料分类属性模板与物料属性值库的L4分类代码有三种写法：具体的L4分类代码、L1分类代码，"
        "以及形如起始-终止的L1分类范围。按L4分类代码查询时，命中任意一种写法的记录都会返回，"
        "并按排序和物料短描述顺序排列。",
        "ClassificationAttributeRefMapper.xml#queryrangeCodeByfourCode; AttributeValueMapper#queryRangeByFourCode",
    ),
    RuleDef(
        "属性值解析规则",
        "解析分类属性时，属性类型为single、multiple、list或multList的属性，"
        "要到物料属性值库里查询可选值；其他类型的属性可选值为空。",
        "ClassificationAttributeRefServiceImpl#getParsedValue",
    ),
    RuleDef(
        "物料描述拼接规则",
        "物料短描述和英文描述取是否进ERP物料短描述标识为X或XY的属性，物料长描述取标识为Y或XY的属性，"
        "均按物料短描述顺序升序拼接；顺序小于1000的作为前缀，大于1000的作为后缀，私有属性夹在前缀和后缀之间；"
        "同一成组属性之间用成组属性拼接符连接，其余用空格连接。",
        "AddCodeApplyServiceImpl#generateDescriptions",
    ),
    RuleDef(
        "物料基础属性取值规则",
        "创建物料基础属性时，物料名称属性取自物料分类的物料子类L4，物料简称属性取自物料分类的元器件物料简称，"
        "物料类型属性取自物料编码号段的物料类型，其余属性按申请信息填充。",
        "AddCodeApplyServiceImpl#createPublicAttributes",
    ),
    RuleDef(
        "编码号段选取规则",
        "L1分类为38，或L4分类为40120101时，取该L4分类自己的号段；其他情况取L1分类加010101对应的号段。",
        "CodeRangeServiceImpl#getCodeAndCommit",
    ),
    RuleDef(
        "汽车电子号段规则",
        "汽车电子物料（即汽车电子BG的物料）使用汽车电子编码起始、汽车电子编码终止和汽车电子当前最大编码三个号段字段，"
        "其他物料使用普通的编码起始、编码终止和当前最大编码。",
        "CodeRangeServiceImpl#getCodeAndCommit (addCodeApply.getEcar() == 1)",
    ),
    RuleDef(
        "旧物料编码校验规则",
        "物料沿用旧物料编码时，旧物料编码必须是11位数字，不能与已有物料编码重复，"
        "且前4位必须与新生成编码的前4位一致。",
        "CodeRangeServiceImpl#getCodeAndCommit",
    ),
]

# 规则 → 约束的实体（类名）
ENTITY_RULES: Dict[str, List[str]] = {
    "AddCodeApply": [
        "有效物料判定规则", "物料升级规则", "物料状态口径规则", "物料编码BG前缀规则",
        "物料描述拼接规则", "旧物料编码校验规则", "分类代码层级规则",
    ],
    "AcAddCodeApplyAttr": ["物料基础属性取值规则", "客户专用料规则"],
    "ClassificationManagement": ["分类代码层级规则"],
    "ClassificationAttributeRef": ["分类属性范围匹配规则", "属性值解析规则", "物料描述拼接规则"],
    "AttributeValue": ["分类属性范围匹配规则", "属性值解析规则"],
    "CodeRange": ["编码号段选取规则", "汽车电子号段规则"],
}


# --------------------------------------------------------------------------- #
# 5. 常用属性（物料基础属性里常用的 attr_code）
# --------------------------------------------------------------------------- #


@dataclass
class CommonAttr:
    label: str  # 规范名（节点名）
    code: str  # attr_code
    desc: str  # 业务口径（不要出现触发词）
    derives_from: Optional[str]  # 取值来源字段（中文名）
    source: str
    basis: str = "code"


COMMON_ATTRS: List[CommonAttr] = [
    CommonAttr("物料名称属性", "materialName", "物料的名称，创建时默认就是物料子类L4的名称。", "物料子类L4",
               "AcAddCodeApplyAttrMapper.xml#getMaterialNameByMaterialNo; AddCodeApplyServiceImpl#createPublicAttributes"),
    CommonAttr("物料简称属性", "materialAbbreviation", "物料的简称，创建时默认来自分类上的元器件物料简称。", "元器件物料简称",
               "AddCodeApplyServiceImpl#createPublicAttributes"),
    CommonAttr("物料类型属性", "materialType", "物料类型，创建时默认来自所在号段的物料类型。", "物料类型",
               "AddCodeApplyServiceImpl#createPublicAttributes"),
    CommonAttr("生命周期阶段属性", "lifeCyclePhase",
               "物料在业务上的物料状态，分为研发、测试、试产、批量、EOL、部分失效、采购失效、完全失效、完全停产。", None,
               BIZ + "; AddCodeApplyController#checkLifeCyclePhase", "confirmed"),
    CommonAttr("优选标识属性", "preferredIdentification",
               "由采购维护，标记物料是否为某个BG的优选物料；被标记为优选的物料，研发设计BOM时会优先考虑。", None,
               BIZ + "; AcAddCodeApplyAttrServiceImpl#batchUpdateMaterialAttributes", "confirmed"),
    CommonAttr("制造商AVL等级属性", "manufacturerAvlRating",
               "物料对应制造商的AVL等级，每天晚上定时根据采购维护的制造商等级更新；"
               "研发设计BOM时优先考虑主力、合格、试用的物料。", None,
               BIZ + "; AddCodeApplyController#checkParam", "confirmed"),
    CommonAttr("专用客户属性", "notes",
               "该属性有值表示物料是某个客户的专用料，属性值就是指定的专用客户；"
               "属性值与客户名称、客户编码并不相等，但从字面上能看出是同一个客户。", None, BIZ, "confirmed"),
    CommonAttr("制造商名称属性", "manufacturersName", "物料对应的制造商名称。", None,
               "AcAddCodeApplyAttrServiceImpl#getByMainIdAndPurchase"),
    CommonAttr("项目类型属性", "projectType", "物料所属项目的类型。", None,
               "AcAddCodeApplyAttrServiceImpl#getByMainIdAndPurchase"),
    CommonAttr("品牌异常类型属性", "brandExceptionType",
               "品牌异常的类型；制造商AVL等级为考察、限制时必填，为主力、合格、试用时不能填写。", None,
               "AddCodeApplyController#checkParam"),
    CommonAttr("细分类属性", "subdivision", "物料的细分类，取值的描述存放在物料属性值库里。", None,
               "AttributeValueServiceImpl#getSubdivisionDesc"),
    CommonAttr("文档编号属性", "documentNumber", "物料关联的文档编号。", None,
               "AddCodeApplyServiceImpl#handleNeed"),
]


# --------------------------------------------------------------------------- #
# 6. 枚举值 / 业务群
# --------------------------------------------------------------------------- #

BUSINESS_GROUPS: List[str] = ["海外家电BG", "国内家电BG", "汽车电子BG"]


# 字段 → 标明的 BG（业务方确认：是否汽车电子 = 汽车电子BG）
BG_INDICATORS: List[Tuple[str, str, str]] = [
    ("是否汽车电子", "汽车电子BG", BIZ + "; CodeRangeServiceImpl#getCodeAndCommit (ecar == 1)"),
]


@dataclass
class EnumValueDef:
    code: str
    name: str
    desc: str
    bg: Optional[str] = None  # 仅优选标识：该值标识哪个 BG 的优选物料


@dataclass
class EnumGroup:
    owner: str  # 字段中文名 | 常用属性规范名
    prefix: str  # 枚举值节点名前缀：“{prefix}-{name}”
    values: List[EnumValueDef]
    source: str = BIZ

    def label(self, v: EnumValueDef) -> str:
        return f"{self.prefix}-{v.name}"


ENUM_GROUPS: List[EnumGroup] = [
    EnumGroup("申请状态", "申请状态", [
        EnumValueDef("0", "草稿", "申请还没有提交。"),
        EnumValueDef("1", "标准化审批中", "申请已提交，正在标准化审批。"),
        EnumValueDef("2", "审批完成", "审批通过的有效数据，同一物料编码只有一条。"),
        EnumValueDef("3", "SCM采购审批中", "申请正在SCM采购审批。"),
        EnumValueDef("4", "退回", "申请被退回。"),
        EnumValueDef("5", "历史版本", "物料升级后被新版本取代的旧记录。"),
    ], BIZ + "; AddCodeApplyController#importExcel (applyStatus=0 草稿)"),
    EnumGroup("生命周期阶段属性", "生命周期阶段", [
        EnumValueDef("YF", "研发", "物料处于研发阶段。"),
        EnumValueDef("NA", "测试", "物料处于测试阶段。"),
        EnumValueDef("CA", "试产", "物料处于试产阶段。"),
        EnumValueDef("AP", "批量", "物料处于批量阶段。"),
        EnumValueDef("00", "EOL", "物料为EOL状态。"),
        EnumValueDef("02", "部分失效", "物料部分失效。"),
        EnumValueDef("03", "采购失效", "物料对采购失效。"),
        EnumValueDef("04", "完全失效", "物料完全失效。"),
        EnumValueDef("99", "完全停产", "物料完全停产。"),
    ]),
    EnumGroup("优选标识属性", "优选标识", [
        EnumValueDef("优选A", "优选A", "采购标记为优选A的物料，研发设计BOM时会优先考虑。", "海外家电BG"),
        EnumValueDef("优选B", "优选B", "采购标记为优选B的物料，研发设计BOM时会优先考虑。", "国内家电BG"),
        EnumValueDef("优选1(汽电)", "优选1(汽电)", "采购标记为优选1(汽电)的物料，研发设计BOM时会优先考虑。", "汽车电子BG"),
    ]),
    EnumGroup("制造商AVL等级属性", "制造商AVL等级", [
        EnumValueDef("主力", "主力", "研发设计BOM时优先考虑。"),
        EnumValueDef("合格", "合格", "研发设计BOM时优先考虑。"),
        EnumValueDef("试用", "试用", "研发设计BOM时优先考虑。"),
        EnumValueDef("考察", "考察", "物料对应的制造商不合格或未验证，研发设计BOM时不优先考虑。"),
        EnumValueDef("限制", "限制", "处理方式和考察一样：物料对应的制造商不合格或未验证，研发设计BOM时不优先考虑。"),
    ], BIZ + "; AddCodeApplyController#checkParam"),
]


# --------------------------------------------------------------------------- #
# 7. 应用场景及其支撑关系
# --------------------------------------------------------------------------- #

SCENARIOS: List[Tuple[str, str]] = [
    ("物料精确查找", "根据物料编码、描述关键字、分类或属性值，定位到具体的物料。"),
    ("物料相似查找", "在同分类下找出属性相近的物料。"),
    ("替代料推荐", "为某个物料推荐可以替换的其他物料。"),
]


@dataclass
class Support:
    subject: str  # 实体类名 | 字段中文名 | 常用属性规范名
    scenario: str
    basis: str  # confirmed | code | inferred
    reason: str  # 说明（不要出现触发词）
    source: str = ""


# 全部场景支撑关系均已由业务方确认（含原先按字段含义推断的 17 条）。
SUPPORTS: List[Support] = [
    # ---- 物料精确查找 ----
    Support("AddCodeApply", "物料精确查找", "code", "物料主数据一行对应一个物料，物料编码、分类、描述和状态都在这张表里。", "AddCodeApply.java"),
    Support("物料编码", "物料精确查找", "confirmed",
            "物料编码首位数字区分BG：汽车电子BG以2开头，其他BG以1开头；同一物料编码只有一条申请状态为2的有效记录。", BIZ),
    Support("旧物料编码", "物料精确查找", "code", "新物料可以沿用旧物料编码，可用来从老编码反查物料。", "CodeRangeServiceImpl#getCodeAndCommit"),
    Support("申请状态", "物料精确查找", "confirmed", "只有申请状态为2的记录才是有效物料，其他状态的记录不进入图谱。", BIZ),
    Support("L4分类", "物料精确查找", "code", "物料主数据按L4分类归类，可先按分类缩小范围。", "AddCodeApply.java @Dict"),
    Support("AcAddCodeApplyAttr", "物料精确查找", "code", "物料名称等基础属性通过加码id挂在物料主数据上。", "AcAddCodeApplyAttrMapper.xml#getMaterialNameByMaterialNo"),
    Support("物料名称属性", "物料精确查找", "code", "按物料编码可以查到物料名称。", "AcAddCodeApplyAttrMapper.xml#getMaterialNameByMaterialNo"),
    Support("物料短描述", "物料精确查找", "confirmed", "描述由属性值按固定顺序拼接而成，可以用关键字检索。", "AddCodeApplyServiceImpl#generateDescriptions"),
    Support("物料长描述", "物料精确查找", "confirmed", "长描述包含更完整的属性值，可以用关键字检索。", "AddCodeApplyServiceImpl#generateDescriptions"),
    Support("属性值", "物料精确查找", "confirmed", "属性代码加属性值的组合，可以按参数筛选物料。", "AcAddCodeApplyAttr.java"),
    Support("制造商名称属性", "物料精确查找", "confirmed", "可以按制造商名称限定物料范围。", "AcAddCodeApplyAttrServiceImpl#getByMainIdAndPurchase"),
    Support("生命周期阶段属性", "物料精确查找", "confirmed", "它是物料在业务上的状态，可以排除失效、停产的物料。", BIZ),
    Support("专用客户属性", "物料精确查找", "confirmed", "有值说明是客户专用料，研发查找物料时可以过滤掉这些专用料。", BIZ),
    Support("是否汽车电子", "物料精确查找", "confirmed", "可据此区分汽车电子BG的物料和其他BG的物料。", BIZ),
    # ---- 物料相似查找 ----
    Support("L4分类", "物料相似查找", "confirmed", "同一L4分类下的物料适用同一套属性模板，才有可比性。", "ClassificationAttributeRefServiceImpl#queryrangeCodeByfourCode"),
    Support("ClassificationAttributeRef", "物料相似查找", "confirmed", "模板规定了每类物料有哪些属性，是比较的依据。", "ClassificationAttributeRef.java"),
    Support("是否属于可比性属性", "物料相似查找", "confirmed", "该标识表明哪些属性可以用来比较，源码里没有直接使用。", "ClassificationAttributeRef.java"),
    Support("属性值", "物料相似查找", "confirmed", "属性值越接近，物料越相似。", "AcAddCodeApplyAttr.java"),
    Support("物料短描述", "物料相似查找", "confirmed", "描述的拼接顺序相同，描述文本可以用来比较相近程度。", "AddCodeApplyServiceImpl#generateDescriptions"),
    Support("AcAddCodeApplyAttrp", "物料相似查找", "confirmed", "私有属性是各分类特有的技术参数，决定物料是否相似。", "AcAddCodeApplyAttrp.java"),
    Support("细分类属性", "物料相似查找", "confirmed", "细分类相同说明物料更接近。", "AttributeValueServiceImpl#getSubdivisionDesc"),
    # ---- 替代料推荐 ----
    Support("AcAddCodeApplyAttrp", "替代料推荐", "confirmed", "技术参数一致是替代的前提。", "AcAddCodeApplyAttrp.java"),
    Support("是否属于可比性属性", "替代料推荐", "confirmed", "只比较可比性属性，才能判断能否替代。", "ClassificationAttributeRef.java"),
    Support("是否涉及优选", "替代料推荐", "confirmed", "替代时应优先推荐优选物料。", "AddCodeApplyServiceImpl#pushMainData"),
    Support("优选标识属性", "替代料推荐", "confirmed",
            "被标记为优选的物料研发设计BOM时优先考虑，推荐替代料时应优先给出，并注意优选所属的BG。", BIZ),
    Support("制造商AVL等级属性", "替代料推荐", "confirmed",
            "优先推荐主力、合格、试用的物料；考察、限制表示制造商不合格或未验证，不宜优先推荐。", BIZ),
    Support("标准件/非标准件", "替代料推荐", "confirmed", "标准件之间更容易互相替换。", "ClassificationManagement.java"),
    Support("制造商名称属性", "替代料推荐", "confirmed", "替代料常常是同规格、不同制造商的物料。", "AcAddCodeApplyAttrServiceImpl#getByMainIdAndPurchase"),
    Support("生命周期阶段属性", "替代料推荐", "confirmed", "物料进入EOL或失效、停产后，需要为它找替代；推荐的替代料自身也不应是失效或停产的。", BIZ),
    Support("专用客户属性", "替代料推荐", "confirmed", "推荐替代料时同样应该过滤掉客户专用料。", BIZ),
]


# --------------------------------------------------------------------------- #
# 8. 抽取规则（中文关系触发词）
# --------------------------------------------------------------------------- #

# (predicate, 触发词正则)
# 触发词按出现位置切分句子：主语 = 触发词左侧最近且类型兼容的实体，
# 宾语 = 触发词右侧、下一个触发词之前的所有类型兼容实体。
RELATION_CUES: List[Tuple[str, str]] = [
    ("mapsToTable", r"对应数据表"),
    ("hasKeyField", r"的关键字段(?:包括|有)"),
    ("hasValue", r"的枚举值(?:包括|有)"),
    ("includesAttribute", r"包含常用属性"),
    ("preferredFor", r"标识(?=[^。；]*?的优选物料)"),
    ("indicatesBG", r"标明"),
    ("partOf", r"属于"),
    ("refersTo", r"引用"),
    ("usesDictionary", r"使用"),
    ("derivesFrom", r"取自"),
    ("supports", r"支持"),
    ("governedBy", r"受(?=[^。；]*?约束)"),
]

# 句内“切断”词：对象列表遇到这些词就结束（如“…，关联字段为…”“…约束”）
OBJECT_STOP = r"约束|关联字段"
