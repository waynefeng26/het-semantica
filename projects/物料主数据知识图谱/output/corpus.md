# 抽取语料（由 Java 源码整理）


## entity:AddCodeApply

- 类型：entity
- 出处：AddCodeApply.java

物料主数据的业务口径：即加码申请表，业务上是物料主数据表，一行对应一个物料，记录物料编码、L1至L4分类、物料描述和申请状态。物料主数据（AddCodeApply）对应数据表ac_add_code_apply。物料主数据的关键字段包括L1分类、L2分类、L3分类、L4分类、物料编码、旧物料编码、物料短描述、物料长描述、英文描述、申请状态、是否临时码、是否汽车电子。物料主数据共有42个持久化字段。物料主数据的是否汽车电子使用yn字典。物料主数据的是否临时码使用yn字典。


## entity:AcAddCodeApplyAttr

- 类型：entity
- 出处：AcAddCodeApplyAttr.java

物料基础属性的业务口径：即加码申请基础属性，业务上是物料基础属性，也叫公有属性，是同一分类下物料共有的属性取值。物料基础属性（AcAddCodeApplyAttr）对应数据表ac_add_code_apply_attr。物料基础属性的关键字段包括加码id、属性代码、属性值、属性描述、属性类型。物料基础属性共有14个持久化字段。


## entity:AcAddCodeApplyAttrp

- 类型：entity
- 出处：AcAddCodeApplyAttrp.java

物料私有属性的业务口径：即加码申请私有属性，业务上是物料私有属性，也叫物料技术属性，是各分类自己特有的技术参数取值。物料私有属性（AcAddCodeApplyAttrp）对应数据表ac_add_code_apply_attrp。物料私有属性的关键字段包括加码id、属性代码、属性值、属性描述、属性类型。物料私有属性共有14个持久化字段。


## entity:ClassificationManagement

- 类型：entity
- 出处：ClassificationManagement.java

物料分类的业务口径：即分类维护，业务上是物料分类体系，分为L1至L4四级，L4是最末级分类。物料分类（ClassificationManagement）对应数据表ac_classification_management。物料分类的关键字段包括L1分类代码、L2分类代码、L3分类代码、L4分类代码、物料子类L4、元器件物料简称、是否涉及优选、标准件/非标准件。物料分类共有21个持久化字段。


## entity:AttributeManagement

- 类型：entity
- 出处：AttributeManagement.java

物料属性定义的业务口径：即属性维护，业务上是物料属性的定义清单，每个属性有属性代码和属性名称。物料属性定义（AttributeManagement）对应数据表ac_attribute_management。物料属性定义的关键字段包括属性代码、属性名称。物料属性定义共有8个持久化字段。


## entity:ClassificationAttributeRef

- 类型：entity
- 出处：ClassificationAttributeRef.java

物料分类属性模板的业务口径：即分类属性维护，业务上是物料分类属性模板，规定某个分类下有哪些属性、公有还是私有、必填与否、描述拼接顺序。物料分类属性模板（ClassificationAttributeRef）对应数据表ac_classification_attribute_ref。物料分类属性模板的关键字段包括L4分类代码、属性代码、公有属性/私有属性、属性类型、唯一性、物料短描述顺序、是否进ERP物料短描述、成组属性、成组属性拼接符、是否必填、默认值。物料分类属性模板共有33个持久化字段。物料分类属性模板的公有属性/私有属性使用pubOrPri字典。物料分类属性模板的属性类型使用attrType字典。物料分类属性模板的单选/多选使用smc字典。


## entity:AttributeValue

- 类型：entity
- 出处：AttributeValue.java

物料属性值库的业务口径：即属性值库维护，业务上是物料属性值库，保存单选、多选类属性的可选值及其描述。物料属性值库（AttributeValue）对应数据表ac_attribute_value。物料属性值库的关键字段包括L4分类代码、属性代码、项次代码、参数值、属性值描述。物料属性值库共有13个持久化字段。


## entity:CodeRange

- 类型：entity
- 出处：CodeRange.java

物料编码号段的业务口径：即编码范围，业务上是物料编码号段，按L4分类划分起止号段并记录当前最大编码，用于顺序分配物料编码。物料编码号段（CodeRange）对应数据表ac_code_range。物料编码号段的关键字段包括L4分类代码、编码起始、编码终止、当前最大编码、汽车电子编码起始、汽车电子编码终止、汽车电子当前最大编码、物料类型。物料编码号段共有18个持久化字段。


## relation:AcAddCodeApplyAttr-partOf-AddCodeApply

- 类型：relation
- 出处：AcAddCodeApplyAttrMapper.xml#selectByMainId (add_code_id = #{mainId})

