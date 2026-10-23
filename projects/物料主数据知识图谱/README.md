# 物料主数据知识图谱

基于 [Semantica](../../../semantica) 对 `het-main/.../modules/addcode` 中 8 个核心实体做语义抽取。

**目的**：让 agent 理解公司物料主数据的结构，从而更准确地 **查找物料、推荐替代料、查找相似物料**。
因此图谱只保留数据结构和数据语义；service 层的调用 / 读写关系不入图，只作为整理规则时的参考（出处写在 `source` 里）。

## 范围（业务口径 = 节点名）

| 节点名 | Java 类 | 表 | 来源 |
|---|---|---|---|
| 物料主数据 | `AddCodeApply`（加码申请表） | `ac_add_code_apply` | 业务方确认 |
| 物料基础属性 | `AcAddCodeApplyAttr` | `ac_add_code_apply_attr` | 业务方确认 |
| 物料私有属性（物料技术属性） | `AcAddCodeApplyAttrp` | `ac_add_code_apply_attrp` | 业务方确认 |
| 物料分类 | `ClassificationManagement` | `ac_classification_management` | 业务方确认 |
| 物料属性定义 | `AttributeManagement` | `ac_attribute_management` | 业务方确认 |
| 物料分类属性模板 | `ClassificationAttributeRef` | `ac_classification_attribute_ref` | 业务方确认 |
| 物料属性值库 | `AttributeValue` | `ac_attribute_value` | 业务方确认 |
| 物料编码号段 | `CodeRange` | `ac_code_range` | 业务方确认 |

## 本体

- 概念：Entity、DataTable、Field、Dictionary、CommonAttribute（常用属性）、BusinessRule、Scenario（应用场景）
- 结构关系：`mapsToTable`、`hasKeyField`、`refersTo`、`partOf`（带关联字段）、`usesDictionary`
- 语义关系：`includesAttribute`（物料基础属性→常用属性）、`derivesFrom`（常用属性→取值来源字段）、
  `governedBy`（实体→业务规则）、`supports`（实体/字段/常用属性→应用场景）、`similarTo`（仅由语义分析推断）
- 枚举值：`hasValue`（字段 / 常用属性 → 枚举值，节点名形如“申请状态-审批完成”“生命周期阶段-批量”），
  `preferredFor`（优选标识的枚举值 → 优选所属的 BG）
- 应用场景：物料精确查找、物料相似查找、替代料推荐
- 每条三元组带依据：`confirmed`（业务方说明）、`code`（源码有直接证据）、`inferred`（按字段含义推断，**待业务方确认**）

## 关键业务口径（业务方说明）

- 申请状态：0草稿、1标准化审批中、2审批完成、3SCM采购审批中、4退回、5历史版本。
  物料升级会新建一条记录（物料编码不变），审批通过后新记录为 2、原来为 2 的改为 5，
  所以同一物料编码状态为 2 的记录只有一条。**入图数据必须始终是状态为 2 的记录**，
  校验函数见 `matkg/ingest_rules.py`（`validate_material_rows` / `ensure_ingestable`，校验阶段调用）。
- 业务上的物料状态 = 基础属性 `lifeCyclePhase`（生命周期阶段）：研发、测试、试产、批量、EOL、部分失效、采购失效、完全失效、完全停产；
  数据里还出现 TA、GA、NG、05、YJ、Preliminary，已补进枚举，名称暂用代码，业务含义待业务方说明。
- 优选标识 `preferredIdentification`（采购维护）：优选A = 海外家电BG，优选B = 国内家电BG，优选1(汽电) = 汽车电子BG；研发设计 BOM 时优先考虑。
- 制造商AVL等级 `manufacturerAvlRating`（每晚按采购维护的制造商等级更新）：主力、合格、试用、考察；考察表示制造商不合格或未验证。
  使用时只筛选主力 / 合格 / 试用，其他取值一律认为不及格；数据里不规范的取值（如“考察(暂定)”“AVL-C”）暂时忽略（`制造商AVL等级筛选规则`），不建枚举值。
