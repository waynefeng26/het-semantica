# 语义分析结果

## 语义角色分布

| 角色 | 数量 |
|---|---|
| predicate | 105 |
| agent | 105 |
| attribute | 69 |
| purpose | 30 |
| value | 23 |
| constraint | 17 |
| key | 15 |
| theme | 11 |
| location | 8 |
| source | 6 |
| resource | 5 |
| beneficiary | 3 |
| indicator | 1 |

## 实体语义相似度（降序）

| 实体 A | 实体 B | 文本余弦 | 关键字段 Jaccard | 共享关键字段 |
|---|---|---|---|---|
| 物料分类 | 物料编码号段 | 0.4574 | 0.0667 | L4分类代码 |
| 物料分类属性模板 | 物料属性值库 | 0.3345 | 0.1333 | L4分类代码、属性代码 |
| 物料主数据 | 物料分类 | 0.272 | 0.0 |  |
| 物料属性定义 | 物料属性值库 | 0.263 | 0.1667 | 属性代码 |
| 物料属性定义 | 物料分类属性模板 | 0.2416 | 0.0769 | 属性代码 |
| 物料基础属性 | 物料分类 | 0.2144 | 0.0 |  |
| 物料基础属性 | 物料编码号段 | 0.2129 | 0.0 |  |
| 物料分类 | 物料分类属性模板 | 0.2061 | 0.0526 | L4分类代码 |
| 物料主数据 | 物料编码号段 | 0.2025 | 0.0 |  |
| 物料主数据 | 物料基础属性 | 0.1791 | 0.0 |  |
| 物料私有属性 | 物料分类属性模板 | 0.1374 | 0.1333 | 属性代码、属性类型 |
| 物料基础属性 | 物料分类属性模板 | 0.1351 | 0.1333 | 属性代码、属性类型 |
| 物料分类 | 物料属性值库 | 0.1229 | 0.0833 | L4分类代码 |
| 物料分类属性模板 | 物料编码号段 | 0.1204 | 0.0526 | L4分类代码 |
| 物料主数据 | 物料私有属性 | 0.1069 | 0.0 |  |
| 物料私有属性 | 物料属性定义 | 0.1039 | 0.1667 | 属性代码 |
| 物料属性值库 | 物料编码号段 | 0.0946 | 0.0833 | L4分类代码 |
| 物料主数据 | 物料分类属性模板 | 0.0926 | 0.0 |  |
| 物料基础属性 | 物料属性定义 | 0.0808 | 0.1667 | 属性代码 |
| 物料主数据 | 物料属性值库 | 0.0752 | 0.0 |  |
| 物料属性定义 | 物料编码号段 | 0.0736 | 0.0 |  |
| 物料私有属性 | 物料属性值库 | 0.0715 | 0.1111 | 属性代码 |
| 物料基础属性 | 物料属性值库 | 0.0712 | 0.1111 | 属性代码 |
| 物料分类 | 物料属性定义 | 0.0675 | 0.0 |  |
| 物料基础属性 | 物料私有属性 | 0.0645 | 1.0 | 加码id、属性代码、属性值、属性描述、属性类型 |
| 物料私有属性 | 物料分类 | 0.0457 | 0.0 |  |
| 物料私有属性 | 物料编码号段 | 0.0432 | 0.0 |  |
| 物料主数据 | 物料属性定义 | 0.0429 | 0.0 |  |

## 实体聚类（阈值 0.35）

- 簇 0：物料主数据（平均相似度 1.0）
- 簇 1：物料基础属性（平均相似度 1.0）
- 簇 2：物料私有属性（平均相似度 1.0）
- 簇 3：物料分类、物料编码号段（平均相似度 0.4574）
- 簇 4：物料属性定义（平均相似度 1.0）
- 簇 5：物料分类属性模板（平均相似度 1.0）
- 簇 6：物料属性值库（平均相似度 1.0）

## 文档级语义特征