物料基础属性属于物料主数据，关联字段为加码id。


## relation:AcAddCodeApplyAttrp-partOf-AddCodeApply

- 类型：relation
- 出处：AcAddCodeApplyAttrpMapper.xml#selectByMainId (add_code_id = #{mainId})

物料私有属性属于物料主数据，关联字段为加码id。


## relation:AddCodeApply-refersTo-ClassificationManagement

- 类型：relation
- 出处：AddCodeApply.java @Dict(dictTable=ac_classification_management)

物料主数据引用物料分类，关联字段为L1分类、L2分类、L3分类、L4分类。


## relation:AddCodeApply-refersTo-CodeRange

- 类型：relation
- 出处：CodeRangeServiceImpl#getCodeAndCommit (four_code = classifyL4 或 classifyL1+010101)

物料主数据引用物料编码号段，关联字段为L4分类。


## relation:ClassificationAttributeRef-refersTo-ClassificationManagement

- 类型：relation
- 出处：ClassificationAttributeRefController#queryById (classificationManagementService.queryByFourCode)

物料分类属性模板引用物料分类，关联字段为L4分类代码。


## relation:ClassificationAttributeRef-refersTo-AttributeManagement

- 类型：relation
- 出处：ClassificationAttributeRef.attributeCode 与 AttributeManagement.attributeCode 同名同义（未见显式 JOIN）

物料分类属性模板引用物料属性定义，关联字段为属性代码。


## relation:AttributeValue-refersTo-ClassificationAttributeRef

- 类型：relation
- 出处：ClassificationAttributeRefServiceImpl#getParsedValue (queryRangeByFourCode(ref.fourCode, ref.attributeCode))

物料属性值库引用物料分类属性模板，关联字段为L4分类代码、属性代码。


## relation:AttributeValue-refersTo-AttributeManagement

- 类型：relation
- 出处：AttributeValueServiceImpl#getSubdivisionDesc (attribute_code 过滤)

物料属性值库引用物料属性定义，关联字段为属性代码。


## relation:CodeRange-refersTo-ClassificationManagement

- 类型：relation
- 出处：ClassificationManagementController#page (codeRangeService.getByFourcode(record.fourCode))

物料编码号段引用物料分类，关联字段为L4分类代码。


## relation:AcAddCodeApplyAttr-refersTo-ClassificationAttributeRef

- 类型：relation
- 出处：AddCodeApplyServiceImpl#buildAttrList (attr.setAttrCode(ref.getAttributeCode()))

物料基础属性引用物料分类属性模板，关联字段为属性代码。


## relation:AcAddCodeApplyAttrp-refersTo-ClassificationAttributeRef

- 类型：relation
- 出处：AddCodeApplyServiceImpl#buildAttrpList (attrp.setAttrCode(ref.getAttributeCode()))

物料私有属性引用物料分类属性模板，关联字段为属性代码。


## attr:materialName

- 类型：attribute
- 出处：业务方说明; AcAddCodeApplyAttrMapper.xml#getMaterialNameByMaterialNo; AddCodeApplyServiceImpl#createPublicAttributes

物料基础属性包含常用属性物料名称属性。物料名称属性（materialName）：物料的名称，创建时默认就是物料子类L4的名称，是查找物料时最直观的属性。物料名称属性取自物料子类L4。


## attr:materialAbbreviation

- 类型：attribute
- 出处：AddCodeApplyServiceImpl#createPublicAttributes

物料基础属性包含常用属性物料简称属性。物料简称属性（materialAbbreviation）：物料的简称，创建时默认来自分类上的元器件物料简称。物料简称属性取自元器件物料简称。


## attr:materialType

- 类型：attribute
- 出处：AddCodeApplyServiceImpl#createPublicAttributes

物料基础属性包含常用属性物料类型属性。物料类型属性（materialType）：物料类型，创建时默认来自所在号段的物料类型。物料类型属性取自物料类型。


## attr:lifeCyclePhase

- 类型：attribute
- 出处：业务方说明; AddCodeApplyController#checkLifeCyclePhase

物料基础属性包含常用属性生命周期阶段属性。生命周期阶段属性（lifeCyclePhase）：物料在业务上的物料状态，分为研发、测试、试产、批量、EOL、部分失效、采购失效、完全失效、完全停产。


## attr:preferredIdentification

- 类型：attribute
- 出处：业务方说明; AcAddCodeApplyAttrServiceImpl#batchUpdateMaterialAttributes

物料基础属性包含常用属性优选标识属性。优选标识属性（preferredIdentification）：由采购维护，标记物料是否为某个BG的优选物料；被标记为优选的物料，研发设计BOM时会优先考虑。


## attr:manufacturerAvlRating

