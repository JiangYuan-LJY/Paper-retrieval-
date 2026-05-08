# GET-Paper 论文检索与评分工具

GET-Paper 是一个用于自动检索、补全、评分和导出论文信息的 Python 命令行工具。用户只需要配置检索主题、关键词、年份、返回数量和评分规则，程序会从 Scopus 检索论文，补全论文元数据，调用 EasyScholar 获取期刊分区信息，并根据配置对论文进行评分排序，最后生成 Markdown 和 JSON 结果文件。

本项目不会自动下载 PDF。

## 主要功能

- 根据关键词和年份从 Scopus 检索论文。
- 支持通过配置选择关键词之间使用 `AND` 或 `OR` 连接。
- 提取论文标题、作者、年份、期刊、摘要、DOI、链接、Author Keywords 等信息。
- 当 Scopus 搜索结果中缺少摘要或 Author Keywords 时，尝试通过 DOI 调用 Scopus Abstract Retrieval 接口补全。
- 调用 EasyScholar 获取期刊分区或排名信息。
- 根据期刊质量、主题相关性、关键词匹配度对论文评分。
- 按总分降序排序论文。
- 在 `results/` 目录下同时生成 Markdown 和 JSON 文件。

## 快速启动流程

新用户可以按以下顺序使用本项目：

1. **获取项目代码**

   ```bash
   git clone <项目地址>
   cd GET-Paper
   ```

2. **创建 Python 虚拟环境**

   ```bash
   python -m venv .venv
   ```

3. **安装依赖**

   ```bash
   ./.venv/Scripts/python.exe -m pip install -r requirements.txt
   ```

4. **创建本地环境变量文件**

   ```bash
   cp .env.example .env
   ```

   然后打开 `.env`，填写自己的 Scopus、EasyScholar 和可选的大模型中转站 API 信息。

5. **配置检索与评分参数**

   打开 `Get_Paper.yaml`，根据自己的研究需求修改：

   - `topic`：研究主题。
   - `keywords`：Scopus 检索关键词。
   - `keyword_operator`：关键词连接方式，填写 `AND` 或 `OR`。
   - `max_results`：最大返回论文数量。
   - `year`：检索年份。
   - `scoring_prompt`、`score_weights`、`journal_quality`：评分规则。

6. **运行程序**

   ```bash
   ./.venv/Scripts/python.exe src/main.py
   ```

7. **查看结果**

   运行完成后，在 `results/` 目录查看生成的：

   - Markdown 文件：适合人工阅读和筛选。
   - JSON 文件：适合后续结构化处理。

如果已经激活虚拟环境，也可以使用 `python src/main.py` 运行程序。

## 项目文件说明

常用文件如下：

- `src/main.py`：程序入口。
- `src/config.py`：读取 `.env` 中的 API key 和模型温度等环境变量。
- `src/retrieval_config.py`：读取并校验 `Get_Paper.yaml` 用户配置文件。
- `src/scopus_client.py`：负责 Scopus 检索和论文元数据解析。
- `src/easyscholar_client.py`：负责 EasyScholar 期刊分区查询。
- `src/paper_scoring.py`：负责论文评分和排序。
- `src/markdown_writer.py`：负责生成 Markdown 和 JSON 结果文件。
- `Get_Paper.yaml`：用户检索与评分配置文件，支持注释。
- `.env`：本地私有 API key 文件，不应提交或分享。
- `.env.example`：环境变量示例文件，可分享给其他用户。
- `workflow.md`：项目运行流程说明。

## 安装依赖

建议先创建虚拟环境：

```bash
python -m venv .venv
```

安装依赖：

```bash
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

如果已经激活虚拟环境，也可以使用：

```bash
pip install -r requirements.txt
```

## 配置 API Key

项目根目录下需要创建 `.env` 文件，用于保存本地私有 API key。

`.env` 不应上传到 GitHub，也不应分享给其他人。

必填配置：

```env
SCOPUS_API_KEY=your_scopus_api_key
EASYSCHOLAR_SECRET_KEY=your_easyscholar_secret_key
```

如果需要使用大模型评分，还需要配置：

```env
PAPER_SCORING_API_URL=https://aixor.org
PAPER_SCORING_API_KEY=your_model_relay_key
PAPER_SCORING_MODEL=your_model_name
PAPER_SCORING_TEMPERATURE=0
```

说明：

- `SCOPUS_API_KEY`：Scopus API key。
- `EASYSCHOLAR_SECRET_KEY`：EasyScholar API key。
- `PAPER_SCORING_API_URL`：大模型中转站地址。
- `PAPER_SCORING_API_KEY`：大模型中转站 key。
- `PAPER_SCORING_MODEL`：使用的模型名称。
- `PAPER_SCORING_TEMPERATURE`：模型输出随机性，建议评分任务使用 `0`。

如果不配置大模型相关变量，程序仍然可以运行，但 `Topic Relevance` 和 `Keyword Match` 会显示为 `Not scored`。

## 配置用户检索文件 Get_Paper.yaml

用户主要修改项目根目录下的 `Get_Paper.yaml`。YAML 格式支持使用 `#` 写注释，方便直接在配置文件中说明每个字段的用途。