| 文档 | 类型 | 提及数 | 唯一实体 | 角色标注数 |
|---|---|---|---|---|
| entity:AddCodeApply | entity | 29 | 15 | 23 |
| entity:AcAddCodeApplyAttr | entity | 14 | 7 | 10 |
| entity:AcAddCodeApplyAttrp | entity | 14 | 7 | 10 |
| entity:ClassificationManagement | entity | 16 | 10 | 13 |
| entity:AttributeManagement | entity | 11 | 4 | 7 |
| entity:ClassificationAttributeRef | entity | 29 | 18 | 26 |
| entity:AttributeValue | entity | 13 | 7 | 10 |
| entity:CodeRange | entity | 19 | 12 | 13 |
| relation:AcAddCodeApplyAttr-partOf-AddCodeApply | relation | 3 | 3 | 4 |
| relation:AcAddCodeApplyAttrp-partOf-AddCodeApply | relation | 3 | 3 | 4 |
| relation:AddCodeApply-refersTo-ClassificationManagement | relation | 6 | 6 | 7 |
| relation:AddCodeApply-refersTo-CodeRange | relation | 3 | 3 | 4 |
| relation:ClassificationAttributeRef-refersTo-ClassificationManagement | relation | 3 | 3 | 4 |
| relation:ClassificationAttributeRef-refersTo-AttributeManagement | relation | 3 | 3 | 4 |
| relation:AttributeValue-refersTo-ClassificationAttributeRef | relation | 4 | 4 | 5 |
| relation:AttributeValue-refersTo-AttributeManagement | relation | 3 | 3 | 4 |
| relation:CodeRange-refersTo-ClassificationManagement | relation | 3 | 3 | 4 |
| relation:AcAddCodeApplyAttr-refersTo-ClassificationAttributeRef | relation | 3 | 3 | 4 |
| relation:AcAddCodeApplyAttrp-refersTo-ClassificationAttributeRef | relation | 3 | 3 | 4 |
| attr:materialName | attribute | 7 | 3 | 6 |
| attr:materialAbbreviation | attribute | 7 | 3 | 6 |
| attr:materialType | attribute | 8 | 3 | 6 |
| attr:lifeCyclePhase | attribute | 4 | 2 | 3 |
| attr:preferredIdentification | attribute | 4 | 2 | 3 |
| attr:manufacturerAvlRating | attribute | 4 | 2 | 3 |
| attr:notes | attribute | 6 | 3 | 3 |
| attr:manufacturersName | attribute | 4 | 2 | 3 |
| attr:projectType | attribute | 4 | 2 | 3 |
| attr:brandExceptionType | attribute | 4 | 2 | 3 |
| attr:subdivision | attribute | 5 | 3 | 3 |
| attr:documentNumber | attribute | 4 | 2 | 3 |
| enum:申请状态 | enum | 7 | 7 | 8 |
| enumval:申请状态-草稿 | enum | 1 | 1 | 0 |
| enumval:申请状态-标准化审批中 | enum | 1 | 1 | 0 |
| enumval:申请状态-审批完成 | enum | 2 | 2 | 0 |
| enumval:申请状态-SCM采购审批中 | enum | 1 | 1 | 0 |
| enumval:申请状态-退回 | enum | 1 | 1 | 0 |
| enumval:申请状态-历史版本 | enum | 1 | 1 | 0 |
| enum:生命周期阶段 | enum | 10 | 10 | 11 |
| enumval:生命周期阶段-研发 | enum | 1 | 1 | 0 |
| enumval:生命周期阶段-测试 | enum | 1 | 1 | 0 |
| enumval:生命周期阶段-试产 | enum | 1 | 1 | 0 |
| enumval:生命周期阶段-批量 | enum | 1 | 1 | 0 |
| enumval:生命周期阶段-EOL | enum | 1 | 1 | 0 |
| enumval:生命周期阶段-部分失效 | enum | 1 | 1 | 0 |
| enumval:生命周期阶段-采购失效 | enum | 1 | 1 | 0 |
| enumval:生命周期阶段-完全失效 | enum | 1 | 1 | 0 |
| enumval:生命周期阶段-完全停产 | enum | 1 | 1 | 0 |
| enum:优选标识 | enum | 4 | 4 | 5 |
| enumval:优选标识-优选A | enum | 3 | 2 | 3 |
| enumval:优选标识-优选B | enum | 3 | 2 | 3 |
| enumval:优选标识-优选1(汽电) | enum | 3 | 2 | 3 |
| enum:制造商AVL等级 | enum | 6 | 6 | 7 |
| enumval:制造商AVL等级-主力 | enum | 1 | 1 | 0 |
| enumval:制造商AVL等级-合格 | enum | 1 | 1 | 0 |
| enumval:制造商AVL等级-试用 | enum | 1 | 1 | 0 |
| enumval:制造商AVL等级-考察 | enum | 1 | 1 | 0 |
| enumval:制造商AVL等级-限制 | enum | 1 | 1 | 0 |
| bg:是否汽车电子:汽车电子BG | enum | 2 | 2 | 3 |
| rule:有效物料判定规则 | rule | 8 | 4 | 0 |
| rule:物料升级规则 | rule | 6 | 4 | 0 |
| rule:物料状态口径规则 | rule | 2 | 2 | 0 |
| rule:物料编码BG前缀规则 | rule | 6 | 4 | 0 |
| rule:客户专用料规则 | rule | 3 | 3 | 0 |
| rule:分类代码层级规则 | rule | 13 | 11 | 0 |
| rule:分类属性范围匹配规则 | rule | 9 | 7 | 0 |
| rule:属性值解析规则 | rule | 3 | 3 | 0 |
| rule:物料描述拼接规则 | rule | 9 | 9 | 0 |
| rule:物料基础属性取值规则 | rule | 11 | 10 | 9 |
| rule:编码号段选取规则 | rule | 5 | 3 | 0 |
| rule:汽车电子号段规则 | rule | 8 | 8 | 0 |
| rule:旧物料编码校验规则 | rule | 4 | 3 | 0 |
| governed:AddCodeApply:有效物料判定规则 | rule | 2 | 2 | 3 |
| governed:AddCodeApply:物料升级规则 | rule | 2 | 2 | 3 |
| governed:AddCodeApply:物料状态口径规则 | rule | 2 | 2 | 3 |
| governed:AddCodeApply:物料编码BG前缀规则 | rule | 2 | 2 | 3 |
| governed:AddCodeApply:物料描述拼接规则 | rule | 2 | 2 | 3 |
| governed:AddCodeApply:旧物料编码校验规则 | rule | 2 | 2 | 3 |
| governed:AddCodeApply:分类代码层级规则 | rule | 2 | 2 | 3 |
| governed:AcAddCodeApplyAttr:物料基础属性取值规则 | rule | 2 | 2 | 3 |
| governed:AcAddCodeApplyAttr:客户专用料规则 | rule | 2 | 2 | 3 |
| governed:ClassificationManagement:分类代码层级规则 | rule | 2 | 2 | 3 |
| governed:ClassificationAttributeRef:分类属性范围匹配规则 | rule | 2 | 2 | 3 |
| governed:ClassificationAttributeRef:属性值解析规则 | rule | 2 | 2 | 3 |
| governed:ClassificationAttributeRef:物料描述拼接规则 | rule | 2 | 2 | 3 |
| governed:AttributeValue:分类属性范围匹配规则 | rule | 2 | 2 | 3 |
| governed:AttributeValue:属性值解析规则 | rule | 2 | 2 | 3 |
| governed:CodeRange:编码号段选取规则 | rule | 2 | 2 | 3 |
| governed:CodeRange:汽车电子号段规则 | rule | 2 | 2 | 3 |
| scenario:物料精确查找 | scenario | 3 | 3 | 0 |
| scenario:物料相似查找 | scenario | 1 | 1 | 0 |
| scenario:替代料推荐 | scenario | 1 | 1 | 0 |
| support:AddCodeApply:物料精确查找 | support | 4 | 3 | 3 |
| support:物料编码:物料精确查找 | support | 6 | 4 | 3 |
| support:旧物料编码:物料精确查找 | support | 3 | 2 | 3 |
| support:申请状态:物料精确查找 | support | 3 | 2 | 3 |
| support:L4分类:物料精确查找 | support | 4 | 3 | 3 |
| support:AcAddCodeApplyAttr:物料精确查找 | support | 5 | 4 | 3 |
| support:物料名称属性:物料精确查找 | support | 3 | 3 | 3 |
| support:物料短描述:物料精确查找 | support | 3 | 3 | 3 |
| support:物料长描述:物料精确查找 | support | 3 | 3 | 3 |
| support:属性值:物料精确查找 | support | 4 | 3 | 3 |
| support:制造商名称属性:物料精确查找 | support | 2 | 2 | 3 |
| support:生命周期阶段属性:物料精确查找 | support | 2 | 2 | 3 |
| support:专用客户属性:物料精确查找 | support | 2 | 2 | 3 |
| support:是否汽车电子:物料精确查找 | support | 3 | 3 | 3 |
| support:L4分类:物料相似查找 | support | 4 | 3 | 3 |
| support:ClassificationAttributeRef:物料相似查找 | support | 2 | 2 | 3 |
| support:是否属于可比性属性:物料相似查找 | support | 2 | 2 | 3 |
| support:属性值:物料相似查找 | support | 3 | 2 | 3 |
| support:物料短描述:物料相似查找 | support | 2 | 2 | 3 |
| support:AcAddCodeApplyAttrp:物料相似查找 | support | 3 | 2 | 3 |
| support:细分类属性:物料相似查找 | support | 2 | 2 | 3 |
| support:AcAddCodeApplyAttrp:替代料推荐 | support | 2 | 2 | 3 |
| support:是否属于可比性属性:替代料推荐 | support | 2 | 2 | 3 |
| support:是否涉及优选:替代料推荐 | support | 2 | 2 | 3 |
| support:优选标识属性:替代料推荐 | support | 2 | 2 | 3 |
| support:制造商AVL等级属性:替代料推荐 | support | 2 | 2 | 3 |
| support:标准件/非标准件:替代料推荐 | support | 2 | 2 | 3 |
| support:制造商名称属性:替代料推荐 | support | 2 | 2 | 3 |
| support:生命周期阶段属性:替代料推荐 | support | 2 | 2 | 3 |
| support:专用客户属性:替代料推荐 | support | 2 | 2 | 3 |
