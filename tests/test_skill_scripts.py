import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "sas-fas-analyst"
INIT = SKILL_ROOT / "scripts" / "init_run.py"
CALCULATE = SKILL_ROOT / "scripts" / "calculate_metrics.py"
VALIDATE = SKILL_ROOT / "scripts" / "validate_run.py"


def load_calculator():
    spec = importlib.util.spec_from_file_location("sas_calculate_metrics", CALCULATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CALC = load_calculator()


class SkillScriptsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def command(self, *args):
        return subprocess.run(
            [sys.executable, *map(str, args)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def new_run(self, asset_type="equity"):
        result = self.command(
            INIT,
            "--asset",
            "TEST",
            "--asset-type",
            asset_type,
            "--runs-root",
            self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return Path(result.stdout.strip())

    def read_json(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def make_evidence_ready(self, run):
        manifest = self.read_json(run / "00_manifest.json")
        manifest.update(
            status="evidence_ready",
            as_of="2026-07-18T00:00:00+00:00",
            data_completeness_score=80,
        )
        self.write_json(run / "00_manifest.json", manifest)
        ledger = {
            "critical_fields": ["price"],
            "metrics": {"price": 10, "company_class": "non_manufacturing"},
            "metric_evidence": {"price": ["EV-001"]},
            "evidence": [
                {
                    "id": "EV-001",
                    "claim": "Test price was observed at the research cutoff.",
                    "as_of": "2026-07-18T00:00:00Z",
                    "source_url": "user-artifact:test-fixture",
                    "source_tier": 3,
                    "confidence": "high",
                }
            ],
            "conflicts": [],
        }
        self.write_json(run / "01_evidence.json", ledger)

    def write_valid_final(self, run):
        self.make_evidence_ready(run)
        manifest = self.read_json(run / "00_manifest.json")
        manifest["status"] = "complete"
        self.write_json(run / "00_manifest.json", manifest)
        result = self.command(CALCULATE, run)
        self.assertEqual(result.returncode, 0, result.stderr)
        judge = {
            "schema_version": "5.0",
            "asset_type": "equity",
            "evidence_grade": "B",
            "fundamental_state": "stable",
            "odds_state": "favorable",
            "verdict_possible": True,
            "action_mode": "research_only",
            "scenario_probabilities_pct": {"bear": 25, "base": 50, "bull": 25},
            "evidence_ids": ["EV-001"],
            "unresolved_evidence": [],
        }
        self.write_json(run / "06_judge.json", judge)
        prose = (
            "# Analysis\n\n[F][EV-001] Verified fixture fact. "
            "This paragraph is intentionally long enough to prove the validator rejects placeholder files "
            "while accepting substantive evidence-linked analysis with a falsifiable conclusion.\n"
        )
        for name in ("03_bull.md", "04_bear.md", "05_market_structure.md", "06_judge.md"):
            (run / name).write_text(prose, encoding="utf-8")
        final = """# TEST — SAS-FAS v5 深度研究

## 一句话裁决
[I] Test conclusion based on EV-001.
## 四维评级
Evidence B; stable; favorable; research only.
## 已确认的底层事实
- [F][EV-001] Verified fixture fact.
## 核心推断与未知
- [I] Inference.\n- [H] Falsifiable hypothesis.\n- [U] Decision-relevant unknown.
## Bull：最强成立路径
[F][EV-001] Evidence-linked upside path.
## Bear：永久损失路径
[F][EV-001] Evidence-linked impairment path.
## 估值与概率
Bear 25%; base 50%; bull 25%.
## 基准率与市场结构
[F][EV-001] Reference-class and structure note.
## 事前验尸
Trigger → transmission → damage → impairment.
## 行动与仓位（仅在请求且资料完整时）
Research only; no personalized action.
## 什么会改变结论
Three future observations would change it.
## 数据盲区与冲突
[U] Fixture limitation.
## 来源
EV-001 — user-artifact:test-fixture
"""
        (run / "07_FINAL_REPORT.md").write_text(final, encoding="utf-8")

    def test_empty_scaffold_cannot_pass_evidence_gate(self):
        run = self.new_run()
        result = self.command(VALIDATE, run, "--stage", "evidence")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("critical_fields must be a non-empty list", result.stdout)
        self.assertIn("requires at least one evidence item", result.stdout)

    def test_valid_evidence_and_final_contract_pass(self):
        run = self.new_run()
        self.write_valid_final(run)
        evidence = self.command(VALIDATE, run, "--stage", "evidence")
        final = self.command(VALIDATE, run, "--stage", "final")
        self.assertEqual(evidence.returncode, 0, evidence.stdout)
        self.assertEqual(final.returncode, 0, final.stdout)

    def test_blocked_run_with_substantive_blocker_passes_stop_gate(self):
        run = self.new_run()
        manifest = self.read_json(run / "00_manifest.json")
        manifest["status"] = "blocked"
        self.write_json(run / "00_manifest.json", manifest)
        ledger = self.read_json(run / "01_evidence.json")
        ledger["critical_fields"] = ["price"]
        self.write_json(run / "01_evidence.json", ledger)
        (run / "BLOCKER.md").write_text(
            "# Blocker\nMissing verified price after exhausting allowed public sources. "
            "It can change valuation and position sizing. Resume after the user provides "
            "a dated primary artifact or authorizes a named data source.",
            encoding="utf-8",
        )
        result = self.command(VALIDATE, run, "--stage", "evidence")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_placeholder_final_artifacts_are_rejected(self):
        run = self.new_run()
        self.make_evidence_ready(run)
        manifest = self.read_json(run / "00_manifest.json")
        manifest["status"] = "complete"
        self.write_json(run / "00_manifest.json", manifest)
        self.write_json(run / "02_quant.json", {})
        self.write_json(run / "06_judge.json", {})
        for name in ("03_bull.md", "04_bear.md", "05_market_structure.md", "06_judge.md", "07_FINAL_REPORT.md"):
            (run / name).write_text("x", encoding="utf-8")
        result = self.command(VALIDATE, run, "--stage", "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("calculated must be a non-empty object", result.stdout)
        self.assertIn("too short", result.stdout)

    def test_unexplained_null_is_rejected(self):
        run = self.new_run()
        self.write_valid_final(run)
        quant = self.read_json(run / "02_quant.json")
        quant["calculated"]["unexplained_test_metric"] = None
        self.write_json(run / "02_quant.json", quant)
        result = self.command(VALIDATE, run, "--stage", "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexplained_test_metric", result.stdout)

    def test_personalized_action_requires_profile_gate(self):
        run = self.new_run()
        self.write_valid_final(run)
        judge = self.read_json(run / "06_judge.json")
        judge["action_mode"] = "personalized"
        self.write_json(run / "06_judge.json", judge)
        result = self.command(VALIDATE, run, "--stage", "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("complete investor profile", result.stdout)

    def test_invalid_cutoff_and_probabilities_are_rejected(self):
        run = self.new_run()
        self.write_valid_final(run)
        manifest = self.read_json(run / "00_manifest.json")
        manifest["as_of"] = "not-a-date"
        self.write_json(run / "00_manifest.json", manifest)
        judge = self.read_json(run / "06_judge.json")
        judge["scenario_probabilities_pct"] = {"bear": 25, "base": 50, "bull": 50}
        self.write_json(run / "06_judge.json", judge)
        result = self.command(VALIDATE, run, "--stage", "final")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ISO-8601", result.stdout)
        self.assertIn("sum to 100", result.stdout)

    def test_critical_metric_requires_finite_value_and_known_evidence(self):
        run = self.new_run()
        self.make_evidence_ready(run)
        ledger = self.read_json(run / "01_evidence.json")
        ledger["metrics"]["price"] = "10"
        ledger["metric_evidence"]["price"] = ["EV-999"]
        self.write_json(run / "01_evidence.json", ledger)
        result = self.command(VALIDATE, run, "--stage", "evidence")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("finite JSON number", result.stdout)
        self.assertIn("unknown evidence IDs", result.stdout)

    def test_bank_percentage_units_are_unambiguous(self):
        cases = (
            ({"cet1_ratio_pct": 1.2, "binding_cet1_requirement_pct": 4.5}, -330),
            ({"cet1_ratio": 0.141, "binding_cet1_requirement": 0.105}, 360),
            ({"cet1_ratio": 14.1, "binding_cet1_requirement": 10.5}, 360),
        )
        for fields, expected in cases:
            calculated, _ = CALC.equity_metrics({"company_class": "bank", **fields})
            actual = calculated["bank_route"]["cet1_buffer_over_binding_requirement_bps"]
            self.assertAlmostEqual(actual, expected)

    def test_beneish_tata_uses_continuing_operations_income(self):
        metrics = {
            "company_class": "non_manufacturing",
            "net_income": 999,
            "income_from_continuing_operations": 100,
            "cash_from_operations": 80,
            "total_assets_current": 200,
        }
        calculated, _ = CALC.equity_metrics(metrics)
        self.assertAlmostEqual(calculated["beneish_components"]["tata"], 0.1)
        metrics.pop("income_from_continuing_operations")
        calculated, notes = CALC.equity_metrics(metrics)
        self.assertIsNone(calculated["beneish_components"]["tata"])
        self.assertIn("income_from_continuing_operations", notes["beneish_components.tata"])


if __name__ == "__main__":
    unittest.main()
