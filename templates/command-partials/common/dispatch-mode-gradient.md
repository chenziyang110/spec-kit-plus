## Dispatch Mode

Dispatch mode follows command tier, not a uniform rule.

| Tier | Dispatch Mode | Rule |
|------|---------------|------|
| trivial | leader-direct | No subagent dispatch. Leader performs and verifies the change directly. |
| light | subagent-preferred | Dispatch to one subagent; leader-inline fallback allowed if dispatch unavailable. |
| heavy | subagent-mandatory | Must dispatch. If dispatch unavailable, record reason and escalate. |

### Fallback (light tier only)

When subagent dispatch is unavailable for a light-tier command:
1. Record the reason in workflow state
2. Switch to `execution_surface: leader-inline`
3. Proceed with the same scope and verification gates

This is a designed fallback path, not an exception.
