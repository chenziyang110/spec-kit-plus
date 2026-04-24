import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { homedir, tmpdir } from 'node:os';
import { basename, delimiter, dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const engineRoot = resolve(__dirname, '..', '..');

const DEFAULT_CONFIG = {
  concurrency: 3,
  max_fix_attempts: 3,
  worker_cli: '',
  worker_launch_mode: '',
  sandbox: {
    worktree_dir: '.specify/agent-teams/worktrees',
    state_dir: '.specify/agent-teams/state',
    tmux_prefix: 'sp-team-',
  },
};

const TASK_LINE_RE = /^- \[(?<mark>[ xX])\] (?<taskId>T\d+)(?<rest>.*)$/;
const PARALLEL_BATCH_RE = /^\*\*(?<name>Parallel Batch [^*]+)\*\*$/;
const JOIN_POINT_RE = /^\*\*(?<name>Join Point [^*]+)\*\*/;
const INLINE_TASK_ID_RE = /`(T\d+)`/g;

function parseArgs(argv) {
  const result = {
    specFile: '',
    tasksFile: '',
    configFile: '',
    teamName: process.env.AGENT_TEAMS_TEAM_NAME || 'default',
  };

  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index];
    if (current === '--spec') result.specFile = argv[index + 1] || '';
    if (current === '--tasks') result.tasksFile = argv[index + 1] || '';
    if (current === '--config') result.configFile = argv[index + 1] || '';
    if (current === '--team-name') result.teamName = argv[index + 1] || result.teamName;
  }

  if (!result.specFile || !result.tasksFile) {
    throw new Error('Usage: node bridge.js --spec <spec.md> --tasks <tasks.md> [--config <agent-teams-config.yml>]');
  }

  return result;
}

function resolveProjectRoot(specFile, tasksFile) {
  const taskAbs = resolve(tasksFile);
  const specAbs = resolve(specFile);
  const commonRoot = resolve(dirname(taskAbs), '..', '..');

  if (existsSync(resolve(commonRoot, '.specify'))) return commonRoot;
  if (existsSync(resolve(dirname(specAbs), '..', '..', '.specify'))) return resolve(dirname(specAbs), '..', '..');
  return process.cwd();
}

function ensureGitExcludePatterns(projectRoot, patterns) {
  const excludePath = resolve(projectRoot, '.git', 'info', 'exclude');
  if (!existsSync(dirname(excludePath))) return;

  const existing = existsSync(excludePath) ? readFileSync(excludePath, 'utf8') : '';
  const lines = new Set(existing.split(/\r?\n/).filter(Boolean));
  let changed = false;
  for (const pattern of patterns) {
    if (lines.has(pattern)) continue;
    lines.add(pattern);
    changed = true;
  }
  if (!changed) return;

  const next = `${[...lines].join('\n')}\n`;
  writeFileSync(excludePath, next, 'utf8');
}

function loadConfig(projectRoot, explicitConfigFile) {
  const configPath = explicitConfigFile
    ? resolve(projectRoot, explicitConfigFile)
    : resolve(projectRoot, '.specify', 'extensions', 'agent-teams', 'agent-teams-config.yml');

  if (!existsSync(configPath)) {
    return {
      configPath,
      config: DEFAULT_CONFIG,
    };
  }

  const raw = yaml.load(readFileSync(configPath, 'utf8'));
  const sandbox = {
    ...DEFAULT_CONFIG.sandbox,
    ...((raw && typeof raw === 'object' && raw.sandbox) || {}),
  };

  return {
    configPath,
    config: {
      ...DEFAULT_CONFIG,
      ...(raw && typeof raw === 'object' ? raw : {}),
      sandbox,
    },
  };
}

