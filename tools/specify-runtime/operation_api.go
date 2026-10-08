package main

// Operation commands are a separate state protocol. They deliberately do not
// inherit feature-workflow stage transitions or a shell execution facade.
type operationAPIContract struct {
	usage      string
	sideEffect string
	schema     string
	input      string
}

var operationAPIContracts = map[string]operationAPIContract{
	"do.start": {
		usage:      "specify-runtime do start --input-json <object|-> [--project-root <path>] --format json",
		sideEffect: "creates-do-session-and-work-ownership", schema: "do-start-input",
		input: "Freeze the exact ordered definition, required checks, source/output/write scopes and optional method revision before native execution. Reusing an explicit session_id with identical inputs returns the same session. Runtime records and validates observations; it never executes the operation.",
	},
	"do.record": {
		usage:      "specify-runtime do record <session-id> --input-json <object|-> [--project-root <path>] --format json",
		sideEffect: "writes-do-session-and-evidence", schema: "do-record-input",
		input: "Use expected_revision and request_id. Record started before invoking a native tool; checkpoint terminal observations with exact step/attempt ids, argv, cwd, tool identity and observed results. An interrupted or unknown attempt requires explicit observation before retry.",
	},
	"do.validate": {
		usage:      "specify-runtime do validate <session-id> [--project-root <path>] --format json",
		sideEffect: "read-only",
		input:      "Revalidate frozen required steps/checks, current source/output hashes and source-mutation closeout. Successful agent-tool observations are not represented as independent runtime execution proof.",
	},
	"do.finish": {
		usage:      "specify-runtime do finish <session-id> --input-json <object|-> [--project-root <path>] --format json",
		sideEffect: "writes-do-session-and-work-closeout", schema: "do-finish-input",
		input: "Use expected_revision; identical state/receipt replay is idempotent. Runtime derives execution_outcome separately from knowledge_status. Persist an already verified method through playbook.update, then close knowledge without rerunning the completed operation.",
	},
	"do.resume": {
		usage:      "specify-runtime do resume <session-id> [--input-json <object|->] [--project-root <path>] --format json",
		sideEffect: "read-only-without-input-otherwise-writes-do-recovery", schema: "do-resume-input",
		input: "Read-only without input. Recovery requires expected_revision and an exact attempt/recovery receipt. Typed replan also requires request_id, an observed failed attempt and inspected effects; it preserves immutable definition epochs, extends exact scopes and requires fresh observations for all required steps and checks. Exact replay is idempotent. Never infer that an interrupted process completed or is safe to retry.",
	},
	"do.show": {
		usage:      "specify-runtime do show (<session-id> [--section <definition|definitions|definition:epoch|attempts|attempt:id>]|--active [--adapter-id <adapter-id>]) [--project-root <path>] --format json",
		sideEffect: "read-only",
		input:      "Read a compact explicit session, expanding only a selected definition or attempt section. --active resolves live Work Board bindings, optionally within an explicit adapter identity, and returns an ambiguity blocker for multiple sessions; it never chooses the newest directory.",
	},
	"playbook.find": {
		usage:      "specify-runtime playbook find [--query <text>] [--operation <operation>] [--target <target>] [--context-json <object>] [--limit <1..20>] [--cursor <n>] [--project-root <path>] --format json",
		sideEffect: "read-only", schema: "playbook-find-input",
		input: "Return bounded method cards, aliases and applicability/drift status. Use operation/target flags and explicit context for applicability filtering; expand only selected candidates. The schema documents the query fields, which are passed using the documented flags.",
	},
	"playbook.show": {
		usage:      "specify-runtime playbook show --id <playbook-id> [--section <summary|steps|checks|evidence|all>] [--revision <n>|--proposal-digest <sha256>] [--project-root <path>] --format json",
		sideEffect: "read-only", schema: "playbook-show-input",
		input: "Expand selected ordered sections from one method with revision, digest and source drift. A historic success does not satisfy the current DoSession's validation obligations.",
	},
	"playbook.update": {
		usage:      "specify-runtime playbook update --input-json <object|-> [--project-root <path>] --format json",
		sideEffect: "writes-playbook-revision-or-proposal", schema: "playbook-update-input",
		input: "Compare-and-swap base_digest; bind the exact definition digest and previous method revision to a passed DoSession. Unverified behavior remains a proposal. Repeated unchanged success records bounded usage without creating another content revision.",
	},
	"playbook.validate": {
		usage:      "specify-runtime playbook validate (--id <playbook-id>|--input-json <definition|->) [--context-json <object>] [--project-root <path>] --format json",
		sideEffect: "read-only", schema: "playbook-validate-input",
		input: "Validate structural integrity and current applicability/source fingerprints without silently repairing the method or blessing it for native execution.",
	},
}

func applyOperationAPIContract(id string, capability map[string]any, env *Envelope) {
	contract, ok := operationAPIContracts[id]
	if !ok {
		return
	}
	capability["usage"] = contract.usage
	capability["side_effect"] = contract.sideEffect
	capability["input_contract"] = contract.input
	if contract.schema != "" {
		capability["input_schema"] = contract.schema
		env.ShowArgv = []string{"specify-runtime", "api", "schema", contract.schema, "--format", "json"}
	}
}