- 类型：attribute
- 出处：业务方说明; AddCodeApplyController#checkParam

物料基础属性包含常用属性制造商AVL等级属性。制造商AVL等级属性（manufacturerAvlRating）：物料对应制造商的AVL等级，每天晚上定时根据采购维护的制造商等级更新；研发设计BOM时优先考虑主力、合格、试用的物料。


## attr:notes

- 类型：attribute
- 出处：业务方说明

物料基础属性包含常用属性专用客户属性。专用客户属性（notes）：该属性有值表示物料是某个客户的专用料，属性值保存的是客户编码：A001为兰吉尔，A002为京瓷，目前只有这两个客户。


## attr:manufacturerPartNumber

- 类型：attribute
- 出处：业务方说明; AddCodeApplyController#dupCheck; ClassificationAttributeRefController (标准件临时码仅MPN必填)

物料基础属性包含常用属性制造商零件编号属性。制造商零件编号属性（manufacturerPartNumber）：制造商零件编号，即MPN，是识别通用件的关键属性，与制造商名称一起用于查重和检索；标准件临时码只要求必填它。


## attr:manufacturersName

- 类型：attribute
- 出处：业务方说明; AddCodeApplyController#dupCheck; AcAddCodeApplyAttrServiceImpl#getByMainIdAndPurchase

物料基础属性包含常用属性制造商名称属性。制造商名称属性（manufacturersName）：物料对应的制造商名称，与制造商零件编号或图号一起用于查重和检索。


## attr:mapNumber

- 类型：attribute
- 出处：AddCodeApplyController#dupCheck

物料基础属性包含常用属性图号属性。图号属性（mapNumber）：定制件的图号，定制件靠它加制造商名称识别同一物料。


## attr:projectType

- 类型：attribute
- 出处：AcAddCodeApplyAttrServiceImpl#getByMainIdAndPurchase

物料基础属性包含常用属性项目类型属性。项目类型属性（projectType）：物料所属项目的类型。


## attr:brandExceptionType

- 类型：attribute
- 出处：AddCodeApplyController#checkParam

物料基础属性包含常用属性品牌异常类型属性。品牌异常类型属性（brandExceptionType）：品牌异常的类型；制造商AVL等级为考察、限制时必填，为主力、合格、试用时不能填写。


## attr:subdivision

- 类型：attribute
- 出处：AttributeValueServiceImpl#getSubdivisionDesc

物料基础属性包含常用属性细分类属性。细分类属性（subdivision）：物料的细分类，取值的描述存放在物料属性值库里。


## attr:documentNumber

- 类型：attribute
- 出处：AddCodeApplyServiceImpl#handleNeed

物料基础属性包含常用属性文档编号属性。文档编号属性（documentNumber）：物料关联的文档编号。


## attrs:core

- 类型：attribute
- 出处：业务方说明

物料基础属性的核心属性包括物料名称属性、制造商零件编号属性、制造商名称属性。


## enum:申请状态

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#importExcel (applyStatus=0 草稿)

申请状态的枚举值包括申请状态-草稿、申请状态-标准化审批中、申请状态-审批完成、申请状态-SCM采购审批中、申请状态-退回、申请状态-历史版本。


## enumval:申请状态-草稿

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#importExcel (applyStatus=0 草稿)

申请状态-草稿（0）：申请还没有提交。


## enumval:申请状态-标准化审批中

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#importExcel (applyStatus=0 草稿)

申请状态-标准化审批中（1）：申请已提交，正在标准化审批。


## enumval:申请状态-审批完成

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#importExcel (applyStatus=0 草稿)

申请状态-审批完成（2）：审批通过的有效数据，同一物料编码只有一条。


## enumval:申请状态-SCM采购审批中

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#importExcel (applyStatus=0 草稿)

申请状态-SCM采购审批中（3）：申请正在SCM采购审批。


## enumval:申请状态-退回

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#importExcel (applyStatus=0 草稿)

申请状态-退回（4）：申请被退回。


## enumval:申请状态-历史版本

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#importExcel (applyStatus=0 草稿)

申请状态-历史版本（5）：物料升级后被新版本取代的旧记录。


## enum:生命周期阶段

- 类型：enum
- 出处：业务方说明

生命周期阶段属性的枚举值包括生命周期阶段-研发、生命周期阶段-测试、生命周期阶段-试产、生命周期阶段-批量、生命周期阶段-EOL、生命周期阶段-部分失效、生命周期阶段-采购失效、生命周期阶段-完全失效、生命周期阶段-完全停产。


## enumval:生命周期阶段-研发

- 类型：enum
- 出处：业务方说明

生命周期阶段-研发（YF）：物料处于研发阶段。


## enumval:生命周期阶段-测试

