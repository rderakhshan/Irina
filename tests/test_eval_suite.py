"""End-to-end offline suite and reporting tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.back.evaluations.datasets import build_core_datasets, flatten_datasets
from src.back.evaluations.governance import summary as coverage_summary
from src.back.evaluations.reporting import summarise_metrics, write_report
from src.back.evaluations.runners import run_core_suite
from src.back.evaluations.worlds import WorldFactory


class CoreSuiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.world = WorldFactory().build(seed=11)
        self.grouped = build_core_datasets(self.world)
        self.cases = flatten_datasets(self.grouped)
        self.result = run_core_suite(self.world, self.cases)

    def test_all_core_families_present(self) -> None:
        self.assertEqual(
            set(self.grouped),
            {
                "DS01",
                "DS02",
                "DS03",
                "DS04",
                "DS05",
                "DS06",
                "DS07",
                "DS08",
                "DS10",
                "DS11",
                "DS12",
                "DS14",
            },
        )

    def test_every_case_has_metrics(self) -> None:
        self.assertGreater(len(self.result.outcomes), 10)
        for outcome in self.result.outcomes:
            self.assertTrue(outcome.metrics, outcome.case_id)

    def test_reference_suite_passes_deterministic_cases(self) -> None:
        failures = [outcome for outcome in self.result.outcomes if outcome.passed is False]
        self.assertEqual(failures, [], [f.case_id for f in failures])
        self.assertEqual(self.result.integration_level, "L1_simulated_workflow")

    def test_retrieval_metrics_are_defined(self) -> None:
        summaries = {item.metric_id: item for item in summarise_metrics(self.result.outcomes)}
        recall = summaries["tools.retrieval_recall_at_k"]
        self.assertTrue(recall.defined)
        self.assertGreater(recall.value, 0)

    def test_report_files_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            json_path, md_path = write_report(
                self.result,
                world_manifest=self.world.manifest,
                output_dir=directory,
            )
            payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
            self.assertEqual(payload["world_id"], self.world.world_id)
            self.assertIn("Governance Evaluation Report", Path(md_path).read_text(encoding="utf-8"))

    def test_coverage_maps_all_concerns(self) -> None:
        self.assertEqual(coverage_summary()["unmapped_concerns"], [])


if __name__ == "__main__":
    unittest.main()
