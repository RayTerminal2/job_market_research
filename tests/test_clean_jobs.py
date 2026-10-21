"""招聘数据清洗逻辑的第一版单元测试。"""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src import clean_jobs


class CleanJobsTests(unittest.TestCase):
    """测试清洗模块中的字段校验、标准化和薪资处理函数。"""

    def make_row(self, **overrides):
        """创建一条最小的岗位测试记录，可按需覆盖字段值。"""
        row = {
            "job_title": "数据分析师",
            "city": "北京",
            "salary": "10k-15k",
            "education": "本科",
            "company": "甲公司",
        }
        row.update(overrides)
        return row

    def test_identical_five_field_records_are_deduplicated(self):
        """五个原始字段完全相同的记录只保留一条。"""
        data = pd.DataFrame([self.make_row(), self.make_row()])

        cleaned = clean_jobs.clean_text_fields(data)
        deduplicated = cleaned.drop_duplicates(
            subset=clean_jobs.REQUIRED_COLUMNS, keep="first"
        )

        self.assertEqual(len(deduplicated), 1)

    def test_text_fields_are_stripped_before_deduplication(self):
        """五个字段的首尾空格会清理，清理后相同的行可去重。"""
        first = self.make_row()
        second = {
            key: f"  {value}  " for key, value in first.items()
        }
        data = pd.DataFrame([first, second])

        cleaned = clean_jobs.clean_text_fields(data)
        deduplicated = cleaned.drop_duplicates(
            subset=clean_jobs.REQUIRED_COLUMNS, keep="first"
        )

        self.assertEqual(len(deduplicated), 1)
        for column in clean_jobs.REQUIRED_COLUMNS:
            self.assertEqual(cleaned.iloc[1][column], first[column])

    def test_empty_job_title_is_separated_for_review(self):
        """职位名称为空的记录进入待核查部分，其余记录保留在正式部分。"""
        data = pd.DataFrame(
            [self.make_row(job_title="   "), self.make_row(company="乙公司")]
        )
        cleaned = clean_jobs.clean_text_fields(data)
        missing_title = cleaned["job_title"].isna()
        review = cleaned.loc[missing_title].copy()
        formal = cleaned.loc[~missing_title].copy()
        review[clean_jobs.REVIEW_REASON_COLUMN] = "job_title 为空"

        self.assertEqual(len(review), 1)
        self.assertTrue(pd.isna(review.iloc[0]["job_title"]))
        self.assertEqual(review.iloc[0]["review_reason"], "job_title 为空")
        self.assertEqual(len(formal), 1)
        self.assertTrue(formal["job_title"].notna().all())

    def test_negotiable_salary_is_preserved_with_empty_numeric_values(self):
        """“面议”保留原文，三个数值薪资字段均为空。"""
        data = pd.DataFrame([self.make_row(salary="面议")])

        result = clean_jobs.add_salary_columns(data)

        self.assertEqual(result.iloc[0]["salary"], "面议")
        for column in clean_jobs.SALARY_COLUMNS:
            self.assertTrue(pd.isna(result.iloc[0][column]))

    def test_salary_range_is_converted_to_thousands_and_midpoint(self):
        """10k-15k 按千元换算，并正确计算区间中点。"""
        result = clean_jobs.parse_salary("10k-15k")

        self.assertEqual(result, (10000.0, 15000.0, 12500.0))

    def test_unknown_salary_format_keeps_record_and_has_no_numeric_values(self):
        """未知薪资格式不会使岗位记录丢失，解析数值保持为空。"""
        data = pd.DataFrame([self.make_row(salary="薪资面议或另议")])

        result = clean_jobs.add_salary_columns(data)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["salary"], "薪资面议或另议")
        for column in clean_jobs.SALARY_COLUMNS:
            self.assertTrue(pd.isna(result.iloc[0][column]))

    def test_missing_required_column_has_clear_error(self):
        """缺少必需字段时抛出 ValueError，并指出缺少的字段名称。"""
        data = pd.DataFrame(columns=[
            "job_title", "city", "salary", "education"
        ])

        with self.assertRaisesRegex(ValueError, "company"):
            clean_jobs.validate_columns(data)

    def test_header_only_csv_produces_empty_results_with_expected_columns(self):
        """只有表头的 CSV 可读取为空数据，并保留输出所需字段结构。"""
        header = ",".join(clean_jobs.REQUIRED_COLUMNS) + "\n"
        temporary_parent = Path(__file__).resolve().parent / ".tmp"
        temporary_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_parent) as temporary_directory:
            csv_path = Path(temporary_directory) / "header_only.csv"
            csv_path.write_text(header, encoding="utf-8")
            data = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

        clean_jobs.validate_columns(data)
        cleaned = clean_jobs.clean_text_fields(data)
        formal = cleaned.loc[cleaned["job_title"].notna()].copy()
        review = cleaned.loc[cleaned["job_title"].isna()].copy()
        formal = clean_jobs.add_salary_columns(formal)
        review = clean_jobs.add_salary_columns(review)
        review[clean_jobs.REVIEW_REASON_COLUMN] = pd.Series(dtype="object")

        self.assertEqual(len(formal), 0)
        self.assertEqual(len(review), 0)
        self.assertEqual(
            list(formal.columns), clean_jobs.REQUIRED_COLUMNS + clean_jobs.SALARY_COLUMNS
        )
        self.assertEqual(
            list(review.columns),
            clean_jobs.REQUIRED_COLUMNS
            + clean_jobs.SALARY_COLUMNS
            + [clean_jobs.REVIEW_REASON_COLUMN],
        )


if __name__ == "__main__":
    unittest.main()
