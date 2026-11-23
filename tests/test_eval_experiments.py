"""Experiment/feedback adapter tests without a live Opik server."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.back.evaluations.opik_adapter import client as adapter


class FakeDataset:
    def __init__(self) -> None:
        self.items = [
            {"id": "item-1", "case_id": "case-1"},
            {"id": "item-2", "case_id": "case-2"},
        ]

    def get_items(self):
        return list(self.items)


class FakeExperiment:
    def __init__(self) -> None:
        self.references = []

    def insert(self, references) -> None:
        self.references.extend(references)


class FakeClient:
    def __init__(self) -> None:
        self.datasets: dict[str, FakeDataset] = {}
        self.scores = []
        self.created = []
        self.experiment = FakeExperiment()

    def get_or_create_dataset(self, name, project_name=None, description=None):
        return self.datasets.setdefault(name, FakeDataset())

    def get_dataset(self, name, project_name=None):
        return self.datasets[name]

    def create_experiment(self, **kwargs):
        self.created.append(kwargs)
        return self.experiment

    def log_traces_feedback_scores(self, scores, project_name=None):
        self.scores.extend(scores)


class ExperimentAdapterTests(unittest.TestCase):
    def test_dataset_items_and_experiment_link(self) -> None:
        client = FakeClient()
        with patch.object(adapter, "_get_client", return_value=client):
            name = adapter.ensure_dataset("ds", [{"case_id": "case-1"}])
            items = adapter.dataset_items(name)
            experiment = adapter.create_experiment(
                name="exp", dataset_name=name, config={"seed": 1}
            )
            linked = adapter.link_experiment_items(
                experiment, [("item-1", "trace-1")]
            )
        self.assertEqual(items, {"case-1": "item-1", "case-2": "item-2"})
        self.assertEqual(linked, 1)
        self.assertEqual(client.created[0]["name"], "exp")
        self.assertEqual(len(experiment.references), 1)

    def test_feedback_scores_are_attached(self) -> None:
        client = FakeClient()
        with patch.object(adapter, "_get_client", return_value=client):
            count = adapter.log_feedback_scores(
                "trace-1",
                [{"name": "llm.task_completion", "value": 1.0}],
            )
        self.assertEqual(count, 1)
        self.assertEqual(client.scores[0]["name"], "llm.task_completion")
        self.assertEqual(client.scores[0]["value"], 1.0)

    def test_missing_client_degrades(self) -> None:
        with patch.object(adapter, "_get_client", return_value=None):
            self.assertEqual(adapter.dataset_items("ds"), {})
            self.assertIsNone(adapter.create_experiment(name="e", dataset_name="d"))
            self.assertEqual(adapter.log_feedback_scores("t", []), 0)


if __name__ == "__main__":
    unittest.main()
