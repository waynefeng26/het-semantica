"""把 MySQL 物料主数据按本体写入 Neo4j。

连接信息只从环境变量读取（见 matkg/neo4j_loader.py 顶部说明），例如 PowerShell：

    $env:MATKG_MYSQL_URL = "jdbc:mysql://10.16.25.98:3306/jeecg-boot"
    $env:MATKG_MYSQL_USER = "guest_select";  $env:MATKG_MYSQL_PASSWORD = "..."
    $env:MATKG_NEO4J_URI = "bolt://10.16.8.25:7687"
    $env:MATKG_NEO4J_USER = "neo4j";  $env:MATKG_NEO4J_PASSWORD = "..."

用法：
    python load_neo4j.py --dry-run                      只校验，不写 Neo4j
    python load_neo4j.py --reset --limit 20000          抽样 2 万条物料压测
    python load_neo4j.py --reset                        全量（可中断，再次运行自动续跑）
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from matkg.neo4j_loader import Config, LoadOptions, run_load  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="只做入图前校验")
    ap.add_argument("--reset", action="store_true", help="先清理本工具写入的节点（不动其它数据）")
    ap.add_argument("--limit", type=int, default=None, help="最多导入多少条物料主数据（压测用）")
    ap.add_argument("--batch-size", type=int, default=2000, help="每批物料主数据条数（默认 2000）")
    ap.add_argument("--tx-rows", type=int, default=4000, help="每个 Neo4j 事务的行数（默认 4000）")
    ap.add_argument("--no-basic-template-rel", action="store_true", help="基础属性不建到分类属性模板的关系（更快、更小）")
    ap.add_argument("--skip-ontology", action="store_true")
    ap.add_argument("--skip-dimensions", action="store_true")
    ap.add_argument("--ontology", default=str(HERE / "output" / "ontology.json"))
    ap.add_argument("--out", default=str(HERE / "output"))
    a = ap.parse_args()

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)  # 首次建库时的“属性不存在”提示无需展示
    opts = LoadOptions(batch_size=a.batch_size, tx_rows=a.tx_rows, limit_materials=a.limit,
                       basic_template_rel=not a.no_basic_template_rel)
    report = run_load(Config.from_env(), Path(a.ontology), Path(a.out), opts, reset=a.reset,
                      skip_ontology=a.skip_ontology, skip_dimensions=a.skip_dimensions, dry_run=a.dry_run,
                      progress=lambda s: print(s, flush=True))
    print("完成。报告：", Path(a.out) / "neo4j_load_report.md")
    if "neo4j_counts" in report:
        print(report["neo4j_counts"])


if __name__ == "__main__":
    main()