function normalizeSummary(rest) {
  return rest
    .replace(/\[P\]/g, '')
    .replace(/\[AGENT\]/g, '')
    .replace(/\[US\d+\]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function inferRole(summary) {
  const lowered = summary.toLowerCase();
  if (/\b(test|pytest|vitest|jest|coverage|verification)\b/.test(lowered)) return 'test-engineer';
  if (/\b(ui|ux|css|design|layout|frontend|component)\b/.test(lowered)) return 'designer';
  if (/\b(debug|diagnose|root cause|fix build|build fix|compile)\b/.test(lowered)) return 'debugger';
  if (/\b(doc|readme|guide|changelog|documentation)\b/.test(lowered)) return 'writer';
  if (/\b(security|auth|xss|csrf|vulnerability)\b/.test(lowered)) return 'security-reviewer';
  return 'executor';
}

function parseTasksMarkdown(tasksPath) {
  const tasks = [];
  const batches = [];
  let currentBatch = null;

  for (const rawLine of readFileSync(tasksPath, 'utf8').split(/\r?\n/)) {
    const line = rawLine.trim();
    const taskMatch = line.match(TASK_LINE_RE);
    if (taskMatch) {
      tasks.push({
        id: taskMatch.groups.taskId,
        completed: taskMatch.groups.mark.toLowerCase() === 'x',
        summary: normalizeSummary(taskMatch.groups.rest),
        orderIndex: tasks.length,
      });
      continue;
    }

    const batchMatch = line.match(PARALLEL_BATCH_RE);
    if (batchMatch) {
      currentBatch = {
        id: `batch-${batches.length + 1}`,
        name: batchMatch.groups.name,
        taskIds: [],
        joinPointName: '',
      };
      batches.push(currentBatch);
      continue;
    }

    if (!currentBatch) continue;

    const joinMatch = line.match(JOIN_POINT_RE);
    if (joinMatch) {
      currentBatch.joinPointName = joinMatch.groups.name;
      currentBatch = null;
      continue;
    }

    const taskIds = [...line.matchAll(INLINE_TASK_ID_RE)].map((match) => match[1]);
    if (taskIds.length > 0) currentBatch.taskIds.push(...taskIds);
  }

  return { tasks, batches };
}

function buildDependencies(parsed) {
  const taskMap = new Map(parsed.tasks.map((task) => [task.id, task]));
  const batchByTaskId = new Map();
  for (const batch of parsed.batches) {
    for (const taskId of batch.taskIds) batchByTaskId.set(taskId, batch);
  }

  const dependencies = new Map();
  let currentGate = [];
  let currentBatchId = '';

  for (const task of parsed.tasks) {
    const batch = batchByTaskId.get(task.id);
    if (batch) {
      if (currentBatchId !== batch.id) {
        const batchTaskIds = batch.taskIds.filter((taskId) => taskMap.has(taskId) && !taskMap.get(taskId).completed);
        for (const batchTaskId of batchTaskIds) {
          dependencies.set(batchTaskId, [...currentGate]);
        }
        currentGate = batchTaskIds;
        currentBatchId = batch.id;
      }
      continue;
    }

    currentBatchId = '';
    dependencies.set(task.id, [...currentGate]);
    if (!task.completed) {
      currentGate = [task.id];
    }
  }

  return dependencies;
}

function copyMissingTree(sourceRoot, destinationRoot) {
  if (!existsSync(sourceRoot)) return;

  const queue = [{ source: sourceRoot, destination: destinationRoot }];
  while (queue.length > 0) {
    const current = queue.pop();
    const stats = statSync(current.source);
    if (stats.isDirectory()) {
      mkdirSync(current.destination, { recursive: true });
      for (const entry of readdirSync(current.source)) {
        queue.push({
          source: join(current.source, entry),
          destination: join(current.destination, entry),
        });
      }
      continue;
    }

    if (!existsSync(current.destination)) {
      mkdirSync(dirname(current.destination), { recursive: true });
      cpSync(current.source, current.destination);
    }
  }
}

function syncOptionalFile(sourcePath, destinationPath) {
  if (!existsSync(sourcePath)) return;
  mkdirSync(dirname(destinationPath), { recursive: true });
  cpSync(sourcePath, destinationPath);
}

function resolveSourceCodexHome() {
  const explicit = process.env.CODEX_HOME?.trim();
  if (explicit) return resolve(explicit);
  return resolve(homedir(), '.codex');
}

function ensureRuntimeCodexHome(projectRoot) {
  const hash = createHash('sha256').update(projectRoot).digest('hex').slice(0, 12);
  const codexHomeRoot = resolve(tmpdir(), 'sp-teams-codex-home', hash);
  const sourceCodexHome = resolveSourceCodexHome();
  copyMissingTree(join(engineRoot, 'skills', 'worker'), join(codexHomeRoot, 'skills', 'worker'));
  syncOptionalFile(join(sourceCodexHome, 'config.toml'), join(codexHomeRoot, 'config.toml'));
  syncOptionalFile(join(sourceCodexHome, '.omx-config.json'), join(codexHomeRoot, '.omx-config.json'));
  return codexHomeRoot;
}

function buildTaskDescription(task, specFile, projectMapSpec) {
  const lines = [
    `Task ${task.id}: ${task.summary}`,
    '',
    'Context files:',
    `- ${specFile}`,
  ];
  if (projectMapSpec && projectMapSpec !== specFile) {
    lines.push(`- ${projectMapSpec}`);
  }
  return lines.join('\n');
}

function writeLedger(projectRoot, stateRoot, teamName, parsed, dependencies, specFile, projectMapSpec) {
  const ledgerDir = resolve(projectRoot, stateRoot, 'team', teamName, 'tasks');
  mkdirSync(ledgerDir, { recursive: true });

  for (const task of parsed.tasks) {
    const payload = {
      id: task.id,
      role: inferRole(task.summary),
      status: task.completed ? 'completed' : 'pending',
      depends_on: dependencies.get(task.id) || [],
      input: {
        description: buildTaskDescription(task, specFile, projectMapSpec),
        context_files: [specFile],
      },
      output: {
        artifact_path: '',
      },
    };
    writeFileSync(join(ledgerDir, `${task.id}.json`), JSON.stringify(payload, null, 2), 'utf8');
  }

  return ledgerDir;
}

function buildRuntimePayload(parsed, dependencies, specFile, projectMapSpec, teamName, workerCount, projectRoot) {
  const tasks = parsed.tasks
    .filter((task) => !task.completed)
    .map((task) => ({
      subject: task.id,
      description: buildTaskDescription(task, specFile, projectMapSpec),
      blocked_by: dependencies.get(task.id) || [],
      role: inferRole(task.summary),
    }));

  return {
    teamName,
    workerCount: Math.max(1, Math.min(workerCount, tasks.length || workerCount)),
    agentTypes: Array.from({ length: Math.max(1, Math.min(workerCount, tasks.length || workerCount)) }, () => 'codex'),
    tasks,
    cwd: projectRoot,
    pollIntervalMs: 2500,
  };
}

function resolveRuntimeCliPath() {
  const override = process.env.AGENT_TEAMS_RUNTIME_CLI?.trim();
  if (override) return isAbsolute(override) ? override : resolve(process.cwd(), override);
  return resolve(engineRoot, 'dist', 'team', 'runtime-cli.js');
}

function runRuntime(projectRoot, stateRoot, runtimePayload, codexHome) {
  const runtimeCliPath = resolveRuntimeCliPath();
  const engineBinDir = resolve(engineRoot, 'bin');
  if (!existsSync(runtimeCliPath)) {
    throw new Error(`runtime-cli is unavailable: ${runtimeCliPath}`);
  }

  const result = spawnSync(
    process.execPath,
    [runtimeCliPath],
    {
      cwd: projectRoot,
      input: JSON.stringify(runtimePayload),
      encoding: 'utf8',
      env: {
        ...process.env,
        OMX_TEAM_STATE_ROOT: stateRoot,
        SP_TEAMS_STATE_ROOT: stateRoot,
        OMX_TEAM_SKIP_READY_WAIT: '1',
        SP_TEAMS_SKIP_STARTUP_EVIDENCE: '1',
        OMX_TEAM_DISABLE_HUD: '1',
        SP_TEAMS_DISABLE_HUD: '1',
        OMX_TEAM_WORKER_CLI: process.env.SP_TEAMS_WORKER_CLI || process.env.OMX_TEAM_WORKER_CLI || runtimePayload.workerCli || '',
        OMX_TEAM_WORKER_LAUNCH_MODE: process.env.SP_TEAMS_WORKER_LAUNCH_MODE || process.env.OMX_TEAM_WORKER_LAUNCH_MODE || runtimePayload.workerLaunchMode || '',
        CODEX_HOME: codexHome,
        PATH: `${engineBinDir}${delimiter}${process.env.PATH || ''}`,
      },
    },
  );

  if (result.status !== 0) {
    const stderr = result.stderr?.trim() || result.stdout?.trim() || 'runtime-cli exited non-zero';
    throw new Error(stderr);
  }

  if (result.stdout?.trim()) {
    console.log(result.stdout.trim());
  }
}

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const specFile = resolve(args.specFile);
    const tasksFile = resolve(args.tasksFile);
    const projectRoot = resolveProjectRoot(specFile, tasksFile);
    ensureGitExcludePatterns(projectRoot, ['.omx/', '.codex/', '.specify/agent-teams/']);
    const { config } = loadConfig(projectRoot, args.configFile);
    const stateRoot = resolve(projectRoot, config.sandbox.state_dir);
    const codexHome = ensureRuntimeCodexHome(projectRoot);
    const projectMapSpec = '';
    const parsed = parseTasksMarkdown(tasksFile);
    const dependencies = buildDependencies(parsed);

    writeLedger(projectRoot, config.sandbox.state_dir, args.teamName, parsed, dependencies, specFile, projectMapSpec);

    const runtimePayload = buildRuntimePayload(
      parsed,
      dependencies,
      specFile,
      projectMapSpec,
      args.teamName,
      Number(config.concurrency) || DEFAULT_CONFIG.concurrency,
      projectRoot,
    );
    runtimePayload.workerCli = typeof config.worker_cli === 'string' ? config.worker_cli.trim() : '';
    runtimePayload.workerLaunchMode = typeof config.worker_launch_mode === 'string' ? config.worker_launch_mode.trim() : '';

    mkdirSync(stateRoot, { recursive: true });
    writeFileSync(join(stateRoot, 'runtime-input.json'), JSON.stringify(runtimePayload, null, 2), 'utf8');

    runRuntime(projectRoot, stateRoot, runtimePayload, codexHome);
  } catch (error) {
    console.error(`agent-teams bridge: ${error instanceof Error ? error.message : String(error)}`);
    process.exit(1);
  }
}

if (import.meta.url === `file://${process.argv[1]?.replace(/\\/g, '/')}` || process.argv[1] === __filename) {
  main();
}
