# Spec: Test Feature

## Capability Map

| Capability | Purpose | State |
|-----------|---------|-------|
| Cap 1: Core Engine | 核心引擎 | confirmed |
| Cap 2: Plugin System | 插件系统 | inferred |
| Cap 3: Remote API | 远程 API | unresolved |

### Capability Details

- CAP1: Core Engine — confirmed by existing implementation
- CAP2: Plugin System — inferred from common patterns
- CAP3: Remote API — unresolved, needs deep-research

## Non-Functional Requirements

### Performance
- Latency < 100ms p95
- Startup time < 2s

### Security
- Input sanitization against injection
- Permission model: role-based access

### Reliability
- Graceful degradation on dependency failure

### Observability
- Structured logging with correlation IDs
- Metrics: latency histogram, error rate

## Error Handling

### PTY Launch Failure
- Internal: throw ITerminalLaunchError
- User visible: display red banner "Terminal failed to start", show retry button

### Connection Lost
- Internal: enter reconnecting state
- User visible: yellow "Reconnecting..." banner, input preserved, auto-flush on reconnect

## Configuration

| Item | Default | Effective When |
|------|---------|----------------|
| shellPath | /bin/bash | next session |
| flowControlHighWater | 4096 | immediate |

### Test Strategy Note per capability
- CAP1: cross-platform integration tests (Windows/macOS/Linux)
- CAP2: unit tests for plugin loader, integration for hot-reload
- CAP3: contract tests against mock backend