- 类型：enum
- 出处：业务方说明

生命周期阶段-测试（NA）：物料处于测试阶段。


## enumval:生命周期阶段-试产

- 类型：enum
- 出处：业务方说明

生命周期阶段-试产（CA）：物料处于试产阶段。


## enumval:生命周期阶段-批量

- 类型：enum
- 出处：业务方说明

生命周期阶段-批量（AP）：物料处于批量阶段。


## enumval:生命周期阶段-EOL

- 类型：enum
- 出处：业务方说明

生命周期阶段-EOL（00）：物料为EOL状态。


## enumval:生命周期阶段-部分失效

- 类型：enum
- 出处：业务方说明

生命周期阶段-部分失效（02）：物料部分失效。


## enumval:生命周期阶段-采购失效

- 类型：enum
- 出处：业务方说明

生命周期阶段-采购失效（03）：物料对采购失效。


## enumval:生命周期阶段-完全失效

- 类型：enum
- 出处：业务方说明

生命周期阶段-完全失效（04）：物料完全失效。


## enumval:生命周期阶段-完全停产

- 类型：enum
- 出处：业务方说明

生命周期阶段-完全停产（99）：物料完全停产。


## enum:优选标识

- 类型：enum
- 出处：业务方说明

优选标识属性的枚举值包括优选标识-优选A、优选标识-优选B、优选标识-优选1(汽电)。


## enumval:优选标识-优选A

- 类型：enum
- 出处：业务方说明

优选标识-优选A：采购标记为优选A的物料，研发设计BOM时会优先考虑。优选标识-优选A标识海外家电BG的优选物料。


## enumval:优选标识-优选B

- 类型：enum
- 出处：业务方说明

优选标识-优选B：采购标记为优选B的物料，研发设计BOM时会优先考虑。优选标识-优选B标识国内家电BG的优选物料。


## enumval:优选标识-优选1(汽电)

- 类型：enum
- 出处：业务方说明

优选标识-优选1(汽电)：采购标记为优选1(汽电)的物料，研发设计BOM时会优先考虑。优选标识-优选1(汽电)标识汽车电子BG的优选物料。


## enum:专用客户

- 类型：enum
- 出处：业务方说明

专用客户属性的枚举值包括专用客户-兰吉尔、专用客户-京瓷。


## enumval:专用客户-兰吉尔

- 类型：enum
- 出处：业务方说明

专用客户-兰吉尔（A001）：客户兰吉尔的专用料，属性值保存客户编码A001。


## enumval:专用客户-京瓷

- 类型：enum
- 出处：业务方说明

专用客户-京瓷（A002）：客户京瓷的专用料，属性值保存客户编码A002。


## enum:制造商AVL等级

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#checkParam

制造商AVL等级属性的枚举值包括制造商AVL等级-主力、制造商AVL等级-合格、制造商AVL等级-试用、制造商AVL等级-考察、制造商AVL等级-限制。


## enumval:制造商AVL等级-主力

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#checkParam

制造商AVL等级-主力：研发设计BOM时优先考虑。


## enumval:制造商AVL等级-合格

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#checkParam

制造商AVL等级-合格：研发设计BOM时优先考虑。


## enumval:制造商AVL等级-试用

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#checkParam

制造商AVL等级-试用：研发设计BOM时优先考虑。


## enumval:制造商AVL等级-考察

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#checkParam

制造商AVL等级-考察：物料对应的制造商不合格或未验证，研发设计BOM时不优先考虑。


## enumval:制造商AVL等级-限制

- 类型：enum
- 出处：业务方说明; AddCodeApplyController#checkParam

制造商AVL等级-限制：处理方式和考察一样：物料对应的制造商不合格或未验证，研发设计BOM时不优先考虑。


## bg:是否汽车电子:汽车电子BG

- 类型：enum
- 出处：业务方说明; CodeRangeServiceImpl#getCodeAndCommit (ecar == 1)

是否汽车电子标明汽车电子BG的物料。


## rule:有效物料判定规则

- 类型：rule
- 出处：业务方说明

有效物料判定规则：物料主数据的申请状态表示申请审批状态，申请状态为2即审批完成的记录才是有效物料。同一个物料编码，申请状态为2的记录只有一条，进入图数据库的物料主数据只取申请状态为2的记录。


## rule:物料升级规则

- 类型：rule
- 出处：业务方说明

物料升级规则：物料升级时会新建一条物料主数据，物料编码保持不变；新建的升级记录审批通过后，申请状态改为2，原来申请状态为2的记录改为5即历史版本，因此同一物料编码始终只有一条有效记录。


## rule:物料状态口径规则

- 类型：rule
- 出处：业务方说明