- 制造商AVL等级里的“限制”与“考察”处理方式一样（制造商不合格或未验证，不优先考虑）。
- 专用客户 `notes`：有值表示该物料是某客户的专用料，属性值保存客户编码：A001 = 兰吉尔，A002 = 京瓷（目前只有这两个客户）。研发找物料时可以过滤掉客户专用料。
- 基础属性里最重要的三个“核心属性”（`hasCoreAttribute`）：物料名称 `materialName`、制造商零件编号（MPN）`manufacturerPartNumber`、制造商名称 `manufacturersName`。
  MPN 对物料精确查找、物料相似查找、替代料推荐都有作用；MPN 相同、制造商不同**不再**单独算替代料（已去掉“同MPN替代规则”）；MPN 前缀或系列号相同不能单独判断，要结合 L4 分类和物料私有属性（`MPN相近替代判断规则`）。
  源码里：通用件按“MPN + 制造商”查重、定制件按“图号 `mapNumber` + 制造商”查重；物料列表可按 MPN、制造商名称、图号、文档编号过滤。
- 物料编码：以 2 开头的是汽车电子物料（汽车电子BG），其他开头一律是非汽车电子物料；是否汽车电子 = 汽车电子BG。
- 物料主数据的 `materialStatus`（物料状态）字段目前未使用，已从关键字段中去掉。

## 替代料推荐的判断路径

MPN 与 L4 分类之间没有直接连线，而是沿图谱走：
制造商零件编号属性 ← 物料基础属性 → 物料主数据 → 物料分类（L4）← 物料分类属性模板 ← 物料私有属性（技术属性），
再比较两个物料的核心技术属性是否相近，相近则互为替代（`lexicon.SCENARIO_PATHS`，导出到 `ontology.json` 的 `reasoning_paths`）。
MPN 只是找到物料的入口，前缀或系列号相同不能单独判断是否替代，以核心技术属性是否相近为准。
核心技术属性 = 私有属性中、物料分类属性模板里“是否必填”为 X 的属性（公有属性不算）；“是否属于可比性属性”字段忽略。
“相近”没有统一标准，各分类不同、按绝对差比较、单位一般统一；目前只有 L1 分类 = 28（包材）：核心技术属性里长、宽、高这类尺寸数值属性，分类有哪些就比哪些（不是每个包材分类都有），取值之差都在 ±5 以内表示相近，可以互为替代料或相似料；规则按“分类范围 + 属性类别”配置，不逐个属性写死；哪些属性算尺寸类，目前先按属性名称判断（参考词见 `name_hints`，可增补）
（`lexicon.SIMILARITY_CRITERIA`，导出到 `ontology.json` 的 `similarity_criteria`）。其他分类暂无标准。

## 待确认

目前没有待确认项（`output/to_confirm.md` 会列出所有仍为“推断”的内容）。

已移除：Service / Operation 概念，以及 `manages`、`dependsOn`、`providesOperation`、`reads`、`writes`、`matchesBy`、`generates`。

当前已完成：**三元组抽取 → 语义分析 → 语义网络抽取**。本体导出（`matkg/export_ontology.py`）已完成；LLM 增强、入图校验的接入：待确认后再做。

## 运行

```bash
python run_pipeline.py            # 结果写入 output/
python -m pytest tests -q
```

## 写入 Neo4j

`load_neo4j.py` 把 MySQL 数据按本体写入 Neo4j（`matkg/neo4j_loader.py`）。连接信息只通过环境变量传入（`MATKG_MYSQL_URL/USER/PASSWORD`、`MATKG_NEO4J_URI/USER/PASSWORD`），不进仓库。

```bash
python load_neo4j.py --dry-run            # 只做入图前校验
python load_neo4j.py --reset --limit 20000  # 抽样压测
python load_neo4j.py --reset              # 全量；中断后直接再跑会从检查点续上（MERGE 幂等）
python load_neo4j.py --reset --no-basic-template-rel   # 基础属性不建到分类属性模板的关系（更小更快）
```

