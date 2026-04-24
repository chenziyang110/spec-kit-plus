import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const repoRoot = resolve(__dirname, '..', '..', '..', '..');
const bridgePath = join(repoRoot, 'extensions', 'agent-teams', 'engine', 'src', 'cli', 'bridge.js');
const engineBinDir = join(repoRoot, 'extensions', 'agent-teams', 'engine', 'bin');

function writeFile(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, 'utf8');
}

test('bridge writes agent-teams ledger, syncs worker assets, and hands runtime-cli a dependency-aware task graph', () => {
  const projectRoot = mkdtempSync(join(tmpdir(), 'agent-teams-bridge-'));
  const featureDir = join(projectRoot, 'specs', '001-sample-feature');
  const configPath = join(projectRoot, '.specify', 'extensions', 'agent-teams', 'agent-teams-config.yml');
  const runtimeCapturePath = join(projectRoot, 'runtime-input.json');
  const runtimeEnvPath = join(projectRoot, 'runtime-env.json');
  const fakeRuntimePath = join(projectRoot, 'fake-runtime.mjs');
  const stateRoot = join(projectRoot, '.specify', 'agent-teams', 'state');
  const sourceCodexHome = join(projectRoot, 'source-codex-home');
  const sourceConfigPath = join(sourceCodexHome, 'config.toml');
  const sourceOmxConfigPath = join(sourceCodexHome, '.omx-config.json');

  writeFile(
    join(featureDir, 'spec.md'),
    '# Feature\n\nBridge runtime integration.\n',
  );
  writeFile(
    join(featureDir, 'tasks.md'),
    [
      '# Tasks',
      '',
      '- [ ] T001 Prepare shared runtime context in docs/runtime.md',
      '- [ ] T002 [P] Implement worker bootstrap in src/worker_bootstrap.ts',
      '- [ ] T003 [P] Add runtime verification in tests/runtime_cli.test.ts',
      '- [ ] T004 Merge the parallel work in src/runtime_bridge.ts',
      '',
      '**Parallel Batch 1.1**',
      '',
      '- `T002`',
      '- `T003`',
      '',
      '**Join Point 1.1**: integrate batch before T004',
      '',
    ].join('\n'),
  );
  writeFile(
    configPath,
    [
      'concurrency: 2',
      'max_fix_attempts: 3',
      'sandbox:',
      '  worktree_dir: ".specify/agent-teams/worktrees"',
      '  state_dir: ".specify/agent-teams/state"',
      '  tmux_prefix: "sp-team-"',
      '',
    ].join('\n'),
  );
  writeFile(
    fakeRuntimePath,
    [
      'import { readFileSync, writeFileSync } from "node:fs";',
      'const chunks = [];',
      'for await (const chunk of process.stdin) chunks.push(chunk);',
      'writeFileSync(process.env.RUNTIME_CAPTURE_PATH, Buffer.concat(chunks).toString("utf8"));',
      'writeFileSync(process.env.RUNTIME_ENV_PATH, JSON.stringify({',
      '  OMX_TEAM_STATE_ROOT: process.env.OMX_TEAM_STATE_ROOT,',
      '  OMX_TEAM_WORKER_CLI_MAP: process.env.OMX_TEAM_WORKER_CLI_MAP ?? "",',
      '  CODEX_HOME: process.env.CODEX_HOME ?? "",',
      '  PATH: process.env.PATH ?? "",',
      '}, null, 2));',
      'process.stdout.write(JSON.stringify({',
      '  status: "completed",',
      '  teamName: "captured-team",',
      '  taskResults: [],',
      '  duration: 0,',
      '  workerCount: 2,',
      '}));',
      '',
    ].join('\n'),
  );
  writeFile(
    sourceConfigPath,
    [
      'model_provider = "OpenAI"',
      'model = "gpt-5.4"',
      '',
      '[model_providers.OpenAI]',
      'name = "OpenAI"',
      'base_url = "https://example.invalid"',
      'wire_api = "responses"',
      'requires_openai_auth = true',
      '',
    ].join('\n'),
  );
  writeFile(
    sourceOmxConfigPath,
    JSON.stringify({
      env: {
        OMX_DEFAULT_FRONTIER_MODEL: 'gpt-5.4',
      },
      models: {
        team: 'gpt-5.4',
      },
    }, null, 2),
  );

  const result = spawnSync(
    process.execPath,
    [bridgePath, '--spec', join(featureDir, 'spec.md'), '--tasks', join(featureDir, 'tasks.md')],
    {
      cwd: projectRoot,
      encoding: 'utf8',
      env: {
        ...process.env,
        AGENT_TEAMS_RUNTIME_CLI: fakeRuntimePath,
        RUNTIME_CAPTURE_PATH: runtimeCapturePath,
        RUNTIME_ENV_PATH: runtimeEnvPath,
        CODEX_HOME: sourceCodexHome,
      },
    },
  );

  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.equal(existsSync(runtimeCapturePath), true, 'runtime-cli should receive stdin JSON');
  assert.equal(existsSync(runtimeEnvPath), true, 'runtime-cli should receive extension env');

  const runtimeInput = JSON.parse(readFileSync(runtimeCapturePath, 'utf8'));
  const runtimeEnv = JSON.parse(readFileSync(runtimeEnvPath, 'utf8'));

  assert.equal(runtimeInput.workerCount, 2);
  assert.equal(Array.isArray(runtimeInput.tasks), true);
  assert.equal(runtimeInput.tasks.length, 4);

  const bySubject = new Map(runtimeInput.tasks.map((task) => [task.subject, task]));
  assert.deepEqual(bySubject.get('T001')?.blocked_by ?? [], []);
  assert.deepEqual(bySubject.get('T002')?.blocked_by ?? [], ['T001']);
  assert.deepEqual(bySubject.get('T003')?.blocked_by ?? [], ['T001']);
  assert.deepEqual(bySubject.get('T004')?.blocked_by ?? [], ['T002', 'T003']);
  assert.equal(runtimeEnv.OMX_TEAM_STATE_ROOT, stateRoot);
  assert.match(runtimeEnv.PATH, new RegExp(engineBinDir.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  assert.equal(runtimeEnv.CODEX_HOME.startsWith(projectRoot), false, 'runtime CODEX_HOME should not live inside the project workspace');
  assert.equal(existsSync(join(runtimeEnv.CODEX_HOME, 'skills', 'worker', 'SKILL.md')), true);
  assert.equal(
    readFileSync(join(runtimeEnv.CODEX_HOME, 'config.toml'), 'utf8'),
    readFileSync(sourceConfigPath, 'utf8'),
    'runtime CODEX_HOME should inherit config.toml from the source CODEX_HOME',
  );
  assert.equal(
    readFileSync(join(runtimeEnv.CODEX_HOME, '.omx-config.json'), 'utf8'),
    readFileSync(sourceOmxConfigPath, 'utf8'),
    'runtime CODEX_HOME should inherit .omx-config.json from the source CODEX_HOME',
  );

  const ledgerDir = join(stateRoot, 'team', 'default', 'tasks');
  const t002 = JSON.parse(readFileSync(join(ledgerDir, 'T002.json'), 'utf8'));
  const t004 = JSON.parse(readFileSync(join(ledgerDir, 'T004.json'), 'utf8'));
  assert.deepEqual(t002.depends_on, ['T001']);
  assert.deepEqual(t004.depends_on, ['T002', 'T003']);
  assert.equal(t002.input.context_files[0], join(featureDir, 'spec.md'));

  assert.equal(
    existsSync(join(projectRoot, '.codex', 'skills', 'worker', 'SKILL.md')),
    false,
    'bridge should not dirty the project workspace by seeding worker assets into .codex',
  );
  assert.equal(
    existsSync(join(projectRoot, '.codex', 'prompts', 'executor.md')),
    false,
    'extension should not expose upstream prompt bundles into project-local .codex',
  );
  assert.equal(
    existsSync(join(projectRoot, '.specify', 'project-map', 'spec.md')),
    false,
    'bridge should not create compatibility spec files that dirty the leader workspace before runtime start',
  );
});