物料状态口径规则：物料在业务上的物料状态以生命周期阶段属性为准。


## rule:物料编码BG前缀规则

- 类型：rule
- 出处：业务方说明

物料编码BG前缀规则：汽车电子BG的物料编码以2开头，其他BG的物料编码以1开头；汽车电子BG的物料，其是否汽车电子为是。


## rule:物料查重规则

- 类型：rule
- 出处：AddCodeApplyController#dupCheck

物料查重规则：新增物料前要查重：通用件按制造商零件编号属性加制造商名称属性查重，定制件按图号属性加制造商名称属性查重；查重时排除当前记录、升级前的历史版本，以及LOA标识为是的物料。


## rule:同MPN替代规则

- 类型：rule
- 出处：业务方说明

同MPN替代规则：制造商零件编号属性相同但制造商名称属性不同的物料，算替代料。


## rule:替代料判断流程

- 类型：rule
- 出处：业务方说明

替代料判断流程：判断两个制造商零件编号属性对应的物料是否互为替代料：先由制造商零件编号属性找到所在的物料主数据，再由物料主数据的L4分类找到对应的物料分类属性模板，进而找到该分类下的物料私有属性，比较两个物料的核心技术属性（物料私有属性中，物料分类属性模板的是否必填为X的属性）是否相近，相近的标准因分类而异，相近则互为替代料。


## rule:核心技术属性判定规则

- 类型：rule
- 出处：业务方说明

核心技术属性判定规则：物料私有属性中，物料分类属性模板的是否必填为X的属性，是核心技术属性；公有属性不算核心技术属性。


## rule:分类相近标准规则

- 类型：rule
- 出处：业务方说明

分类相近标准规则：物料相近的标准因分类而异，没有统一标准，核心技术属性取值的单位一般是统一的，按绝对差比较。L1分类为28（包材）的物料，核心技术属性里凡是长、宽、高这类尺寸数值属性，该分类有哪些就比较哪些，取值之差都在正负5以内才表示相近，可以互为替代料或相似料；不是每个包材分类都有长、宽、高。哪些属性算尺寸类，目前先按属性名称判断。


## rule:MPN相近替代判断规则

- 类型：rule
- 出处：业务方说明

MPN相近替代判断规则：制造商零件编号属性的前缀或系列号相同，不能单独判断是否算替代料，要结合L4分类和物料私有属性一起判断。


## rule:客户专用料规则

- 类型：rule
- 出处：业务方说明

客户专用料规则：专用客户属性有值的物料是客户专用料，属性值保存的是客户编码（A001对应兰吉尔，A002对应京瓷），目前只有这两个客户。研发查找物料时可以过滤掉客户专用料。


## rule:分类代码层级规则

- 类型：rule
- 出处：ClassificationAttributeRefServiceImpl#queryrangeCodeByfourCode (fourCode.substring(0, 2)); AddCodeApply.java @Dict

分类代码层级规则：L4分类代码的前两位就是L1分类代码；物料主数据的L1分类、L2分类、L3分类、L4分类，分别对应物料分类里的L1分类代码、L2分类代码、L3分类代码、L4分类代码。


## rule:分类属性范围匹配规则

- 类型：rule
- 出处：ClassificationAttributeRefMapper.xml#queryrangeCodeByfourCode; AttributeValueMapper#queryRangeByFourCode

分类属性范围匹配规则：物料分类属性模板与物料属性值库的L4分类代码有三种写法：具体的L4分类代码、L1分类代码，以及形如起始-终止的L1分类范围。按L4分类代码查询时，命中任意一种写法的记录都会返回，并按排序和物料短描述顺序排列。


## rule:属性值解析规则

- 类型：rule
- 出处：ClassificationAttributeRefServiceImpl#getParsedValue

属性值解析规则：解析分类属性时，属性类型为single、multiple、list或multList的属性，要到物料属性值库里查询可选值；其他类型的属性可选值为空。


## rule:物料描述拼接规则

- 类型：rule
- 出处：AddCodeApplyServiceImpl#generateDescriptions

物料描述拼接规则：物料短描述和英文描述取是否进ERP物料短描述标识为X或XY的属性，物料长描述取标识为Y或XY的属性，均按物料短描述顺序升序拼接；顺序小于1000的作为前缀，大于1000的作为后缀，私有属性夹在前缀和后缀之间；同一成组属性之间用成组属性拼接符连接，其余用空格连接。


## rule:物料基础属性取值规则

- 类型：rule
- 出处：AddCodeApplyServiceImpl#createPublicAttributes

物料基础属性取值规则：创建物料基础属性时，物料名称属性取自物料分类的物料子类L4，物料简称属性取自物料分类的元器件物料简称，物料类型属性取自物料编码号段的物料类型，其余属性按申请信息填充。


