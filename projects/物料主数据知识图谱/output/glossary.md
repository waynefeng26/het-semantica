# 业务口径对照表

## 实体

| 规范名（节点名） | 源码叫法 | Java 类 | 表 | 别名 | 业务口径 | 来源 |
|---|---|---|---|---|---|---|
| 物料主数据 | 加码申请 | AddCodeApply | ac_add_code_apply | 加码申请、AddCodeApply、加码申请表、物料主数据表 | 即加码申请表，业务上是物料主数据表，一行对应一个物料，记录物料编码、L1至L4分类、物料描述和申请状态。 | 业务方确认 |
| 物料基础属性 | 加码申请基础属性 | AcAddCodeApplyAttr | ac_add_code_apply_attr | 加码申请基础属性、AcAddCodeApplyAttr、基础属性、公有属性、物料公有属性 | 即加码申请基础属性，业务上是物料基础属性，也叫公有属性，是同一分类下物料共有的属性取值。 | 业务方确认 |
| 物料私有属性 | 加码申请私有属性 | AcAddCodeApplyAttrp | ac_add_code_apply_attrp | 加码申请私有属性、AcAddCodeApplyAttrp、私有属性、物料技术属性、技术属性 | 即加码申请私有属性，业务上是物料私有属性，也叫物料技术属性，是各分类自己特有的技术参数取值。 | 业务方确认 |
| 物料分类 | 分类维护 | ClassificationManagement | ac_classification_management | 分类维护、ClassificationManagement、物料分类维护 | 即分类维护，业务上是物料分类体系，分为L1至L4四级，L4是最末级分类。 | 按“同理”推出，待确认 |
| 物料属性定义 | 属性维护 | AttributeManagement | ac_attribute_management | 属性维护、AttributeManagement | 即属性维护，业务上是物料属性的定义清单，每个属性有属性代码和属性名称。 | 按“同理”推出，待确认 |
| 物料分类属性模板 | 分类属性维护 | ClassificationAttributeRef | ac_classification_attribute_ref | 分类属性维护、ClassificationAttributeRef、分类属性模板、属性模板 | 即分类属性维护，业务上是物料分类属性模板，规定某个分类下有哪些属性、公有还是私有、必填与否、描述拼接顺序。 | 按“同理”推出，待确认 |
| 物料属性值库 | 属性值库维护 | AttributeValue | ac_attribute_value | 属性值库维护、AttributeValue | 即属性值库维护，业务上是物料属性值库，保存单选、多选类属性的可选值及其描述。 | 按“同理”推出，待确认 |
| 物料编码号段 | 编码范围 | CodeRange | ac_code_range | 编码范围、CodeRange、编码号段 | 即编码范围，业务上是物料编码号段，按L4分类划分起止号段并记录当前最大编码，用于顺序分配物料编码。 | 按“同理”推出，待确认 |

## 物料基础属性里的常用属性

| 规范名 | attr_code | 说明 | 取自 | 出处 |
|---|---|---|---|---|
| 物料名称属性 | materialName | 物料的名称，创建时默认就是物料子类L4的名称。 | 物料子类L4 | AcAddCodeApplyAttrMapper.xml#getMaterialNameByMaterialNo; AddCodeApplyServiceImpl#createPublicAttributes |
| 物料简称属性 | materialAbbreviation | 物料的简称，创建时默认来自分类上的元器件物料简称。 | 元器件物料简称 | AddCodeApplyServiceImpl#createPublicAttributes |
| 物料类型属性 | materialType | 物料类型，创建时默认来自所在号段的物料类型。 | 物料类型 | AddCodeApplyServiceImpl#createPublicAttributes |
| 生命周期阶段属性 | lifeCyclePhase | 物料在业务上的物料状态，分为研发、测试、试产、批量、EOL、部分失效、采购失效、完全失效、完全停产。 |  | 业务方说明; AddCodeApplyController#checkLifeCyclePhase |
| 优选标识属性 | preferredIdentification | 由采购维护，标记物料是否为某个BG的优选物料；被标记为优选的物料，研发设计BOM时会优先考虑。 |  | 业务方说明; AcAddCodeApplyAttrServiceImpl#batchUpdateMaterialAttributes |
| 制造商AVL等级属性 | manufacturerAvlRating | 物料对应制造商的AVL等级，每天晚上定时根据采购维护的制造商等级更新；研发设计BOM时优先考虑主力、合格、试用的物料。 |  | 业务方说明; AddCodeApplyController#checkParam |
| 专用客户属性 | notes | 该属性有值表示物料是某个客户的专用料，属性值就是指定的专用客户；属性值与客户名称、客户编码并不相等，但从字面上能看出是同一个客户。 |  | 业务方说明 |
| 制造商名称属性 | manufacturersName | 物料对应的制造商名称。 |  | AcAddCodeApplyAttrServiceImpl#getByMainIdAndPurchase |
| 项目类型属性 | projectType | 物料所属项目的类型。 |  | AcAddCodeApplyAttrServiceImpl#getByMainIdAndPurchase |
| 品牌异常类型属性 | brandExceptionType | 品牌异常的类型；制造商AVL等级为考察、限制时必填，为主力、合格、试用时不能填写。 |  | AddCodeApplyController#checkParam |
| 细分类属性 | subdivision | 物料的细分类，取值的描述存放在物料属性值库里。 |  | AttributeValueServiceImpl#getSubdivisionDesc |
| 文档编号属性 | documentNumber | 物料关联的文档编号。 |  | AddCodeApplyServiceImpl#handleNeed |

