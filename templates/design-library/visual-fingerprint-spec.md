# Visual Fingerprint Specification

```yaml
version: "1"
schema: spec-kit-visual-fingerprint-v1
```

## Purpose

Detect whether generated design directions are **materially differentiated at
render-system level**, not only in manifest labels (dials, aesthetic family, or
signature prose).

A fingerprint is a deterministic semantic hash of the direction's visual token
payload. Ready lint uses it as a **quality-layer** check: identical fingerprints
across directions fail even when metadata differs.

## Fingerprint object

```json
{
  "version": "1",
  "dimensions": [
    "typography",
    "geometry",
    "density",
    "elevation",
    "motion",
    "modes"
  ],
  "hash": "<sha256 hex>"
}
```

This object is the **rule contract** for computation and comparison. It is not a
preview-manifest schema change: fingerprints may be computed at lint time and
emitted in diagnostics without rewriting `design-preview-manifest.schema.json`.

## Dimensions (v1)

| Dimension | Manifest path | Meaning |
| --- | --- | --- |
| `typography` | `direction.typography` | Display/body stacks and tracking |
| `geometry` | `direction.geometry` | Control and surface radii |
| `density` | `direction.density` | Spacing unit, label, scale tokens |
| `elevation` | `direction.elevation` | Surface and control shadows |
| `motion` | `direction.motion` | Duration, easing, distance, reduced motion |
| `modes` | `direction.modes` | light / dark / high-contrast palettes |

These dimensions are the render-driving systems owned by the direction payload.
They are distinct from taste dials (`dials.variance|motion|density`), which
describe intent axes rather than token systems.

## Canonicalization (v1)

1. Select only the declared `dimensions` in order from the direction object.
2. Recursively sort object keys.
3. Normalize string values by stripping outer whitespace and collapsing internal
   whitespace runs to a single space.
4. Drop runtime-only or non-visual fields (not present in the dimension set).
5. Serialize as canonical JSON (`sort_keys=true`, UTF-8, no insignificant
   whitespace variation beyond JSON separators).
6. Compute SHA-256 over the UTF-8 bytes; store lowercase hex in `hash`.

## Compatibility

Two fingerprints are comparable only when **both** hold:

- `version` is identical
- `dimensions` lists are identical (same order and members)

If version or dimensions differ, do not treat hash inequality as design
divergence and do not treat equality as sameness across rule generations.

## Evolution

| Change | Action |
| --- | --- |
| Add/remove/rename a dimension | Bump `version` (for example `"2"`) and update this spec |
| Change canonicalization | Bump `version` |
| Same dimensions, bugfix in hash | Bump `version` if hashes change for identical inputs |

Agents and CI must record which fingerprint rule version produced a failure so
a rule upgrade is not misread as a design regression.

## Non-goals (v1)

- Screenshot / pixel diff
- Browser, OS, or font rasterization variance
- Comparing directions across different fingerprint rule versions