## rule:编码号段选取规则

- 类型：rule
- 出处：CodeRangeServiceImpl#getCodeAndCommit

编码号段选取规则：L1分类为38，或L4分类为40120101时，取该L4分类自己的号段；其他情况取L1分类加010101对应的号段。


## rule:汽车电子号段规则

- 类型：rule
- 出处：CodeRangeServiceImpl#getCodeAndCommit (addCodeApply.getEcar() == 1)

汽车电子号段规则：汽车电子物料（即汽车电子BG的物料）使用汽车电子编码起始、汽车电子编码终止和汽车电子当前最大编码三个号段字段，其他物料使用普通的编码起始、编码终止和当前最大编码。


## rule:旧物料编码校验规则

- 类型：rule
- 出处：CodeRangeServiceImpl#getCodeAndCommit

旧物料编码校验规则：物料沿用旧物料编码时，旧物料编码必须是11位数字，不能与已有物料编码重复，且前4位必须与新生成编码的前4位一致。


## governed:AddCodeApply:有效物料判定规则

- 类型：rule
- 出处：业务方说明

物料主数据受有效物料判定规则约束。


## governed:AddCodeApply:物料升级规则

- 类型：rule
- 出处：业务方说明

物料主数据受物料升级规则约束。


## governed:AddCodeApply:物料状态口径规则

- 类型：rule
- 出处：业务方说明

物料主数据受物料状态口径规则约束。


## governed:AddCodeApply:物料编码BG前缀规则

- 类型：rule
- 出处：业务方说明

物料主数据受物料编码BG前缀规则约束。


## governed:AddCodeApply:物料描述拼接规则

- 类型：rule
- 出处：AddCodeApplyServiceImpl#generateDescriptions

物料主数据受物料描述拼接规则约束。


## governed:AddCodeApply:旧物料编码校验规则

- 类型：rule
- 出处：CodeRangeServiceImpl#getCodeAndCommit

物料主数据受旧物料编码校验规则约束。


## governed:AddCodeApply:物料查重规则

- 类型：rule
- 出处：AddCodeApplyController#dupCheck

物料主数据受物料查重规则约束。


## governed:AddCodeApply:分类代码层级规则

- 类型：rule
- 出处：ClassificationAttributeRefServiceImpl#queryrangeCodeByfourCode (fourCode.substring(0, 2)); AddCodeApply.java @Dict

物料主数据受分类代码层级规则约束。


## governed:AcAddCodeApplyAttr:物料基础属性取值规则

- 类型：rule
- 出处：AddCodeApplyServiceImpl#createPublicAttributes

物料基础属性受物料基础属性取值规则约束。


## governed:AcAddCodeApplyAttr:客户专用料规则

- 类型：rule
- 出处：业务方说明

物料基础属性受客户专用料规则约束。


## governed:AcAddCodeApplyAttr:物料查重规则

- 类型：rule
- 出处：AddCodeApplyController#dupCheck

物料基础属性受物料查重规则约束。


## governed:AcAddCodeApplyAttr:同MPN替代规则

- 类型：rule
- 出处：业务方说明

物料基础属性受同MPN替代规则约束。


## governed:AcAddCodeApplyAttr:MPN相近替代判断规则

- 类型：rule
- 出处：业务方说明

物料基础属性受MPN相近替代判断规则约束。


## governed:AcAddCodeApplyAttr:替代料判断流程

- 类型：rule
- 出处：业务方说明

物料基础属性受替代料判断流程约束。


## governed:AcAddCodeApplyAttrp:替代料判断流程

- 类型：rule
- 出处：业务方说明

物料私有属性受替代料判断流程约束。


## governed:ClassificationManagement:分类代码层级规则

- 类型：rule
- 出处：ClassificationAttributeRefServiceImpl#queryrangeCodeByfourCode (fourCode.substring(0, 2)); AddCodeApply.java @Dict

物料分类受分类代码层级规则约束。


## governed:ClassificationManagement:分类相近标准规则

- 类型：rule
- 出处：业务方说明

物料分类受分类相近标准规则约束。


## governed:ClassificationAttributeRef:分类属性范围匹配规则

- 类型：rule
- 出处：ClassificationAttributeRefMapper.xml#queryrangeCodeByfourCode; AttributeValueMapper#queryRangeByFourCode

物料分类属性模板受分类属性范围匹配规则约束。


## governed:ClassificationAttributeRef:属性值解析规则

- 类型：rule
- 出处：ClassificationAttributeRefServiceImpl#getParsedValue

物料分类属性模板受属性值解析规则约束。


## governed:ClassificationAttributeRef:物料描述拼接规则

