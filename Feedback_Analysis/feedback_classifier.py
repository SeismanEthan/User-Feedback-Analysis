#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CSV 反馈模块标注脚本（规则匹配+大模型补全）

用法示例：
  python feedback_classifier.py --input tryinput.csv --output tryoutput.csv \
    --module-col 4 --strategy first --mode overwrite

核心逻辑：
1. 先用规则匹配
2. 对未匹配成功的内容，调用大模型API进行补全
3. 最终输出完整的标注结果
"""

from __future__ import annotations

import argparse
import os
import csv
import json
import requests
from typing import List, Dict, Any, Tuple

import pandas as pd

def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"配置文件 {config_path} 未找到，使用默认配置")
        return {
            "api": {
                "spark": {
                    "api_key": "",
                    "api_url": "https://spark-api-open.xf-yun.com/v2/chat/completions",
                    "model": "x1",
                    "max_tokens": 100,
                    "temperature": 0.7,
                    "top_k": 2,
                    "system_prompt": (
                        "作为学习App用户反馈分类员，任务是用户反馈，将其准确归类至以下标签中的一个如果包含多个就要选择多个回复。请注意，将仅返回与用户反馈内容匹配的标签，思考内容不要展示，不做任何额外回复。标签包含：\n"
                        "【学伴】涉及成长陪伴、元气值、升级石等相关反馈\n"
                        "【卡顿】针对使用过程中出现卡顿、延迟等体验问题\n"
                        "【抽卡】涵盖SSR、SR、卡包等游戏化激励模块的反馈\n"
                        "【VIP】任何与充值、会员服务相关的意见或问题\n"
                        "【奖学金】与学习奖励获取、兑换资格等相关的内容\n"
                        "【排行榜】包括学力值日榜、省份月榜等排名相关反馈\n"
                        "【兑换商店】涉及奖学金兑换、周边商品、发货延迟等事务\n"
                        "【我的】中心功能、个人信息管理等相关反馈\n"
                        "【欧粉说】社区发帖、互动、内容相关的建议或问题\n"
                        "【签到】每周打卡功能、奖励领取异常等反馈\n"
                        "【教材】一些新科目的缺少，现已有教材的版本问题\n"
                    )
                }
            },
            "rules": []
        }

def get_api_key(config: Dict[str, Any]) -> str:
    """获取API密钥，优先使用环境变量"""
    api_key = os.environ.get('SPARK_API_KEY', '')
    if not api_key:
        api_key = config.get("api", {}).get("spark", {}).get("api_key", '')
    return api_key

def call_spark_api(user_content: str, config: Dict[str, Any]) -> str:
    """调用讯飞星火API"""
    api_config = config.get("api", {}).get("spark", {})
    url = api_config.get("api_url", "https://spark-api-open.xf-yun.com/v2/chat/completions")
    api_key = get_api_key(config)
    
    if not api_key:
        print("错误：未配置API密钥")
        return ""
    
    system_prompt = api_config.get(
        "system_prompt",
        (
            "作为学习App用户反馈分类员，任务是用户反馈，将其准确归类至以下标签中的一个如果包含多个就要选择多个回复。请注意，将仅返回与用户反馈内容匹配的标签，思考内容不要展示，不做任何额外回复。标签包含：\n"
            "【学伴】涉及成长陪伴、元气值、升级石等相关反馈\n"
            "【卡顿】针对使用过程中出现卡顿、延迟等体验问题\n"
            "【抽卡】涵盖SSR、SR、卡包等游戏化激励模块的反馈\n"
            "【VIP】任何与充值、会员服务相关的意见或问题\n"
            "【奖学金】与学习奖励获取、兑换资格等相关的内容\n"
            "【排行榜】包括学力值日榜、省份月榜等排名相关反馈\n"
            "【兑换商店】涉及奖学金兑换、周边商品、发货延迟等事务\n"
            "【我的】中心功能、个人信息管理等相关反馈\n"
            "【欧粉说】社区发帖、互动、内容相关的建议或问题\n"
            "【签到】每周打卡功能、奖励领取异常等反馈\n"
            "【教材】一些新科目的缺少，现已有教材的版本问题\n"
        ),
    )

    data = {
        "max_tokens": api_config.get("max_tokens", 100),
        "top_k": api_config.get("top_k", 2),
        "temperature": api_config.get("temperature", 0.7),
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        "model": api_config.get("model", "x1"),
        "stream": True
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=30)
        response.raise_for_status()
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                try:
                    if line.startswith('data: '):
                        line = line[6:]
                    
                    if line.strip() == '[DONE]':
                        break
                    
                    json_data = json.loads(line)
                    if 'choices' in json_data and len(json_data['choices']) > 0:
                        delta = json_data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            full_response += content
                except json.JSONDecodeError:
                    pass
        
        return full_response.strip()
        
    except requests.exceptions.RequestException as e:
        print(f"API调用失败: {e}")
        return ""

def extract_text_inside_brackets(text: str) -> str | None:
    """提取【】中的内容；若不存在则返回None"""
    if not text:
        return None
    start = text.find("【")
    end = text.find("】", start + 1) if start != -1 else -1
    if start != -1 and end != -1 and end > start + 1:
        inner = text[start + 1:end].strip()
        return inner if inner else None
    return None

def postprocess_llm_output(raw_output: str) -> str:
    """
    后处理大模型输出：
    1) 如果包含敏感提示语，则直接返回“其他：”
    2) 否则提取【】中的内容；若没有【】则返回原文去除首尾空白
    """
    if not raw_output:
        return ""
    normalized = str(raw_output).strip()
    if "使用粗鲁、不礼貌和侮辱性的语言是不恰当的" in normalized:
        return "其他："
    inner = extract_text_inside_brackets(normalized)
    return inner if inner is not None else normalized

def read_csv_auto(path: str) -> pd.DataFrame:
    """读取CSV自动尝试多种编码"""
    candidates = ["utf-8", "utf-8-sig", "gb18030", "gbk", "cp936"]
    last_err: Exception | None = None
    for enc in candidates:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_err = e
    raise last_err if last_err else RuntimeError("无法读取 CSV 文件：未知错误")

def apply_rules(
    df: pd.DataFrame,
    rules: List[Dict[str, Any]],
    content_col_index: int,
    module_col_index: int,
    strategy: str = "first",
    mode: str = "overwrite",
) -> Tuple[pd.DataFrame, int]:
    """应用规则匹配"""
    if df is None or df.empty:
        return df, 0

    content_idx0 = max(0, content_col_index - 1)
    module_idx0 = max(0, module_col_index - 1)

    max_needed = max(content_idx0, module_idx0)
    if df.shape[1] <= max_needed:
        raise IndexError(f"列数量不足：当前 {df.shape[1]} 列，但需要索引到 {max_needed+1} 列。")

    match_count = 0
    
    def map_text_to_label(text: Any) -> Any:
        nonlocal match_count
        source_text = "" if pd.isna(text) else str(text)
        hits: List[str] = []
        for rule in rules:
            label = str(rule.get("label", "")).strip()
            for kw in rule.get("keywords", []) or []:
                kw_str = str(kw).strip()
                if kw_str and kw_str in source_text:
                    hits.append(label)
                    break
            if strategy == "first" and hits:
                match_count += 1
                return hits[0]
        if strategy == "all":
            unique_hits = list(dict.fromkeys(hits))
            if unique_hits:
                match_count += 1
            return ",".join(unique_hits) if unique_hits else None
        return None

    out = df.copy()
    mapped = out.iloc[:, content_idx0].apply(map_text_to_label)

    if mode == "overwrite":
        out.iloc[:, module_idx0] = mapped.where(~mapped.isna(), out.iloc[:, module_idx0])
    else:
        out.iloc[:, module_idx0] = mapped

    return out, match_count

def llm_fill_unmatched(
    df: pd.DataFrame,
    content_col_index: int,
    module_col_index: int,
    config: Dict[str, Any],
    mode: str = "overwrite",
) -> pd.DataFrame:
    """使用大模型补全未匹配的内容"""
    if df is None or df.empty:
        return df
    
    content_idx0 = max(0, content_col_index - 1)
    module_idx0 = max(0, module_col_index - 1)
    
    out = df.copy()
    total_rows = len(out)
    
    # 找出所有需要大模型补全的行索引
    unmatched_indices = []
    for i in range(total_rows):
        module_value = out.iloc[i, module_idx0]
        content_value = out.iloc[i, content_idx0]
        if (pd.isna(module_value) or str(module_value).strip() == "") and \
           (not pd.isna(content_value) and str(content_value).strip() != ""):
            unmatched_indices.append(i)
    
    # 对未匹配的行进行大模型补全
    if unmatched_indices:
        print(f"开始大模型补全：共 {len(unmatched_indices)} 条需要补全")
        for idx, row_idx in enumerate(unmatched_indices):
            content_value = out.iloc[row_idx, content_idx0]
            print(f"大模型补全进度：{idx+1}/{len(unmatched_indices)} - 处理第 {row_idx+1} 行")
            
            llm_result = call_spark_api(str(content_value), config)
            processed = postprocess_llm_output(llm_result)
            
            if processed:
                if mode == "overwrite":
                    out.iloc[row_idx, module_idx0] = processed
                else:
                    current_value = out.iloc[row_idx, module_idx0]
                    if pd.isna(current_value) or str(current_value).strip() == "":
                        out.iloc[row_idx, module_idx0] = processed
                    else:
                        out.iloc[row_idx, module_idx0] = f"{current_value},{processed}"
    
    return out

def write_csv(df: pd.DataFrame, path: str, sep: str = ",", quote_opt: str = "all") -> None:
    """写入CSV文件"""
    quoting_map = {
        "all": csv.QUOTE_ALL,
        "minimal": csv.QUOTE_MINIMAL,
        "none": csv.QUOTE_NONE
    }
    quoting = quoting_map.get(quote_opt.lower(), csv.QUOTE_ALL)
    escapechar = "\\" if quote_opt.lower() == "none" else None
    
    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
        sep=sep,
        quoting=quoting,
        escapechar=escapechar,
    )

def main() -> None:
    parser = argparse.ArgumentParser(description="CSV 反馈模块标注脚本（规则匹配+大模型补全）")
    parser.add_argument("--input", required=True, help="输入 CSV 路径")
    parser.add_argument("--output", required=True, help="输出 CSV 路径")
    parser.add_argument("--module-col", type=int, default=4, help="写入模块的列（从1开始），默认4")
    parser.add_argument("--content-col", type=int, default=5, help="输入内容所在列（从1开始），默认5")
    parser.add_argument("--strategy", choices=["first", "all"], default="all", 
                       help="匹配策略：first=命中第一条停止；all=合并所有命中")
    parser.add_argument("--mode", choices=["overwrite", "append"], default="append",
                       help="写入模式：overwrite=覆盖原值；append=在原值后追加")
    parser.add_argument("--out-sep", default=",", help="输出分隔符，默认逗号")
    parser.add_argument("--quote", choices=["all", "minimal", "none"], default="all",
                       help="输出引号策略：all=全部加引号（默认）；minimal=按需；none=不加引号")
    parser.add_argument("--config", default="config.json", help="配置文件路径，默认config.json")
    
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"未找到输入文件：{args.input}")

    # 加载配置
    config = load_config(args.config)
    
    print(f"读取输入文件：{args.input}")
    df = read_csv_auto(args.input)
    total_rows = len(df)
    print(f"输入文件共 {total_rows} 行数据")
    
    print("\n第一步：应用规则匹配...")
    rule_matched_df, match_count = apply_rules(
        df=df,
        rules=config.get("rules", []),
        content_col_index=args.content_col,
        module_col_index=args.module_col,
        strategy=args.strategy,
        mode=args.mode,
    )
    
    unmatched_count = total_rows - match_count
    print(f"规则匹配完成：成功匹配 {match_count} 条，剩余 {unmatched_count} 条需要大模型标注")
    
    if unmatched_count > 0:
        print("\n第二步：使用大模型补全未匹配内容...")
        final_df = llm_fill_unmatched(
            df=rule_matched_df,
            content_col_index=args.content_col,
            module_col_index=args.module_col,
            config=config,
            mode=args.mode,
        )
    else:
        print("所有内容已通过规则匹配完成，无需大模型补全")
        final_df = rule_matched_df

    # 创建输出目录
    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    print(f"\n写入输出文件：{args.output}")
    write_csv(final_df, args.output, sep=args.out_sep, quote_opt=args.quote)
    print("处理完成！")

if __name__ == "__main__":
    main()