## 枚举值

| 所属 | 节点名 | 编码 | 说明 | 优选所属BG |
|---|---|---|---|---|
| 申请状态 | 申请状态-草稿 | 0 | 申请还没有提交。 |  |
| 申请状态 | 申请状态-标准化审批中 | 1 | 申请已提交，正在标准化审批。 |  |
| 申请状态 | 申请状态-审批完成 | 2 | 审批通过的有效数据，同一物料编码只有一条。 |  |
| 申请状态 | 申请状态-SCM采购审批中 | 3 | 申请正在SCM采购审批。 |  |
| 申请状态 | 申请状态-退回 | 4 | 申请被退回。 |  |
| 申请状态 | 申请状态-历史版本 | 5 | 物料升级后被新版本取代的旧记录。 |  |
| 生命周期阶段属性 | 生命周期阶段-研发 | YF | 物料处于研发阶段。 |  |
| 生命周期阶段属性 | 生命周期阶段-测试 | NA | 物料处于测试阶段。 |  |
| 生命周期阶段属性 | 生命周期阶段-试产 | CA | 物料处于试产阶段。 |  |
| 生命周期阶段属性 | 生命周期阶段-批量 | AP | 物料处于批量阶段。 |  |
| 生命周期阶段属性 | 生命周期阶段-EOL | 00 | 物料为EOL状态。 |  |
| 生命周期阶段属性 | 生命周期阶段-部分失效 | 02 | 物料部分失效。 |  |
| 生命周期阶段属性 | 生命周期阶段-采购失效 | 03 | 物料对采购失效。 |  |
| 生命周期阶段属性 | 生命周期阶段-完全失效 | 04 | 物料完全失效。 |  |
| 生命周期阶段属性 | 生命周期阶段-完全停产 | 99 | 物料完全停产。 |  |
| 优选标识属性 | 优选标识-优选A | 优选A | 采购标记为优选A的物料，研发设计BOM时会优先考虑。 | 海外家电BG |
| 优选标识属性 | 优选标识-优选B | 优选B | 采购标记为优选B的物料，研发设计BOM时会优先考虑。 | 国内家电BG |
| 优选标识属性 | 优选标识-优选1(汽电) | 优选1(汽电) | 采购标记为优选1(汽电)的物料，研发设计BOM时会优先考虑。 | 汽车电子BG |
| 制造商AVL等级属性 | 制造商AVL等级-主力 | 主力 | 研发设计BOM时优先考虑。 |  |
| 制造商AVL等级属性 | 制造商AVL等级-合格 | 合格 | 研发设计BOM时优先考虑。 |  |
| 制造商AVL等级属性 | 制造商AVL等级-试用 | 试用 | 研发设计BOM时优先考虑。 |  |
| 制造商AVL等级属性 | 制造商AVL等级-考察 | 考察 | 物料对应的制造商不合格或未验证，研发设计BOM时不优先考虑。 |  |
| 制造商AVL等级属性 | 制造商AVL等级-限制 | 限制 | 处理方式和考察一样：物料对应的制造商不合格或未验证，研发设计BOM时不优先考虑。 |  |

## 业务规则