示例：

```yaml
# 研究主题，用于大模型判断论文摘要与研究方向的相关性
# 注意：topic 不直接参与 Scopus 检索
topic: "Stability analysis"

# Scopus 检索关键词，也用于关键词匹配度评分
keywords:
  - "modular multilevel converter"
  - "Oscillation suppression"

# 关键词连接方式：AND 更严格，OR 更宽泛
keyword_operator: "OR"

# Scopus 最大返回数量
max_results: 20

# 检索年份
year: 2026

# 大模型评分提示词模板
scoring_prompt: "Score this academic paper against the user's research need. Return only JSON with keys topic_relevance_score and keyword_match_score. topic_relevance_score must be a number from 0 to {topic_relevance_max_score}; compare Topic with Abstract. keyword_match_score must be a number from 0 to {keyword_match_max_score}; compare User keywords with Author Keywords. Use null only when the needed paper field is Not available."

# 三项评分权重
score_weights:
  journal_quality: 45
  topic_relevance: 35
  keyword_match: 20

# 期刊质量评分规则
journal_quality:
  q1_or_engineering_1: 45
  q2_or_engineering_2: 40
  q3_or_engineering_3: 30
  other_known_rank: 25
```

### 字段说明

#### topic

论文检索主题，用于大模型评分中的主题相关性判断。

注意：`topic` 不直接参与 Scopus 检索，它用于将论文摘要与用户研究主题进行比较评分。

示例：

```yaml
topic: "Stability analysis"
```

#### keywords

Scopus 检索关键词，同时也用于大模型评分中的关键词匹配度判断。

建议使用英文关键词，因为 Scopus 检索对英文关键词支持更好。

示例：

```yaml
keywords:
  - "modular multilevel converter"
  - "Oscillation suppression"
```

#### keyword_operator

控制多个关键词之间的 Scopus 检索逻辑。

可选值：

- `AND`：要求多个关键词同时匹配，检索更严格，结果更少但更精准。
- `OR`：任意一个关键词匹配即可，检索更宽泛，结果更多。

示例：

```yaml
keyword_operator: "OR"
```

程序生成的查询类似：

```text
TITLE-ABS-KEY("modular multilevel converter" OR "Oscillation suppression") AND PUBYEAR = 2026
```

年份过滤始终使用 `AND PUBYEAR = ...`，不受 `keyword_operator` 影响。

#### max_results

Scopus 最大返回论文数量。

示例：

```yaml
max_results: 20
```

#### year

检索年份。

示例：

```yaml
year: 2026
```

#### scoring_prompt

传给大模型的评分提示词模板。

模板中可以使用以下占位符：

- `{topic_relevance_max_score}`：主题相关性最高分。
- `{keyword_match_max_score}`：关键词匹配度最高分。
- `{journal_quality_max_score}`：期刊质量最高分。

程序会在提示词后自动追加当前论文的主题、用户关键词、摘要和 Author Keywords。

#### score_weights

三类评分的最高分设置。

默认总分为 100：

```yaml
score_weights:
  journal_quality: 45
  topic_relevance: 35
  keyword_match: 20
```

含义：

- `journal_quality`：期刊质量分。
- `topic_relevance`：主题相关性分。
- `keyword_match`：关键词匹配度分。

#### journal_quality

期刊质量评分规则。

默认配置：

```yaml
journal_quality:
  q1_or_engineering_1: 45
  q2_or_engineering_2: 40
  q3_or_engineering_3: 30
  other_known_rank: 25
```

含义：

- `q1_or_engineering_1`：Q1 或工程技术 1 区。
- `q2_or_engineering_2`：Q2 或工程技术 2 区。
- `q3_or_engineering_3`：Q3 或工程技术 3 区。
- `other_known_rank`：有排名信息但不属于以上情况。

如果一篇论文同时匹配多个规则，程序会取最高分。

## 运行程序

在项目根目录运行：

```bash
./.venv/Scripts/python.exe src/main.py
```

如果已经激活虚拟环境：

```bash
python src/main.py
```

运行后程序会：

1. 读取 `.env`。
2. 读取 `Get_Paper.yaml`。
3. 使用关键词和年份检索 Scopus。
4. 补全论文摘要和 Author Keywords。
5. 查询 EasyScholar 期刊分区。
6. 对论文进行评分。
7. 按总分降序排序。
8. 在 `results/` 目录生成结果文件。

