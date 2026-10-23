"""运行：三元组抽取 → 语义分析 → 语义网络抽取。

用法：
    python run_pipeline.py [--java-root <addcode 目录>] [--out output]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DEFAULT_ROOT = r"D:\workspace\jeecg-boot\het-module-main\het-main\src\main\java\com\het\modules\addcode"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--java-root", default=DEFAULT_ROOT)
    ap.add_argument("--out", default=str(HERE / "output"))
    args = ap.parse_args()

    logging.basicConfig(level=logging.WARNING)
    from matkg.pipeline import run_all

    summary = run_all(args.java_root, args.out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
