# Neo4j 入库报告

- 开始：2026-10-23T16:06:05　结束：2026-10-23T16:39:53

## 入图前校验

- 检查物料主数据 391,986 条（申请状态 = 2 且 del_flag = 0）
- 违规统计：{'ecar_mismatch': 72}
- 因逻辑删除（del_flag=1）而排除的状态 2 记录：105 条
  - ecar_mismatch 示例：物料 10935002697 的是否汽车电子为 1，与编码首位 1 不一致；物料 10935002439 的是否汽车电子为 1，与编码首位 1 不一致；物料 10935003169 的是否汽车电子为 1，与编码首位 1 不一致

## 写入结果

| 标签 | 节点数 |
|---|---|
| MaterialMaster | 391,990 |
| MaterialBasicAttribute | 6,916,312 |
| MaterialPrivateAttribute | 2,135,558 |
| MaterialClassification | 835 |
| MaterialAttributeDef | 782 |
| MaterialClassAttrTemplate | 5,330 |
| MaterialAttributeValue | 10,450 |
| MaterialCodeRange | 848 |

| 关系 | 数量 |
|---|---|
| partOf | 9,051,872 |
| refersTo | 9,848,383 |
| hasValue | 576,239 |

## 统计

- resumed_from_materials：0
- basic_template_resolved：6,884,699
- enum_matched：576,208
- enum_ignored：10,883
- private_template_resolved：2,121,888
- materials：391,990
- basic_rows：6,916,312
- private_rows：2,135,558
- private_template_missing：13,670
- basic_template_missing：31,613
- quality::ecar_mismatch：72
- seconds：1585.8
