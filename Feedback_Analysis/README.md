# 用户反馈分类与可视化工具

一个开箱即用的 Python 工具集：先用“规则匹配 + 大模型补全”对用户反馈进行分类，再按时间维度输出交互式趋势图，帮助产品与运营快速洞察反馈热点。

## 功能特性

- **规则匹配优先**：基于关键词快速匹配已知分类
- **大模型智能补全**：对未匹配内容调用讯飞星火API进行智能分类
- **灵活配置**：支持自定义分类规则、输出格式和模型参数
- **进度显示**：实时显示处理进度和统计信息

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

编辑 `config.json` 文件，将 `api.spark.api_key` 替换为您的讯飞星火API密钥：

```json
{
  "api": {
    "spark": {
      "api_key": "您的API密钥"
    }
  }
}
```

或者设置环境变量：
```bash
export SPARK_API_KEY="您的API密钥"
```

### 3. 一键示例运行

1) 先对示例数据进行分类：
```bash
python feedback_classifier.py --input tryinput.csv --output tryoutput.csv
```

2) 再基于输出结果绘制交互式趋势图（默认按 24H 分箱）：
```bash
python stats_plot.py --input tryoutput.csv --outdir plots --module-col 4 --time-col 10 --freq 24H
```
完成后在 `plots/` 目录下生成 HTML 图表，双击或自动在浏览器打开即可缩放查看。

## 使用方法

### 基本用法

```bash
python feedback_classifier.py --input input.csv --output output.csv
```

### 高级选项（可按需调整）

```bash
python feedback_classifier.py \
  --input input.csv \
  --output output.csv \
  --content-col 5 \
  --module-col 4 \
  --strategy all \
  --mode append \
  --out-sep , \
  --quote all
```

### 命令行参数说明

- `--input`：输入CSV文件路径（必填）
- `--output`：输出CSV文件路径（必填）
- `--module-col`：写入模块的列（从1开始），默认4
- `--content-col`：输入内容所在列（从1开始），默认5
- `--strategy`：匹配策略：`first`（命中第一条停止）或`all`（合并所有命中），默认`all`
- `--mode`：写入模式：`overwrite`（覆盖原值）或`append`（在原值后追加），默认`append`
- `--out-sep`：输出分隔符，默认逗号
- `--quote`：输出引号策略：`all`、`minimal`或`none`，默认`all`
- `--config`：配置文件路径，默认`config.json`

## 自定义规则

编辑 `config.json` 文件中的 `rules` 部分，添加或修改分类规则：

```json
{
  "rules": [
    {"keywords": ["关键词1", "关键词2"], "label": "分类名称"},
    {"keywords": ["卡顿", "延迟"], "label": "性能问题"}
  ]
}
```

## 配置指南：如何修改 config.json 适配其他 App

本项目通过 `config.json` 控制两类配置：

- `api`：大模型调用相关参数（如 API Key、模型、采样参数、system_prompt）
- `rules`：规则匹配的分类配置（面向产品经理即可上手修改）

### 1) rules 结构说明（面向产品经理）

- `rules` 是一个数组，每一项代表一条分类规则。
- 每条规则包含：
  - `label`：分类名称（将写入输出列，如“学伴”、“VIP”）。
  - `keywords`：关键词数组，任一关键词命中即视为该分类。

示例：

```json
{
  "rules": [
    { "label": "学伴", "keywords": ["成长陪伴", "元气值", "升级石"] },
    { "label": "卡顿", "keywords": ["卡顿", "延迟", "慢"] },
    { "label": "VIP", "keywords": ["充值", "会员", "开通VIP"] }
  ]
}
```

在默认策略 `--strategy all` 下，若一条反馈同时命中多条规则，会将多个 `label` 以英文逗号`,`合并写入，如：`学伴,VIP`。

实操建议：

- 优先使用用户原话/高频词作为 `keywords`，避免过度宽泛词（如“问题”、“不好用”）。
- 同义词请都写上，例如“会员、VIP、充值、开通VIP”。
- 尽量避免在多个分类中写入相同关键词，减少重复命中；如不可避免，请依赖 `--strategy all` 体现多标签。
- 先用小样本验证规则命中率，再逐步补充或收敛关键词。

### 2) 适配其他 App 的思路

