#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反馈模块按时间统计脚本（交互式版，Plotly）

- 第4列：反馈模块
- 第10列：反馈时间
- 支持按频率分箱（默认 24 小时）
- 输出 HTML 交互图（可缩放、拖拽，自动用浏览器打开）

用法示例：
  python stats_plot_interactive.py --input tryoutput.csv --outdir plots \
    --module-col 4 --time-col 10 --freq 24H --start 2025-09-01 --end 2025-09-17
"""

import argparse
import os
import webbrowser
from typing import Optional, List

import pandas as pd

# 尝试多种常见编码读取
ENCODING_CANDIDATES: List[str] = ["utf-8", "utf-8-sig", "gb18030", "gbk", "cp936"]


def read_csv_auto(path: str) -> pd.DataFrame:
    last_err: Exception | None = None
    for enc in ENCODING_CANDIDATES:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_err = e
    raise last_err if last_err else RuntimeError("无法读取 CSV 文件：未知错误")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="反馈模块按时间统计（交互式 Plotly 版）")
    parser.add_argument("--input", required=True, help="输入 CSV 路径")
    parser.add_argument("--outdir", default="plots", help="输出目录，默认 plots")
    parser.add_argument("--module-col", type=int, default=4, help="模块列（从1开始），默认4")
    parser.add_argument("--time-col", type=int, default=10, help="时间列（从1开始），默认10")
    parser.add_argument("--freq", default="24H", help="分箱频率，默认24H，可为1H/2H/1D等")
    parser.add_argument("--start", help="开始日期/时间，例如 2025-09-01")
    parser.add_argument("--end", help="结束日期/时间，例如 2025-09-17")
    parser.add_argument("--no-browser", action="store_true", help="仅生成文件，不自动打开浏览器")
    return parser.parse_args()


def ensure_outdir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def build_range_name(start: Optional[pd.Timestamp], end: Optional[pd.Timestamp]) -> str:
    if start is None and end is None:
        return "full"
    fmt = "%Y%m%d%H%M%S"
    s = start.strftime(fmt) if start is not None else "min"
    e = end.strftime(fmt) if end is not None else "max"
    return f"{s}_{e}"


def plot_interactive(
    df: pd.DataFrame, range_label: str, outdir: str, freq: str, auto_open: bool = True
) -> None:
    try:
        import plotly.express as px
    except ImportError:
        raise RuntimeError("需要 plotly 才能绘图，请先运行: pip install plotly")

    if df.empty:
        print("警告：所选时间范围内无数据，跳过出图")
        return

    df = df.copy()
    df["time_bin"] = df["__dt__"].dt.floor(freq)

    pivot = (
        df.groupby(["time_bin", "__module__"]).size().reset_index(name="count")
    )

    fig = px.line(
        pivot,
        x="time_bin",
        y="count",
        color="__module__",
        markers=True,
        title=f"模块反馈计数（范围={range_label}，频率={freq}）"
    )

    fig.update_layout(
        xaxis_title="时间",
        yaxis_title="反馈数量",
        hovermode="x unified"
    )

    outfile = os.path.join(outdir, f"range_{range_label}.html")
    fig.write_html(outfile, include_plotlyjs="cdn")
    print(f"已输出交互图：{outfile}")

    if auto_open:
        webbrowser.open(f"file://{os.path.abspath(outfile)}")


def main() -> None:
    args = parse_args()
    ensure_outdir(args.outdir)

    df = read_csv_auto(args.input)

    mod_idx0 = args.module_col - 1
    time_idx0 = args.time_col - 1

    if df.shape[1] <= max(mod_idx0, time_idx0):
        raise IndexError(
            f"列数量不足：当前 {df.shape[1]} 列，需至少包含第{args.module_col}和第{args.time_col}列"
        )

    modules = df.iloc[:, mod_idx0]
    times = pd.to_datetime(df.iloc[:, time_idx0], errors="coerce")

    mask = times.notna() & modules.notna()
    data = pd.DataFrame({"__module__": modules[mask].astype(str), "__dt__": times[mask]})

    if data.empty:
        print("无有效数据可统计（时间或模块为空）")
        return

    start_ts: Optional[pd.Timestamp] = pd.to_datetime(args.start) if args.start else None
    end_ts: Optional[pd.Timestamp] = pd.to_datetime(args.end) if args.end else None

    if start_ts is not None:
        data = data[data["__dt__"] >= start_ts]
    if end_ts is not None:
        data = data[data["__dt__"] <= end_ts]

    range_label = build_range_name(start_ts, end_ts)
    plot_interactive(
        data,
        range_label=range_label,
        outdir=args.outdir,
        freq=args.freq,
        auto_open=not args.no_browser
    )


if __name__ == "__main__":
    main()
