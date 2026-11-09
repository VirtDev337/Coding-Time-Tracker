"""
Tests for PDF Report Generation using standard unittest.
"""

import unittest
import os
import tempfile
from timetracker.config import ReportConfig
from timetracker.reports.pdf_report import PDFReportGenerator


class TestPDFReport(unittest.TestCase):
    def test_pdf_report_generation(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_pdf = tmp.name

        try:
            cfg = ReportConfig(
                developer_name="Test Dev",
                hourly_rate=80.0,
                accent_color="#2563EB",
                include_details=True
            )

            mock_data = {
                "start_date": "2026-10-01",
                "end_date": "2026-10-28",
                "total_coding_seconds": 7200,
                "total_research_seconds": 1800,
                "total_seconds": 9000,
                "total_formatted": "2h 30m",
                "coding_formatted": "2h 0m",
                "research_formatted": "30m",
                "projects": [
                    {
                        "name": "TimeTrackerv2",
                        "coding_seconds": 7200,
                        "research_seconds": 1800,
                        "total_seconds": 9000,
                        "coding_formatted": "2h 0m",
                        "research_formatted": "30m",
                        "total_formatted": "2h 30m",
                        "files": [("src/timetracker/cli.py", 12), ("src/timetracker/gui.py", 6)],
                        "research_topics": [("stackoverflow.com", "20m"), ("docs.python.org", "10m")]
                    }
                ],
                "timeline": [
                    {
                        "day": "2026-10-28",
                        "coding_seconds": 7200,
                        "research_seconds": 1800,
                        "total_seconds": 9000
                    }
                ]
            }

            gen = PDFReportGenerator(output_pdf, cfg)
            result_path = gen.generate(mock_data)

            self.assertTrue(os.path.exists(result_path))
            self.assertGreater(os.path.getsize(result_path), 1000)
        finally:
            if os.path.exists(output_pdf):
                os.remove(output_pdf)


if __name__ == "__main__":
    unittest.main()
