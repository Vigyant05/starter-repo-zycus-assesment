"""
Evaluation harness runner.

Executes all test cases for Task 1 and Task 2, scores them using
rule-based and LLM-as-judge checks, and generates a summary report.
"""

import json
import time
from pathlib import Path

from src.eval.test_cases import TRIAGE_TEST_CASES, SUMMARISER_TEST_CASES, TriageTestCase, SummariserTestCase
from src.eval.scoring import (
    TestResult,
    check_triage_rules,
    check_summariser_rules,
    llm_judge_triage,
    llm_judge_summariser,
    compute_quality_score,
)
from src.triage.agent import triage_ticket
from src.summariser.agent import generate_account_brief
from src.config import PROJECT_ROOT


class EvalHarness:
    """Runs evaluations and generates reports."""

    def __init__(self):
        self.results: list[TestResult] = []

    def run_triage_eval(self, test_case: TriageTestCase) -> TestResult:
        """Run a single triage test case."""
        print(f"Running triage test: {test_case.name}...")
        try:
            # 1. Execute the agent
            result = triage_ticket(subject=test_case.subject, body=test_case.body)
            
            # 2. Rule-based checks
            rule_checks = check_triage_rules(
                result=result,
                expected_category=test_case.expected_category,
                expected_urgency=test_case.expected_urgency,
                expected_product=test_case.expected_product,
                expect_kb_match=test_case.expect_kb_match,
            )
            
            # 3. LLM-as-judge scoring
            llm_score, llm_reasoning = llm_judge_triage(
                ticket_subject=test_case.subject,
                ticket_body=test_case.body,
                result=result,
                acceptance_criteria=test_case.acceptance_criteria,
            )
            
            # 4. Final score
            quality_score = compute_quality_score(rule_checks, llm_score)
            
            # Determine pass/fail: must pass all rule checks + LLM score > 0.7
            passed = all(rule_checks.values()) and llm_score >= 0.7
            
            return TestResult(
                test_name=test_case.name,
                passed=passed,
                quality_score=quality_score,
                rule_checks=rule_checks,
                llm_judge_score=llm_score,
                llm_judge_reasoning=llm_reasoning,
                is_adversarial=test_case.is_adversarial,
            )
            
        except Exception as e:
            print(f"  Error: {str(e)}")
            return TestResult(
                test_name=test_case.name,
                passed=False,
                quality_score=0.0,
                error=str(e),
                is_adversarial=test_case.is_adversarial,
            )

    def run_summariser_eval(self, test_case: SummariserTestCase) -> TestResult:
        """Run a single summariser test case."""
        print(f"Running summariser test: {test_case.name}...")
        
        # Handle the expected exception test case
        if test_case.name == "adversarial_missing_account":
            try:
                generate_account_brief(test_case.account_id)
                return TestResult(
                    test_name=test_case.name,
                    passed=False,
                    quality_score=0.0,
                    error="Failed to raise expected ValueError",
                    is_adversarial=True,
                )
            except ValueError:
                return TestResult(
                    test_name=test_case.name,
                    passed=True,
                    quality_score=1.0,
                    is_adversarial=True,
                )
            except Exception as e:
                 return TestResult(
                    test_name=test_case.name,
                    passed=False,
                    quality_score=0.0,
                    error=f"Raised wrong exception type: {type(e)}",
                    is_adversarial=True,
                )
                
        # Normal execution flow
        try:
            # 1. Execute the agent
            result = generate_account_brief(test_case.account_id)
            
            # Special check for determinism test
            if test_case.name == "determinism_check":
                result2 = generate_account_brief(test_case.account_id)
                passed = (
                    result.executive_summary == result2.executive_summary
                    and result.talking_points == result2.talking_points
                )
                return TestResult(
                    test_name=test_case.name,
                    passed=passed,
                    quality_score=1.0 if passed else 0.0,
                    rule_checks={"is_deterministic": passed},
                )
                
            # 2. Rule-based checks
            rule_checks = check_summariser_rules(
                result=result,
                expect_risks=test_case.expect_risks,
                min_risk_count=test_case.min_risk_count,
                expect_churn_signal=test_case.expect_churn_signal,
            )
            
            # 3. LLM-as-judge scoring
            llm_score, llm_reasoning = llm_judge_summariser(
                account_id=test_case.account_id,
                result=result,
                acceptance_criteria=test_case.acceptance_criteria,
            )
            
            # 4. Final score
            quality_score = compute_quality_score(rule_checks, llm_score)
            
            # Determine pass/fail
            passed = all(rule_checks.values()) and llm_score >= 0.7
            
            return TestResult(
                test_name=test_case.name,
                passed=passed,
                quality_score=quality_score,
                rule_checks=rule_checks,
                llm_judge_score=llm_score,
                llm_judge_reasoning=llm_reasoning,
                is_adversarial=test_case.is_adversarial,
            )
            
        except Exception as e:
            print(f"  Error: {str(e)}")
            return TestResult(
                test_name=test_case.name,
                passed=False,
                quality_score=0.0,
                error=str(e),
                is_adversarial=test_case.is_adversarial,
            )

    def run_all(self):
        """Run all test cases for both tasks."""
        self.results = []
        
        print("\n=== Running Task 1: Triage Evaluations ===")
        for test in TRIAGE_TEST_CASES:
            res = self.run_triage_eval(test)
            self.results.append(res)
            time.sleep(2)  # Delay to respect Groq rate limits
            
        print("\n=== Running Task 2: Summariser Evaluations ===")
        for test in SUMMARISER_TEST_CASES:
            res = self.run_summariser_eval(test)
            self.results.append(res)
            time.sleep(2)  # Delay to respect Groq rate limits
            
    def generate_reports(self):
        """Generate JSON and Markdown reports."""
        if not self.results:
            print("No results to report.")
            return

        json_path = PROJECT_ROOT / "eval_report.json"
        md_path = PROJECT_ROOT / "eval_report.md"
        
        # Calculate summary metrics
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        avg_quality = sum(r.quality_score for r in self.results) / total if total > 0 else 0
        
        # 1. Generate JSON
        report_data = {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate_percent": round((passed / total) * 100, 1) if total > 0 else 0,
                "average_quality_score": round(avg_quality, 3),
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "is_adversarial": r.is_adversarial,
                    "passed": r.passed,
                    "quality_score": r.quality_score,
                    "llm_judge_score": r.llm_judge_score,
                    "llm_judge_reasoning": r.llm_judge_reasoning,
                    "rule_checks": r.rule_checks,
                    "error": r.error,
                }
                for r in self.results
            ]
        }
        
        with open(json_path, "w") as f:
            json.dump(report_data, f, indent=2)
            
        # 2. Generate Markdown table
        md_lines = [
            "# AI Support Tooling — Evaluation Report",
            "",
            "## Summary",
            f"- **Total Tests:** {total}",
            f"- **Passed:** {passed} ({report_data['summary']['pass_rate_percent']}%)",
            f"- **Average Quality Score:** {round(avg_quality, 2)} / 1.0",
            "",
            "## Detailed Results",
            "",
            "| Test Name | Type | Passed | Score | LLM Judge | Rule Checks (Pass/Total) | Notes |",
            "|-----------|------|--------|-------|-----------|-------------------------|-------|"
        ]
        
        for r in self.results:
            test_type = "Adversarial" if r.is_adversarial else "Standard"
            status = "✅ PASS" if r.passed else "❌ FAIL"
            
            rule_pass = sum(1 for v in r.rule_checks.values() if v)
            rule_total = len(r.rule_checks)
            rules_str = f"{rule_pass}/{rule_total}" if rule_total > 0 else "N/A"
            
            notes = r.error if r.error else r.llm_judge_reasoning
            # Truncate notes for table readability
            if len(notes) > 80:
                notes = notes[:77] + "..."
                
            # Sanitize notes for markdown table
            notes = notes.replace("\n", " ").replace("|", "-")
            
            md_lines.append(
                f"| `{r.test_name}` | {test_type} | {status} | {r.quality_score:.2f} | {r.llm_judge_score:.2f} | {rules_str} | {notes} |"
            )
            
        with open(md_path, "w") as f:
            f.write("\n".join(md_lines))
            
        print(f"\n✅ Reports generated:")
        print(f"   - {json_path}")
        print(f"   - {md_path}")
        print(f"   Score: {passed}/{total} passed.")


def run_evals():
    """Entry point for running the evaluation harness."""
    harness = EvalHarness()
    harness.run_all()
    harness.generate_reports()