1. 列出你们产品希望对外输出的“分类清单”（最终出现在输出列的标签）。
2. 用这些分类作为 `label`，为每个分类整理 5–15 个高频关键词填入 `keywords`。
3. 运行脚本观察命中率；若仍有大量“未匹配”，会自动进入大模型补全。
4. 根据结果迭代关键词，缩减误判、补齐漏判。

### 3) 与 LLM 的配合关系

-- 规则匹配优先：能命中的会直接写入，未命中的才调用大模型。
- 系统提示为内置默认文案，若需更换分类体系，可联系研发修改代码内的系统提示内容，并与 `rules.label` 保持一致。
-- 本工具会自动对大模型输出做“【】内文本提取”，并将包含“使用粗鲁、不礼貌和侮辱性的语言是不恰当的…”的内容统一写为“其他：”。

 

### 4) 常见问题

- 多标签输出如何分隔？
  - 使用英文逗号`,`分隔，例如：`学伴,VIP`。
- 想要单标签优先怎么办？
  - 运行时将参数改为 `--strategy first`，命中第一条规则后即停止。
- 输出列或输入列不在默认位置？
  - 用 `--module-col` 指定输出列（1 起始），用 `--content-col` 指定输入文本列（1 起始）。

## 输出示例

处理完成后，会在指定的输出文件中添加分类结果。例如，原文件第4列（反馈模块）会被填充为相应的分类标签。

### 大模型输出后处理说明

- 仅保留大模型输出中【】内的内容，写入时不包含方括号。
- 若大模型输出包含“使用粗鲁、不礼貌和侮辱性的语言是不恰当的…”，将结果直接写为“其他：”。

## 注意事项

-- 请确保您有有效的讯飞星火API密钥
-- 处理大量数据时，API调用可能需要较长时间
-- 建议先在小批量数据上测试，确认分类效果后再处理大规模数据
-- 配置文件中的规则可以根据实际需求进行扩展

## 可视化统计（Plotly）

使用 `stats_plot.py` 对分类结果按时间进行可视化，输出交互式 HTML 图表。

### 依赖

```bash
pip install plotly
```

### 用法（交互图 HTML 输出）

```bash
python stats_plot.py \
  --input tryoutput.csv \
  --outdir plots \
  --module-col 4 \
  --time-col 10 \
  --freq 24H \
  --start 2025-09-01 \
  --end 2025-09-17
```

参数说明：
- `--module-col`：模块列（从1开始），默认4
- `--time-col`：时间列（从1开始），默认10
- `--freq`：分箱频率，如 `1H`、`2H`、`24H`、`1D`
- `--start`/`--end`：可选的起止时间，用于筛选
- `--no-browser`：只生成文件，不自动打开浏览器

小贴士：
- 若数据时间列不是标准格式，可先在 Excel/脚本中统一格式后再导入。
- 输出文件位于 `plots/range_*.html`，便于多时间范围对比保存。

## 项目结构

```text
.
├── feedback_classifier.py   # 分类主脚本（规则匹配 + 大模型补全）
├── stats_plot.py            # 可视化脚本（Plotly 交互折线图）
├── config.json              # 配置：API 参数、规则、system_prompt
├── requirements.txt         # 依赖清单
├── tryinput.csv             # 示例输入（至少包含内容列与时间列）
├── tryoutput.csv            # 示例输出（运行分类脚本后生成/更新）
├── plots/                   # 图表输出目录（由 stats_plot.py 生成）
└── README.md                # 项目说明
```

## 常见报错与排查

- 未安装依赖：运行 `pip install -r requirements.txt`。
- API Key 无效：确认 `config.json > api.spark.api_key` 或 `SPARK_API_KEY` 是否正确。
- CSV 编码问题：脚本已内置多编码尝试，如仍失败，请手动另存为 UTF-8。
- 列号错误：注意所有列号从 1 开始，确保文件中存在对应列。
- 绘图失败：请先安装 `plotly`，或检查时间列是否为可解析格式。

## 贡献与反馈

- 欢迎提交 Issue/PR 优化规则、改进提示词、扩展可视化形式。
- 若在实际业务中有新的分类体系，建议同步更新 `rules` 与 `system_prompt`，保持两端一致。