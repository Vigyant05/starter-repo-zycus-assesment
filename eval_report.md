# AI Support Tooling — Evaluation Report

## Summary
- **Total Tests:** 14
- **Passed:** 3 (21.4%)
- **Average Quality Score:** 0.46 / 1.0

## Detailed Results

| Test Name | Type | Passed | Score | LLM Judge | Rule Checks (Pass/Total) | Notes |
|-----------|------|--------|-------|-----------|-------------------------|-------|
| `clear_p1_bug` | Standard | ❌ FAIL | 0.91 | 0.90 | 11/12 | The triage output meets most of the acceptance criteria, correctly classifyin... |
| `billing_question` | Standard | ❌ FAIL | 0.85 | 0.80 | 9/10 | The output meets most of the acceptance criteria, correctly classifying the i... |
| `feature_request` | Standard | ✅ PASS | 1.00 | 1.00 | 11/11 | The triage output meets all the acceptance criteria, accurately classifying t... |
| `known_error_code` | Standard | ✅ PASS | 0.95 | 0.90 | 12/12 | The triage output correctly identifies SecureVault as the product and matches... |
| `integration_issue` | Standard | ❌ FAIL | 0.86 | 0.80 | 11/12 | The output correctly identifies CloudSync as the product and classifies it un... |
| `adversarial_ambiguous_category` | Adversarial | ❌ FAIL | 0.00 | 0.00 | N/A | Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-... |
| `adversarial_misleading_urgency` | Adversarial | ❌ FAIL | 0.85 | 0.80 | 9/10 | The output correctly classifies the issue as a Bug and assigns it a P4 urgenc... |
| `at_risk_account` | Standard | ❌ FAIL | 0.00 | 0.00 | N/A | 3 validation errors for AccountBrief talking_points.0   Input should be a val... |
| `healthy_account` | Standard | ❌ FAIL | 0.00 | 0.00 | N/A | 3 validation errors for AccountBrief talking_points.0   Input should be a val... |
| `enterprise_with_p1_tickets` | Standard | ❌ FAIL | 0.00 | 0.00 | N/A | 3 validation errors for AccountBrief talking_points.0   Input should be a val... |
| `new_account` | Standard | ❌ FAIL | 0.00 | 0.00 | N/A | 3 validation errors for AccountBrief talking_points.0   Input should be a val... |
| `determinism_check` | Standard | ❌ FAIL | 0.00 | 0.00 | N/A | 3 validation errors for AccountBrief talking_points.0   Input should be a val... |
| `adversarial_no_tickets` | Adversarial | ❌ FAIL | 0.00 | 0.00 | N/A | 3 validation errors for AccountBrief talking_points.0   Input should be a val... |
| `adversarial_missing_account` | Adversarial | ✅ PASS | 1.00 | 0.00 | N/A |  |