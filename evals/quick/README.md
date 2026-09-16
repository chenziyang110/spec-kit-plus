# Quick adaptive execution benchmark

Goal: measure whether adaptive execution reduces cost while preserving accepted
outcomes. This dataset does not decide quality from token count alone.

## Matrix

| Case | Worker Full | Worker Compact | Direct Full | Direct Compact |
|---|---|---|---|---|
| trivial fix | | | | |
| feature addition | | | | |
| cross module change | | | | |
| risky change | | | | |
| recovery | | | | |

## Required observations

Record:

- task case id
- execution mode
- input/output tokens
- tool calls
- duration
- retries
- human intervention
- independent acceptance evidence

Unknown values remain unknown. Do not convert missing acceptance evidence into
failure or success.