- 类型：rule
- 出处：AddCodeApplyServiceImpl#generateDescriptions

物料分类属性模板受物料描述拼接规则约束。


## governed:ClassificationAttributeRef:核心技术属性判定规则

- 类型：rule
- 出处：业务方说明

物料分类属性模板受核心技术属性判定规则约束。


## governed:AttributeValue:分类属性范围匹配规则

- 类型：rule
- 出处：ClassificationAttributeRefMapper.xml#queryrangeCodeByfourCode; AttributeValueMapper#queryRangeByFourCode

物料属性值库受分类属性范围匹配规则约束。


## governed:AttributeValue:属性值解析规则

- 类型：rule
- 出处：ClassificationAttributeRefServiceImpl#getParsedValue

物料属性值库受属性值解析规则约束。


## governed:CodeRange:编码号段选取规则

- 类型：rule
- 出处：CodeRangeServiceImpl#getCodeAndCommit

物料编码号段受编码号段选取规则约束。


## governed:CodeRange:汽车电子号段规则

- 类型：rule
- 出处：CodeRangeServiceImpl#getCodeAndCommit (addCodeApply.getEcar() == 1)

物料编码号段受汽车电子号段规则约束。


## scenario:物料精确查找

- 类型：scenario
- 出处：lexicon.SCENARIOS

物料精确查找：根据物料编码、描述关键字、分类或属性值，定位到具体的物料。


## scenario:物料相似查找

- 类型：scenario
- 出处：lexicon.SCENARIOS

物料相似查找：在同分类下找出属性相近的物料。


## scenario:替代料推荐

- 类型：scenario
- 出处：lexicon.SCENARIOS

替代料推荐：为某个物料推荐可以替换的其他物料。


## support:AddCodeApply:物料精确查找

- 类型：support
- 出处：AddCodeApply.java

物料主数据支持物料精确查找。物料主数据一行对应一个物料，物料编码、分类、描述和状态都在这张表里。


## support:物料编码:物料精确查找

- 类型：support
- 出处：业务方说明

物料编码支持物料精确查找。物料编码首位数字区分BG：汽车电子BG以2开头，其他BG以1开头；同一物料编码只有一条申请状态为2的有效记录。


## support:旧物料编码:物料精确查找

- 类型：support
- 出处：CodeRangeServiceImpl#getCodeAndCommit

旧物料编码支持物料精确查找。新物料可以沿用旧物料编码，可用来从老编码反查物料。


## support:申请状态:物料精确查找

- 类型：support
- 出处：业务方说明

申请状态支持物料精确查找。只有申请状态为2的记录才是有效物料，其他状态的记录不进入图谱。


## support:L4分类:物料精确查找

- 类型：support
- 出处：AddCodeApply.java @Dict

L4分类支持物料精确查找。物料主数据按L4分类归类，可先按分类缩小范围。


## support:AcAddCodeApplyAttr:物料精确查找

- 类型：support
- 出处：AcAddCodeApplyAttrMapper.xml#getMaterialNameByMaterialNo

物料基础属性支持物料精确查找。物料名称等基础属性通过加码id挂在物料主数据上。


## support:物料名称属性:物料精确查找

- 类型：support
- 出处：AcAddCodeApplyAttrMapper.xml#getMaterialNameByMaterialNo

物料名称属性支持物料精确查找。按物料编码可以查到物料名称。


## support:物料短描述:物料精确查找

- 类型：support
- 出处：AddCodeApplyServiceImpl#generateDescriptions

物料短描述支持物料精确查找。描述由属性值按固定顺序拼接而成，可以用关键字检索。


## support:物料长描述:物料精确查找

- 类型：support
- 出处：AddCodeApplyServiceImpl#generateDescriptions

物料长描述支持物料精确查找。长描述包含更完整的属性值，可以用关键字检索。


## support:属性值:物料精确查找

- 类型：support
- 出处：AcAddCodeApplyAttr.java

属性值支持物料精确查找。属性代码加属性值的组合，可以按参数筛选物料。


## support:制造商名称属性:物料精确查找

- 类型：support
- 出处：AddCodeApplyController#queryPageList (selectAttr)

制造商名称属性支持物料精确查找。列表可以按制造商名称过滤物料，并与制造商零件编号一起识别同一物料。


## support:制造商零件编号属性:物料精确查找

- 类型：support
- 出处：AddCodeApplyController#queryPageList (selectAttr)

制造商零件编号属性支持物料精确查找。列表可以按制造商零件编号过滤物料；通用件靠它加制造商名称识别同一物料。


## support:图号属性:物料精确查找

- 类型：support
- 出处：AddCodeApplyController#queryPageList (selectAttr)

图号属性支持物料精确查找。列表可以按图号过滤物料；定制件靠它加制造商名称识别同一物料。


