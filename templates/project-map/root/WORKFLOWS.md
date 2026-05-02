# Workflows

**Last Updated:** YYYY-MM-DD
**Coverage Scope:** repository-wide user and maintainer workflow paths
**Primary Evidence:** templates/commands/, .agents/skills/, docs, tests
**Update When:** entry commands, handoffs, or neighboring workflow risks change

## Core User Flows

[Describe the entry-to-exit data flow for core business or runtime workflows.]

## Core Maintainer Flows

## Capability Flows

## Runtime Data and Event Flows

[Describe runtime data flow, event flow, workflow orchestration, and entity or state-machine lifecycles where those relationships govern behavior.]

## Key Business Lifecycles

[Describe the end-to-end lifecycle of the highest-value user or maintainer journeys, including what starts them, what transforms state, and what marks completion.]

## State and Entity Lifecycles

[Record state lifecycle transitions, persistent checkpoints, cache checkpoints, and coordination identifiers that downstream changes must preserve. If concurrent feature lanes exist, document lane lifecycle state, recovery state, lease expiry behavior, and reconcile-before-resume rules explicitly.]

## Failure and Recovery Flows

[If power-loss or crash recovery matters, state the fail-closed rules. Record whether `uncertain` recovery states block auto-resume and how the system chooses between multiple resumable lanes.]

## Entry Points, Contracts, and Handoffs

## State Transitions and Compatibility Notes

[Call out handoff fields, state transitions, and compatibility notes that govern the workflow.]

## Implicit Dependencies and Feature-Flag Gates

[Explain ordering constraints, hidden runtime dependencies, feature-flag gates, or config-driven detours that are not obvious from static imports alone.]

## Adjacent Workflow Risks

## Entry Commands and Handoffs