| 规则 | 内容 | 依据 | 出处 |
|---|---|---|---|
| 有效物料判定规则 | 物料主数据的申请状态表示申请审批状态，申请状态为2即审批完成的记录才是有效物料。同一个物料编码，申请状态为2的记录只有一条，进入图数据库的物料主数据只取申请状态为2的记录。 | 业务方确认 | 业务方说明 |
| 物料升级规则 | 物料升级时会新建一条物料主数据，物料编码保持不变；新建的升级记录审批通过后，申请状态改为2，原来申请状态为2的记录改为5即历史版本，因此同一物料编码始终只有一条有效记录。 | 业务方确认 | 业务方说明 |
| 物料状态口径规则 | 物料在业务上的物料状态以生命周期阶段属性为准。 | 业务方确认 | 业务方说明 |
| 物料编码BG前缀规则 | 汽车电子BG的物料编码以2开头，其他BG的物料编码以1开头；汽车电子BG的物料，其是否汽车电子为是。 | 业务方确认 | 业务方说明 |
| 客户专用料规则 | 专用客户属性有值的物料是客户专用料。属性值与客户名称、客户编码并不相等，但从字面上能看出是哪个客户，目前可选的客户只有两个。研发查找物料时可以过滤掉客户专用料。 | 业务方确认 | 业务方说明 |
| 分类代码层级规则 | L4分类代码的前两位就是L1分类代码；物料主数据的L1分类、L2分类、L3分类、L4分类，分别对应物料分类里的L1分类代码、L2分类代码、L3分类代码、L4分类代码。 | 源码 | ClassificationAttributeRefServiceImpl#queryrangeCodeByfourCode (fourCode.substring(0, 2)); AddCodeApply.java @Dict |
| 分类属性范围匹配规则 | 物料分类属性模板与物料属性值库的L4分类代码有三种写法：具体的L4分类代码、L1分类代码，以及形如起始-终止的L1分类范围。按L4分类代码查询时，命中任意一种写法的记录都会返回，并按排序和物料短描述顺序排列。 | 源码 | ClassificationAttributeRefMapper.xml#queryrangeCodeByfourCode; AttributeValueMapper#queryRangeByFourCode |
| 属性值解析规则 | 解析分类属性时，属性类型为single、multiple、list或multList的属性，要到物料属性值库里查询可选值；其他类型的属性可选值为空。 | 源码 | ClassificationAttributeRefServiceImpl#getParsedValue |
| 物料描述拼接规则 | 物料短描述和英文描述取是否进ERP物料短描述标识为X或XY的属性，物料长描述取标识为Y或XY的属性，均按物料短描述顺序升序拼接；顺序小于1000的作为前缀，大于1000的作为后缀，私有属性夹在前缀和后缀之间；同一成组属性之间用成组属性拼接符连接，其余用空格连接。 | 源码 | AddCodeApplyServiceImpl#generateDescriptions |
| 物料基础属性取值规则 | 创建物料基础属性时，物料名称属性取自物料分类的物料子类L4，物料简称属性取自物料分类的元器件物料简称，物料类型属性取自物料编码号段的物料类型，其余属性按申请信息填充。 | 源码 | AddCodeApplyServiceImpl#createPublicAttributes |
| 编码号段选取规则 | L1分类为38，或L4分类为40120101时，取该L4分类自己的号段；其他情况取L1分类加010101对应的号段。 | 源码 | CodeRangeServiceImpl#getCodeAndCommit |
| 汽车电子号段规则 | 汽车电子物料（即汽车电子BG的物料）使用汽车电子编码起始、汽车电子编码终止和汽车电子当前最大编码三个号段字段，其他物料使用普通的编码起始、编码终止和当前最大编码。 | 源码 | CodeRangeServiceImpl#getCodeAndCommit (addCodeApply.getEcar() == 1) |
| 旧物料编码校验规则 | 物料沿用旧物料编码时，旧物料编码必须是11位数字，不能与已有物料编码重复，且前4位必须与新生成编码的前4位一致。 | 源码 | CodeRangeServiceImpl#getCodeAndCommit |

## 应用场景

| 场景 | 说明 |
|---|---|
| 物料精确查找 | 根据物料编码、描述关键字、分类或属性值，定位到具体的物料。 |
| 物料相似查找 | 在同分类下找出属性相近的物料。 |
| 替代料推荐 | 为某个物料推荐可以替换的其他物料。 |
