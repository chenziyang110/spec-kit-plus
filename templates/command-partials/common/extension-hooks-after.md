**Check for extension hooks**: {HOOK_TRIGGER}.
- Run `{{specify-subcmd:specify-runtime hook extension-plan --event after_{HOOK_KEY} --format json}}`; never inspect or parse extension storage directly.
- The runtime returns only enabled, unconditional actionable items with integration-native `invocation`, `optional`, `prompt`, and description fields. It filters disabled hooks and defers conditional hooks without exposing YAML.
- Offer each `optional: true` item using its returned invocation. Execute each `optional: false` invocation and wait for its result before closing.
- If `actionable_count` is zero, continue silently.
