"""清洗招聘岗位 CSV，并生成正式数据和待核查数据。"""

from pathlib import Path
import re

import pandas as pd


# 从当前脚本位置推导项目根目录，避免依赖运行命令时所在的目录。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "jobs_sample.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
CLEAN_PATH = OUTPUT_DIR / "jobs_clean.csv"
REVIEW_PATH = OUTPUT_DIR / "jobs_review.csv"

REQUIRED_COLUMNS = ["job_title", "city", "salary", "education", "company"]
SALARY_COLUMNS = ["salary_min", "salary_max", "salary_mid"]
REVIEW_REASON_COLUMN = "review_reason"

# 只接受明确的“数字k-数字k”区间写法；大小写 k/K 均可，允许区间两侧有空格。
SALARY_RANGE_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*[kK]\s*-\s*(\d+(?:\.\d+)?)\s*[kK]\s*$"
)


def validate_columns(data: pd.DataFrame) -> None:
    """确认输入包含全部必需字段，否则给出可读错误。"""
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"输入 CSV 缺少必需字段：{missing_text}")


def clean_text_fields(data: pd.DataFrame) -> pd.DataFrame:
    """清理五个原始文本字段的首尾空格，并统一空字段表示。"""
    cleaned = data.copy()
    for column in REQUIRED_COLUMNS:
        # pandas 会把 CSV 空单元格读成缺失值；其余值转成文本后再去除首尾空格。
        cleaned[column] = cleaned[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        cleaned[column] = cleaned[column].replace("", pd.NA)
    return cleaned


def parse_salary(value: object) -> tuple[object, object, object]:
    """解析已知薪资区间；面议、空值及未知格式的数值字段均留空。"""
    if pd.isna(value):
        return pd.NA, pd.NA, pd.NA

    match = SALARY_RANGE_PATTERN.fullmatch(str(value))
    if not match:
        return pd.NA, pd.NA, pd.NA

    minimum = float(match.group(1)) * 1000
    maximum = float(match.group(2)) * 1000
    midpoint = (minimum + maximum) / 2
    return minimum, maximum, midpoint


def add_salary_columns(data: pd.DataFrame) -> pd.DataFrame:
    """保留原始 salary，并增加三个数值薪资字段。"""
    result = data.copy()
    parsed = result["salary"].map(parse_salary)
    result[SALARY_COLUMNS] = pd.DataFrame(
        parsed.tolist(), index=result.index, columns=SALARY_COLUMNS
    )
    return result


def main() -> None:
    """按约定顺序清洗数据、写出文件并打印运行摘要。"""
    # 1. 读取并校验字段。
    data = pd.read_csv(INPUT_PATH, dtype=str, keep_default_na=False)
    validate_columns(data)

    # 2. 清理文本首尾空格；空字符串也统一作为缺失值处理。
    data = clean_text_fields(data)

    # 3. 按五个原始字段完全一致去重，保留首次出现的记录。
    input_count = len(data)
    data = data.drop_duplicates(subset=REQUIRED_COLUMNS, keep="first").copy()
    duplicate_count = input_count - len(data)

    # 4. 仅职位名称为空的记录进入待核查数据。
    missing_title = data["job_title"].isna()
    review_base = data.loc[missing_title].copy()
    clean_base = data.loc[~missing_title].copy()
    review_base[REVIEW_REASON_COLUMN] = "job_title 为空"

    # 5. 分流后解析薪资；salary 原字段保持清理首尾空格后的文本。
    clean_data = add_salary_columns(clean_base)
    review_data = add_salary_columns(review_base)

    # “面议”是已知的非数值薪资；其他未匹配格式单独统计，但不移入待核查数据。
    is_negotiable = clean_base["salary"].eq("面议")
    has_salary_text = clean_base["salary"].notna() & clean_base["salary"].ne("")
    unknown_salary = has_salary_text & ~is_negotiable & clean_data["salary_min"].isna()
    negotiable_count = int(is_negotiable.sum())
    unknown_salary_count = int(unknown_salary.sum())

    # 6. 输出；即使没有数据行，DataFrame 仍会保留字段表头。
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clean_columns = REQUIRED_COLUMNS + SALARY_COLUMNS
    review_columns = REQUIRED_COLUMNS + SALARY_COLUMNS + [REVIEW_REASON_COLUMN]
    clean_data[clean_columns].to_csv(CLEAN_PATH, index=False, encoding="utf-8-sig")
    review_data[review_columns].to_csv(REVIEW_PATH, index=False, encoding="utf-8-sig")

    print("招聘数据清洗完成")
    print(f"输入记录数：{input_count}")
    print(f"去重删除数：{duplicate_count}")
    print(f"正式数据数：{len(clean_data)}")
    print(f"待核查数据数（职位名称为空）：{len(review_data)}")
    print(f"面议记录数（已知非数值薪资）：{negotiable_count}")
    print(f"未知薪资格式记录数：{unknown_salary_count}")
    print(f"正式数据文件：{CLEAN_PATH}")
    print(f"待核查数据文件：{REVIEW_PATH}")


if __name__ == "__main__":
    main()
