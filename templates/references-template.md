# Reference Memory: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]

## Truth Sources Used For Route And Intent Lock

- [source path or user-supplied reference]
- [repository evidence, PRD input, existing implementation, policy, or user answer that justified a locked route, intent, invariant, or complexity rule]


## Lossless Source Map

- Journal: `brainstorming/journal.ndjson`
- Stage Manifest: `brainstorming/stage-manifest.json`
- Source Event IDs:
  - EVT-###: [Decision, evidence, answer, or checkpoint used]
- Evidence IDs:
  - EVD-###: [Evidence record used]
- Compiled From:
  - `compiled_from`: [journal range and stage artifact inputs]

## Must-Preserve Reference Map

| MP ID | Source | Why It Must Be Preserved | Downstream Consumer |
| --- | --- | --- | --- |
| MP-### | [source path or URL] | [constraint or evidence role] | [spec | context | plan | tasks | implement] |

## Reference Entries

## Truth Sources Used For Route And Intent Lock

- [Source path, repository surface, PRD, or user-supplied material that directly informed route or intent lock]

### Reference 1

- **Source**: [URL, document path, repository, issue, interview note, or artifact name]
- **Description**: [What this source is]
- **Relevance**: [Why it matters to current discovery]
- **Completeness Evidence Mapping**:
  - [Which completeness judgment, missing-capability check, or domain-expected expectation this source supports]
  - [Which part of the ideal complete requirement shape in `spec.md` this source informed]
- **Boundary Evidence Mapping**:
  - [Which current delivery boundary, project constraint, or non-goal this source supports]
  - [Which impact surface, dependency, or compatibility conclusion in `context.md` this source supports]
- **Compatibility / Impact Notes**:
  - [Any compatibility, dependency, or adjacent-effect takeaway preserved from this source]

## Consequence Evidence

- `CA-###`: project cognition query, returned `minimal_live_reads`, discussion handoff, source evidence, or research evidence that supports the obligation.

### Additional References

Repeat the following entry structure once for each retained source:

```markdown
### Reference [N]

- **Source**: [URL, document path, repository, issue, interview note, or artifact name]
- **Description**: [What this source is]
- **Relevance**: [Why it matters to current discovery]
- **Completeness Evidence Mapping**:
  - [Which completeness judgment, missing-capability check, or domain-expected expectation this source supports]
  - [Which part of the ideal complete requirement shape in `spec.md` this source informed]
- **Boundary Evidence Mapping**:
  - [Which current delivery boundary, project constraint, or non-goal this source supports]
  - [Which impact surface, dependency, or compatibility conclusion in `context.md` this source supports]
- **Compatibility / Impact Notes**:
  - [Any compatibility, dependency, or adjacent-effect takeaway preserved from this source]
```
