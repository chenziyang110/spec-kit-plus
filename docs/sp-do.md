# sp-do and project playbooks

This change adds an explicit project-operation workflow for builds, packaging, existing test suites, environment preparation, and reproducible local tooling. Classic `sp-do` and Advanced `spx-do` share the Go runtime and a project-local Playbook store.

## Implementation contract

- Python owns bootstrap, installation, integration rendering and compatibility. Go owns DoSession, Playbook, evidence, revisions and state mutation.
- The Agent executes through native tools. Recorded observations keep `evidence_origin=agent_tool_observation`; the runtime verifies structure, bindings and readable outputs without claiming it independently executed a command.
- `.specify/playbooks/<id>/playbook.json` is current method authority. `PLAYBOOK.md` and the compact index are derived. Revisions are immutable; unverified behavioral changes remain proposals.
- `.specify/do/sessions/<id>/` owns the current operation, frozen required steps/checks, native-tool observations, attempts and recovery points. It does not revive retired Run APIs or introduce a fifth Activity workflow.
- Retrieval uses bounded cards, selected method sections, current applicability checks and exact source/toolchain evidence. A previously useful method is not proof that this invocation passed.
- Revision updates use compare-and-swap and execution-bound evidence. Repeated submission is idempotent; repeated success without new method knowledge does not expand the guide.
- Learning remains the home of reusable lessons and constraints. Methods reference Learning; method revision never automatically promotes a lesson into a project rule.
- Exact Work ownership covers session/method writes and generated output paths. Native methods do not grant authorization for new external effects.
- Retained source/script/configuration changes require canonical `sp-do` cognition closeout. Pure outputs and method bookkeeping explicitly record no source mutation.
- Independent DoSession validation routes through Go; no synthetic feature `workflow-state.md` is created.
- Classic/Advanced installation, references, launchers, hooks, repair and wheel-only installation preserve user methods and edits.

## Delivery acceptance

1. First execution completes and records a reusable method with current evidence.
2. A synonymous second request selects the same method and reads only relevant details.
3. Verified improvements create a new revision; unchanged success leaves method content unchanged.
4. Script, configuration, dirty-source or platform drift causes revalidation rather than stale success.
5. Partial failures, interrupted commands and missing required output evidence cannot pass completion.
6. Concurrent updates preserve both evidence sets and reject stale revision publication.
7. Recovery after knowledge persistence failure does not rerun an already verified build/test.
8. Native CLI/profile rendering, both additive install orders, user edits and repair work from the built wheel.

Implementation and verification progress are tracked in the pull request. The existing release process distributes a matching runtime after integration; this document does not claim a release has been published.
