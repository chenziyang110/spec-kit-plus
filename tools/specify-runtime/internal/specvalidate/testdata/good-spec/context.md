# Context: Test Feature

## Scout Summary

### Ownership & Truth Sources
- Core engine owned by `src/engine/`, truth in `Engine` class
- Plugin system: truth in `PluginRegistry`

### Reusable Assets
- Existing `EventBus` can be reused for plugin communication
- `Logger` interface already defined in `src/common/`

### Change-Propagation Hotspots
- Modifying engine API affects Plugin System and Remote API consumers
- Configuration schema changes propagate to all modules

### Integration Boundaries
- Remote API ↔ Engine: WebSocket boundary
- Plugin System ↔ Engine: in-process event bus

### Verification Entry Points
- Engine tests: `tests/engine/`
- Integration tests: `tests/integration/`

### Known Unknowns
- Remote protocol versioning strategy not yet defined
- Plugin sandboxing requirements unclear

## Change-Propagation Matrix

| Change Surface | Direct Consumers | Indirect (via) | Risk |
|---------------|------------------|-----------------|------|
| Engine API | Plugin System, Remote | UI Layer (via Plugin) | BREAKING |
| Config Schema | All modules | — | MEDIUM |
| Event Format | Plugin System | Remote (via Plugin) | HIGH |