## support:生命周期阶段属性:物料精确查找

- 类型：support
- 出处：业务方说明

生命周期阶段属性支持物料精确查找。它是物料在业务上的状态，可以排除失效、停产的物料。


## support:专用客户属性:物料精确查找

- 类型：support
- 出处：业务方说明

专用客户属性支持物料精确查找。有值说明是客户专用料，研发查找物料时可以过滤掉这些专用料；属性值是客户编码A001（兰吉尔）或A002（京瓷）。


## support:是否汽车电子:物料精确查找

- 类型：support
- 出处：业务方说明

是否汽车电子支持物料精确查找。可据此区分汽车电子BG的物料和其他BG的物料。


## support:L4分类:物料相似查找

- 类型：support
- 出处：ClassificationAttributeRefServiceImpl#queryrangeCodeByfourCode

L4分类支持物料相似查找。同一L4分类下的物料适用同一套属性模板，才有可比性。


## support:ClassificationAttributeRef:物料相似查找

- 类型：support
- 出处：ClassificationAttributeRef.java

物料分类属性模板支持物料相似查找。模板规定了每类物料有哪些属性，是比较的依据。


## support:是否必填:物料相似查找

- 类型：support
- 出处：业务方说明

是否必填支持物料相似查找。物料私有属性里该标识为X的属性是核心技术属性，比较物料是否相似时以它们为准。


## support:是否必填:替代料推荐

- 类型：support
- 出处：业务方说明

是否必填支持替代料推荐。物料私有属性里该标识为X的属性是核心技术属性，判断能否替代时以它们为准。


## support:属性值:物料相似查找

- 类型：support
- 出处：AcAddCodeApplyAttr.java

属性值支持物料相似查找。属性值越接近，物料越相似。


## support:物料短描述:物料相似查找

- 类型：support
- 出处：AddCodeApplyServiceImpl#generateDescriptions

物料短描述支持物料相似查找。描述的拼接顺序相同，描述文本可以用来比较相近程度。


## support:AcAddCodeApplyAttrp:物料相似查找

- 类型：support
- 出处：AcAddCodeApplyAttrp.java

物料私有属性支持物料相似查找。私有属性是各分类特有的技术参数，决定物料是否相似。


## support:细分类属性:物料相似查找

- 类型：support
- 出处：AttributeValueServiceImpl#getSubdivisionDesc

细分类属性支持物料相似查找。细分类相同说明物料更接近。


## support:AcAddCodeApplyAttrp:替代料推荐

- 类型：support
- 出处：AcAddCodeApplyAttrp.java

物料私有属性支持替代料推荐。技术参数一致是替代的前提。


## support:是否涉及优选:替代料推荐

- 类型：support
- 出处：AddCodeApplyServiceImpl#pushMainData

是否涉及优选支持替代料推荐。替代时应优先推荐优选物料。


## support:优选标识属性:替代料推荐

- 类型：support
- 出处：业务方说明

优选标识属性支持替代料推荐。被标记为优选的物料研发设计BOM时优先考虑，推荐替代料时应优先给出，并注意优选所属的BG。


## support:制造商AVL等级属性:替代料推荐

- 类型：support
- 出处：业务方说明

制造商AVL等级属性支持替代料推荐。优先推荐主力、合格、试用的物料；考察、限制表示制造商不合格或未验证，不宜优先推荐。


## support:标准件/非标准件:替代料推荐

- 类型：support
- 出处：ClassificationManagement.java

标准件/非标准件支持替代料推荐。标准件之间更容易互相替换。


## support:制造商名称属性:替代料推荐

- 类型：support
- 出处：业务方说明

制造商名称属性支持替代料推荐。制造商零件编号相同、制造商不同的物料算替代料，判断时要对照制造商。


## support:制造商零件编号属性:替代料推荐

- 类型：support
- 出处：业务方说明

制造商零件编号属性支持替代料推荐。制造商零件编号相同、制造商不同的物料算替代料；前缀或系列号相同还要结合L4分类和物料私有属性判断。


## support:制造商零件编号属性:物料相似查找

- 类型：support
- 出处：业务方说明

制造商零件编号属性支持物料相似查找。制造商零件编号是比较物料相似程度的依据之一。


## support:生命周期阶段属性:替代料推荐

- 类型：support
- 出处：业务方说明

生命周期阶段属性支持替代料推荐。物料进入EOL或失效、停产后，需要为它找替代；推荐的替代料自身也不应是失效或停产的。


## support:专用客户属性:替代料推荐

- 类型：support
- 出处：业务方说明

专用客户属性支持替代料推荐。推荐替代料时同样应该过滤掉客户专用料。
