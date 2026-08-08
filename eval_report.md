# AI Support Tooling — Evaluation Report

## Summary
- **Total Tests:** 14
- **Passed:** 11 (78.6%)
- **Average Quality Score:** 0.88 / 1.0

## Detailed Results

| Test Name | Type | Passed | Score | LLM Judge | Rule Checks (Pass/Total) | Notes |
|-----------|------|--------|-------|-----------|-------------------------|-------|
| `clear_p1_bug` | Standard | ✅ PASS | 1.00 | 1.00 | 12/12 | The triage output meets all acceptance criteria: it correctly classifies the ... |
| `billing_question` | Standard | ✅ PASS | 1.00 | 1.00 | 10/10 | The triage output correctly classifies the issue as a Billing inquiry, assign... |
| `feature_request` | Standard | ✅ PASS | 1.00 | 1.00 | 11/11 | The triage output correctly classifies the issue as a Feature Request, assign... |
| `known_error_code` | Standard | ✅ PASS | 1.00 | 1.00 | 12/12 | The triage output meets all acceptance criteria: it correctly identifies the ... |
| `integration_issue` | Standard | ✅ PASS | 0.95 | 0.90 | 12/12 | The output correctly classifies the issue as an Integration category, identif... |
| `adversarial_ambiguous_category` | Adversarial | ✅ PASS | 0.95 | 0.90 | 9/9 | The output correctly identifies AnalyticsHub as the product, categorizes the ... |
| `adversarial_misleading_urgency` | Adversarial | ✅ PASS | 1.00 | 1.00 | 10/10 | The output correctly classifies the issue as a P4 bug due to its cosmetic nat... |
| `at_risk_account` | Standard | ❌ FAIL | 0.89 | 0.90 | 7/8 | The account brief meets most of the acceptance criteria, including a well-str... |
| `healthy_account` | Standard | ✅ PASS | 0.95 | 0.90 | 4/4 | The account brief meets most of the acceptance criteria, including a well-str... |
| `enterprise_with_p1_tickets` | Standard | ❌ FAIL | 0.60 | 0.40 | 4/5 | The account brief lacks reference to P1 ticket context in the executive summa... |
| `new_account` | Standard | ✅ PASS | 0.95 | 0.90 | 4/4 | The account brief meets most of the acceptance criteria, including a well-str... |
| `determinism_check` | Standard | ❌ FAIL | 0.00 | 0.00 | 0/1 |  |
| `adversarial_no_tickets` | Adversarial | ✅ PASS | 1.00 | 1.00 | 4/4 | The account brief output meets all acceptance criteria, handling zero tickets... |
| `adversarial_missing_account` | Adversarial | ✅ PASS | 1.00 | 0.00 | N/A |  |