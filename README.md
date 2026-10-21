# 招聘数据清洗

## 项目背景与目的

本项目面向招聘岗位 CSV 数据，提供一个简单、可重复运行的第一版清洗流程。它将原始岗位数据整理为正式分析数据和待核查数据，减少完全重复记录，并把符合明确格式的薪资区间转换为数值，方便后续统计。

目前项目只处理本地样例 CSV；没有实现招聘网站采集、全国招聘市场分析或可视化报告。

## 已实现功能

程序位于 `src/clean_jobs.py`，从 `data/raw/jobs_sample.csv` 读取数据，并按以下顺序处理：

1. 检查是否包含 `job_title`、`city`、`salary`、`education`、`company` 五个必需字段；缺少字段时报告字段名并停止。
2. 去除这五个文本字段首尾的空格，并将空字符串作为缺失值处理。
3. 按上述五个字段完全一致去重，保留第一次出现的记录。
4. 仅将 `job_title` 为空的记录放入待核查数据，并添加 `review_reason`。
5. 保留原始 `salary` 文本，并新增 `salary_min`、`salary_max`、`salary_mid` 三个数值字段。
   - 对 `10k-15k` 这类区间按 `k = 1000` 换算，并计算区间中点；不推断薪资周期。
   - “面议”和无法识别的薪资格式保留原文，数值字段留空。未知格式不会导致岗位被移入待核查数据。
6. 输出处理结果和运行摘要，包括记录数、去重数量、“面议”数量及未知薪资格式数量。

正式数据写入 `data/processed/jobs_clean.csv`，待核查数据写入 `data/processed/jobs_review.csv`。输出使用 UTF-8-SIG 编码，便于常见表格软件识别中文。原始 CSV 只读，不会被程序覆盖。

## 目录结构

```text
job_market_research/
├── .gitignore                  # 忽略虚拟环境、缓存、临时测试目录和生成数据
├── README.md                   # 项目说明
├── requirements.txt            # 项目直接依赖及版本约束
├── data/
│   ├── raw/
│   │   └── jobs_sample.csv     # 原始岗位样例数据
│   └── processed/              # 运行后生成正式数据和待核查数据
├── src/
│   └── clean_jobs.py           # 清洗流程与薪资解析逻辑
└── tests/
    └── test_clean_jobs.py      # unittest 自动化测试
```

运行测试时还会临时使用 `tests/.tmp/`；测试结束后临时子目录会自动清理。`.venv/` 是本地 Python 虚拟环境，不属于项目源文件。

## 环境、依赖与运行

项目使用 Python 和 pandas。`requirements.txt` 将直接依赖固定为 `pandas==3.0.6`；清洗程序和测试使用的其他模块（如 `pathlib`、`re`、`tempfile`、`unittest`）属于 Python 标准库，不需要单独安装。pandas 的间接依赖由 pip 根据其包信息自动安装。

以下命令面向 Windows PowerShell，并假设已安装 Python。先在项目根目录创建并启用虚拟环境，再安装依赖：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

激活环境后，运行清洗程序和全部自动化测试：

```powershell
python src\clean_jobs.py
python -m unittest tests.test_clean_jobs -v
```

清洗程序会创建 `data/processed/`（如目录尚不存在），并生成两个结果 CSV。若 PowerShell 不允许激活脚本，也可以直接使用虚拟环境中的 Python 执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src\clean_jobs.py
.\.venv\Scripts\python.exe -m unittest tests.test_clean_jobs -v
```

当前已验证的环境是 Python 3.13.2 和 pandas 3.0.6；在该环境中，清洗程序曾成功运行，8 个自动化测试全部通过。上述“从零创建环境并按 `requirements.txt` 安装”的完整复现过程尚未在全新环境中验证，其他 Python 或 pandas 版本的兼容性也尚未验证。

## 当前运行结果与测试情况

当前样例有 7 条数据记录。最近一次清洗运行成功，摘要为：

- 输入记录：7 条
- 去重删除：1 条
- 正式数据：5 条
- 待核查数据：1 条
- “面议”：1 条
- 未知薪资格式：0 条

最近一次测试执行了 8 个 `unittest` 用例，8 个通过、0 个失败、0 个错误。覆盖内容包括五字段去重、首尾空格清理、职位名称为空时分流、“面议”保留、`10k-15k` 薪资换算、未知薪资格式保留、缺少必需字段时报错，以及只有表头时的空数据处理。

测试主要验证清洗函数和部分处理步骤；没有通过 `main()` 对真实输入到正式输出的完整流程进行自动化集成测试。测试结果反映最近一次实际运行，不代表所有未覆盖场景都已验证。

## 当前局限与未来扩展

当前版本只读取固定路径和单个 CSV 文件；职位名称为空是唯一进入待核查文件的条件。薪资解析只支持数字加 `k`/`K`、连字符和另一数字加 `k`/`K` 的区间格式；其他格式仅保留原文并计入运行摘要。程序不判断区间上下限是否合理，也不推断薪资周期。

未来可在确认业务口径后考虑：支持命令行输入输出路径、增加更多薪资格式和格式校验、扩展待核查原因、为完整读写流程增加隔离的集成测试，以及补充更多样例数据。这些是可选方向，尚未实现。
