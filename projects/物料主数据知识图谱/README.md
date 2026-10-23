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
- 业务上的物料状态 = 基础属性 `lifeCyclePhase`（生命周期阶段）：研发、测试、试产、批量、EOL、部分失效、采购失效、完全失效、完全停产。
- 优选标识 `preferredIdentification`（采购维护）：优选A = 海外家电BG，优选B = 国内家电BG，优选1(汽电) = 汽车电子BG；研发设计 BOM 时优先考虑。
- 制造商AVL等级 `manufacturerAvlRating`（每晚按采购维护的制造商等级更新）：主力、合格、试用、考察；考察表示制造商不合格或未验证。
- 制造商AVL等级里的“限制”与“考察”处理方式一样（制造商不合格或未验证，不优先考虑）。
- 专用客户 `notes`：有值表示该物料是某客户的专用料；值与客户名称 / 客户编码不相等，但字面上能看出是同一客户，目前只有两个客户可选。研发找物料时可以过滤掉客户专用料。
- 物料编码：汽车电子BG以 2 开头，其他BG以 1 开头；是否汽车电子 = 汽车电子BG。
- 物料主数据的 `materialStatus`（物料状态）字段目前未使用，已从关键字段中去掉。

## 待确认

目前没有待确认项（`output/to_confirm.md` 会列出所有仍为“推断”的内容）。

已移除：Service / Operation 概念，以及 `manages`、`dependsOn`、`providesOperation`、`reads`、`writes`、`matchesBy`、`generates`。

当前已完成：**三元组抽取 → 语义分析 → 语义网络抽取**。本体导出（`matkg/export_ontology.py`）已完成；LLM 增强、入图校验的接入：待确认后再做。

## 运行

```bash
python run_pipeline.py            # 结果写入 output/
python -m pytest tests -q
```

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