- **本体层**：标签 `Ont` + 类名（`Entity`、`BusinessRule`、`EnumValue`、`Scenario` …），关系类型即本体谓词；`OntClass` / `OntProperty` 记录类与属性的 domain / range；`Scenario` 节点上有 `reasoningPaths`、`similarityCriteria`（JSON 字符串）。
- **数据层**：标签用英文驼峰命名，属性名沿用 Java 字段名。本体 `Entity` 节点的 `nodeLabel` 属性记录对应的标签：

  | 业务口径 | 标签 |
  |---|---|
  | 物料主数据 | `MaterialMaster` |
  | 物料基础属性 | `MaterialBasicAttribute` |
  | 物料私有属性 | `MaterialPrivateAttribute` |
  | 物料分类 | `MaterialClassification` |
  | 物料属性定义 | `MaterialAttributeDef` |
  | 物料分类属性模板 | `MaterialClassAttrTemplate` |
  | 物料属性值库 | `MaterialAttributeValue` |
  | 物料编码号段 | `MaterialCodeRange` |

  - `(属性行)-[:partOf {via:'addCodeId'}]->(MaterialMaster)`、`(属性行)-[:refersTo {via:'attrCode'}]->(MaterialClassAttrTemplate)`、`(MaterialMaster)-[:refersTo]->(MaterialClassification / MaterialCodeRange)`、`(模板)-[:refersTo]->(MaterialClassification / MaterialAttributeDef)`；`via` 记录用哪个字段关联；
  - 基础属性取值命中枚举值时 `(MaterialBasicAttribute)-[:hasValue]->(:Ont:EnumValue)`；制造商AVL等级只认主力 / 合格 / 试用等已定义的值，其余不报告；
  - 物料主数据上冗余了 `materialName`、`manufacturerPartNumber`、`manufacturersName`、`lifeCyclePhase`、`preferredIdentification`、`manufacturerAvlRating`、`customerCode`（来自 `notes`）；
  - 私有属性行带 `isCoreTechnical`（模板“是否必填”= X）和纯数字时的 `attrValueNum`，便于按绝对差比较；
  - `isAutomotive`：物料编码以 2 开头为 true，其余 false；
  - 是否汽车电子与编码首位不一致的物料带 `qualityFlags = ['ecar_mismatch']`，不阻止入图，只标记。
- **入图规则**：只读 `apply_status = 2 AND del_flag = 0`；入图前先校验同一物料编码只有一条状态 2，否则中止。
- **大表策略**：按主键 keyset 分页，每批 2000 个物料，只写非空属性值；MySQL 预取与 Neo4j 写入并行，事务 4000 行以内（Neo4j 堆只有 2G）；全新库 `CREATE`，有数据或有检查点时自动改 `MERGE`。
- 结果与统计见 `output/neo4j_load_report.{json,md}`。

## 目录

- `matkg/java_scanner.py`  解析 Java 实体 / 控制器 / 服务 / Mapper XML
- `matkg/lexicon.py`       本体 + 人工整理的实体关系、规则、常用属性、应用场景（均带源码出处）
- `matkg/domain_model.py`  领域词表（gazetteer）
- `matkg/corpus.py`        把源码事实写成中文叙述语料
- `matkg/zh_extract.py`    Semantica 中文适配（实体 / 关系 / 三元组方法注册，角色、相似度、聚类）
- `matkg/pipeline.py`      三个阶段与结果输出
- `output/`                `glossary.{json,md}`、`corpus.{json,md}`、`triplets.{json,md}`、`semantic_analysis.{json,md}`、`semantic_network.{json,md}`、`ontology.{ttl,json}`（本体导出）

## 说明

- Semantica 默认实现面向英文（`\b`、空格分词），所以通过 `method_registry` 注册中文方法，并子类化 `SemanticAnalyzer`，未修改 semantica 源码。
- 抽取语料由 Java 源码整理而来：实体结构来自扫描器，关联 / 规则 / 常用属性来自 service 层与 Mapper XML 的阅读结果，每条都记录了出处。
- 因此三元组与语料中的事实同源，抽取结果的“正确率”不能当作泛化能力指标；校验阶段会改用独立的源码事实做对照。
