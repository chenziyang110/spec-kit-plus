# Semantic Audit Resume Examples

Use these examples when a generated workflow resumes with persisted
`semantic-audit-input.json`, `semantic-audit-output.json`, and Semantic Audit
State fields. The table remains a prompt-level comparison guide. The JSON
fixtures in this directory provide a concrete downstream runtime validator
adoption path.

Run the fresh fixture from this directory:

```bash
project-cognition semantic-audit-resume --input resume-validation.json --format json
```

Expected fresh result:

```yaml
semantic_audit_generated_resume_smoke: passed
semantic_audit_resume_status: fresh
can_reuse_persisted_claim_readiness: true
grants_permission: false
```

Run the stale route fixture from this directory:

```bash
project-cognition semantic-audit-resume --input resume-validation-route-changed.json --format json
```

Expected stale result:

```yaml
semantic_audit_generated_resume_smoke: failed
semantic_audit_resume_status: needs-rerun
semantic_audit_stale_reasons: [route-changed]
can_reuse_persisted_claim_readiness: false
grants_permission: false
```

Additional stale matrix fixtures:

- `resume-validation-active-claim-changed.json` expects `semantic_audit_stale_reasons: [active-claim-changed, route-changed]` because the route fingerprint includes `active_claim_type`
- `resume-validation-missing-file.json` expects `semantic_audit_stale_reasons: [missing-file]`
- `resume-validation-claim-ref-mismatch.json` expects `semantic_audit_stale_reasons: [claim-ref-mismatch]`
- `resume-validation-verification-ref-mismatch.json` expects `semantic_audit_stale_reasons: [verification-ref-mismatch]`

| Scenario | Required Comparison | State Result |
| --- | --- | --- |
| fresh | Both audit files exist. Workflow state selected candidates, active claim type, claim authorization refs, claim verification refs, and route fingerprint match `semantic-audit-input.json.semantic_audit_input.route_decision` plus `semantic-audit-output.json.workflow_authorization` and `semantic-audit-output.json.claim_readiness`. | `semantic_audit_generated_resume_smoke: passed`; `semantic_audit_resume_status: fresh`; `semantic_audit_stale_reasons: [none]` |
| missing-file | Either persisted audit file is absent or unreadable. | `semantic_audit_generated_resume_smoke: failed`; `semantic_audit_resume_status: needs-rerun`; `semantic_audit_stale_reasons: [missing-file]` |
| route-changed | Selected candidate IDs or `semantic_audit_route_fingerprint` differ from the persisted route decision. Fingerprint mismatches are `route-changed`. | `semantic_audit_generated_resume_smoke: failed`; `semantic_audit_resume_status: needs-rerun`; `semantic_audit_stale_reasons: [route-changed]` |
| active-claim-changed | `active_claim_type` differs from the persisted workflow state or claim readiness context. Because the route fingerprint includes `active_claim_type`, this fixture also reports `route-changed`. | `semantic_audit_generated_resume_smoke: failed`; `semantic_audit_resume_status: needs-rerun`; `semantic_audit_stale_reasons: [active-claim-changed, route-changed]` |
| claim-ref-mismatch | `claim_authorization_refs` differ from `semantic-audit-output.json.workflow_authorization` or the matching claim authorization entry. | `semantic_audit_generated_resume_smoke: failed`; `semantic_audit_resume_status: needs-rerun`; `semantic_audit_stale_reasons: [claim-ref-mismatch]` |
| verification-ref-mismatch | `claim_verification_refs` differ from `semantic-audit-output.json.claim_readiness.claim_verification_refs` or the matched verification evidence refs. | `semantic_audit_generated_resume_smoke: failed`; `semantic_audit_resume_status: needs-rerun`; `semantic_audit_stale_reasons: [verification-ref-mismatch]` |

When more than one mismatch applies, record every reason. Any failed smoke keeps
`claim_ready` false and requires rebuilding `semantic-audit-input.json` before a
root-cause, fixed, completed, or release-safe claim.
