"""物料主数据知识图谱（基于 Semantica）。

当前范围：``addcode`` 模块中 8 个核心实体及其 service 层，完成三个阶段：

1. 三元组抽取   TripletExtractor
2. 语义分析     SemanticAnalyzer（角色 / 相似度 / 聚类）
3. 语义网络抽取 SemanticNetworkExtractor

LLM 增强、校验、导出待确认后再做。
"""

__version__ = "0.2.0"
