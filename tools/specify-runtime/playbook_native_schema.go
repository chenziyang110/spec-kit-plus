package main

func playbookNativeActionSchema() map[string]any {
	return doSchemaObject(map[string]any{
		"kind": doSchemaEnum("file", "browser", "desktop", "connector"),
		"tool": playbookSchemaString(256), "target": playbookSchemaString(2048),
		"arguments": map[string]any{"type": "object", "maxProperties": 128, "description": "Actual structured native tool arguments, at most 64 KiB UTF-8, depth 24 and 4096 nodes. Duplicate keys and secret values are rejected. Runtime records this call but never executes it or grants authority over its target."},
	}, "kind", "tool", "target", "arguments")
}

func doNativeObservationSchema() map[string]any {
	return doSchemaObject(map[string]any{
		"outcome": doSchemaEnum("succeeded", "failed", "unknown"),
		"result":  map[string]any{"description": "Bounded actual native-tool result JSON, at most 64 KiB, depth 24 and 4096 nodes; no secrets or duplicate keys. Stored in a runtime-owned immutable observation snapshot. Unknown outcome is interrupted, never successful."},
	}, "outcome", "result")
}