## 输出结果

程序会在 `results/` 目录生成两个文件：

```text
papers_YYYYMMDD_HHMM.md
papers_YYYYMMDD_HHMM.json
```

Markdown 文件适合人工阅读，包含：

1. 论文标题。
2. 总分及各单项评分。
3. Journal 和 Journal Rank。
4. 作者、DOI、年份。
5. 摘要。
6. Author Keywords。
7. Scopus Link。
8. Paper Link。

JSON 文件保留结构化数据，方便后续调试、筛选或二次处理。

## 评分逻辑

每篇论文最多包含三项评分：

1. `Journal Quality`
2. `Topic Relevance`
3. `Keyword Match`

### Journal Quality

该分数由 EasyScholar 返回的期刊分区或排名信息决定。

默认规则：

- Q1 或工程技术 1 区：45 分。
- Q2 或工程技术 2 区：40 分。
- Q3 或工程技术 3 区：30 分。
- 其他有排名信息的期刊：25 分。
- 没有期刊排名信息：`Not scored`。

### Topic Relevance

该分数由大模型判断。

程序会比较：

- `Get_Paper.yaml` 中的 `topic`
- 论文摘要 `Abstract`

如果大模型未配置、请求失败或摘要不可用，该项显示为 `Not scored`。

### Keyword Match

该分数由大模型判断。

程序会比较：

- `Get_Paper.yaml` 中的 `keywords`
- 论文的 `Author Keywords`

如果大模型未配置、请求失败或 Author Keywords 不可用，该项显示为 `Not scored`。

### Total

`Total` 是已有评分项的总和。

示例：

- `Journal Quality = 45`，其他两项为 `Not scored`，则 `Total = 45`。
- `Journal Quality = 45`，`Topic Relevance = 30`，`Keyword Match = Not scored`，则 `Total = 75`。
- 如果三项都没有得分，则 `Total = Not scored`。

论文最终按 `Total` 降序排列；没有总分的论文按 0 参与排序。

## 工作流程

本项目的工作流程如下：

1. **加载配置**
   - 从 `.env` 读取 API key 和模型参数。
   - 从 `Get_Paper.yaml` 读取检索参数和评分规则。

2. **校验配置**
   - 检查必填 API key 是否存在。
   - 检查 `Get_Paper.yaml` 是否存在必填字段。
   - 检查 `keyword_operator` 是否为 `AND` 或 `OR`。

3. **构造 Scopus 查询**
   - 使用 `keywords` 和 `keyword_operator` 构造 `TITLE-ABS-KEY(...)`。
   - 使用 `year` 添加年份限制。

4. **检索论文信息**
   - 调用 Scopus Search API。
   - 解析标题、作者、年份、来源、摘要、DOI、链接等元数据。

5. **补全论文元数据**
   - 当摘要或 Author Keywords 缺失且 DOI 可用时，调用 Scopus Abstract Retrieval API 尝试补全。
   - 如果补全失败，程序不会中断，对应字段记为 `Not available`。

6. **获取期刊分区**
   - 调用 EasyScholar 获取 Journal Rank。
   - 如果查询失败，Journal Rank 记为 `Not available`。

7. **论文评分**
   - 根据 Journal Rank 计算 `Journal Quality`。
   - 使用大模型计算 `Topic Relevance` 和 `Keyword Match`。
   - 如果大模型不可用，模型评分项记为 `Not scored`。

8. **排序与导出**
   - 计算 `Total`。
   - 按总分降序排列论文。
   - 输出 Markdown 和 JSON 文件。

## 常见问题

### 是否会自动下载 PDF？

不会。本项目只检索和整理论文元数据，不自动下载 PDF。

### 是否必须配置大模型？

不是。没有配置大模型时，程序仍然可以完成 Scopus 检索、EasyScholar 分区查询、Journal Quality 评分和结果导出。

### 为什么 Topic Relevance 或 Keyword Match 是 Not scored？

常见原因包括：

- 没有配置大模型相关环境变量。
- 大模型中转站请求失败。
- 论文摘要或 Author Keywords 缺失。
- 模型返回内容不是合法 JSON。

### 如何避免泄露 API key？

- 真实 key 只写入 `.env`。
- 不要提交 `.env`。
- 使用 `.env.example` 提供示例配置。
- 提交前运行 `git status --short`，确认没有 `.env`。

## 给其他用户的使用步骤

如果你要把项目分享给其他人，可以让对方按以下步骤使用：

```bash
git clone <项目地址>
cd GET-Paper
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env
```

然后让对方：

1. 在 `.env` 中填写自己的 API key。
2. 在 `Get_Paper.yaml` 中配置检索主题、关键词、年份和评分规则。
3. 运行：

```bash
./.venv/Scripts/python.exe src/main.py
```
