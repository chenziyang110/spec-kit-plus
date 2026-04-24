import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync, realpathSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import {
  AUTORESEARCH_DEPRECATION_MESSAGE,
  autoresearchCommand,
  normalizeAutoresearchCodexArgs,
  parseAutoresearchArgs,
} from '../autoresearch.js';

function runOmx(
  cwd: string,
  argv: string[],
  envOverrides: Record<string, string> = {},
): { status: number | null; stdout: string; stderr: string; error?: string } {
  const testDir = dirname(fileURLToPath(import.meta.url));
  const repoRoot = join(testDir, '..', '..', '..');
  const omxBin = join(repoRoot, 'dist', 'cli', 'omx.js');
  const result = spawnSync(process.execPath, [omxBin, ...argv], {
    cwd,
    encoding: 'utf-8',
    env: {
      ...process.env,
      OMX_AUTO_UPDATE: '0',
      OMX_NOTIFY_FALLBACK: '0',
      OMX_HOOK_DERIVED_SIGNALS: '0',
      ...envOverrides,
    },
  });
  return { status: result.status, stdout: result.stdout || '', stderr: result.stderr || '', error: result.error?.message };
}

async function initRepo(): Promise<string> {
  const raw = await mkdtemp(join(tmpdir(), 'omx-autoresearch-test-'));
  const cwd = realpathSync(raw);
  execFileSync('git', ['init'], { cwd, stdio: 'ignore' });
  execFileSync('git', ['config', 'user.email', 'test@example.com'], { cwd, stdio: 'ignore' });
  execFileSync('git', ['config', 'user.name', 'Test User'], { cwd, stdio: 'ignore' });
  await writeFile(join(cwd, 'README.md'), 'hello\n', 'utf-8');
  execFileSync('git', ['add', 'README.md'], { cwd, stdio: 'ignore' });
  execFileSync('git', ['commit', '-m', 'init'], { cwd, stdio: 'ignore' });
  return cwd;
}

describe('normalizeAutoresearchCodexArgs', () => {
  it('adds sandbox bypass by default for autoresearch workers', () => {
    assert.deepEqual(normalizeAutoresearchCodexArgs(['--model', 'gpt-5']), ['--model', 'gpt-5', '--dangerously-bypass-approvals-and-sandbox']);
  });

  it('deduplicates explicit bypass flags', () => {
    assert.deepEqual(normalizeAutoresearchCodexArgs(['--dangerously-bypass-approvals-and-sandbox']), ['--dangerously-bypass-approvals-and-sandbox']);
  });

  it('normalizes --madmax to the canonical bypass flag', () => {
    assert.deepEqual(normalizeAutoresearchCodexArgs(['--madmax']), ['--dangerously-bypass-approvals-and-sandbox']);
  });
});

describe('parseAutoresearchArgs', () => {
  it('treats top-level topic/evaluator flags as seeded deep-interview input', () => {
    const parsed = parseAutoresearchArgs(['--topic', 'Improve docs', '--evaluator', 'node eval.js', '--slug', 'docs-run']);
    assert.equal(parsed.guided, true);
    assert.equal(parsed.seedArgs?.topic, 'Improve docs');
    assert.equal(parsed.seedArgs?.evaluatorCommand, 'node eval.js');
    assert.equal(parsed.seedArgs?.slug, 'docs-run');
  });

  it('treats bare init as guided alias and init with flags as expert init args', () => {
    const bare = parseAutoresearchArgs(['init']);
    assert.equal(bare.guided, true);
    assert.deepEqual(bare.initArgs, []);

    const flagged = parseAutoresearchArgs(['init', '--topic', 'Ship feature']);
    assert.equal(flagged.guided, true);
    assert.deepEqual(flagged.initArgs, ['--topic', 'Ship feature']);
  });

  it('parses explicit run subcommand without breaking bare mission-dir parsing', () => {
    const runParsed = parseAutoresearchArgs(['run', 'missions/demo', '--model', 'gpt-5']);
    assert.equal(runParsed.runSubcommand, true);
    assert.equal(runParsed.missionDir, 'missions/demo');
    assert.deepEqual(runParsed.codexArgs, ['--model', 'gpt-5']);

    const bareParsed = parseAutoresearchArgs(['missions/demo', '--model', 'gpt-5']);
    assert.equal(bareParsed.runSubcommand, undefined);
    assert.equal(bareParsed.missionDir, 'missions/demo');
    assert.deepEqual(bareParsed.codexArgs, ['--model', 'gpt-5']);
  });
});

describe('omx autoresearch hard deprecation', () => {
  it('documents autoresearch as deprecated in top-level help', async () => {
    const cwd = await mkdtemp(join(tmpdir(), 'omx-autoresearch-help-'));
    try {
      const result = runOmx(cwd, ['--help']);
      assert.equal(result.status, 0, result.stderr || result.stdout);
      assert.match(result.stdout, /omx autoresearch\s+\[DEPRECATED\] Use \$autoresearch; direct CLI launch removed/i);
    } finally {
      await rm(cwd, { recursive: true, force: true });
    }
  });

  it('routes autoresearch --help to local deprecation help', async () => {
    const cwd = await mkdtemp(join(tmpdir(), 'omx-autoresearch-local-help-'));
    try {
      const result = runOmx(cwd, ['autoresearch', '--help']);
      assert.equal(result.status, 0, result.stderr || result.stdout);
      assert.match(result.stdout, /hard-deprecated legacy command surface/i);
      assert.match(result.stdout, /\$deep-interview --autoresearch/i);
      assert.match(result.stdout, /\$autoresearch/i);
      assert.match(result.stdout, /prompt-architect-artifact/i);
      assert.doesNotMatch(result.stdout, /oh-my-codex \(omx\) - Multi-agent orchestration for Codex CLI/i);
    } finally {
      await rm(cwd, { recursive: true, force: true });
    }
  });

  for (const argv of [
    ['autoresearch'],
    ['autoresearch', 'init'],
    ['autoresearch', 'run', 'missions/demo'],
    ['autoresearch', 'missions/demo'],
    ['autoresearch', '--resume', 'run-123'],
    ['autoresearch', '--topic', 'Flaky onboarding'],
  ]) {
    it(`fails legacy invocation: omx ${argv.join(' ')}`, async () => {
      const cwd = await mkdtemp(join(tmpdir(), 'omx-autoresearch-fail-'));
      try {
        const result = runOmx(cwd, argv);
        assert.notEqual(result.status, 0);
        const output = `${result.stdout}\n${result.stderr}`;
        assert.match(output, /hard-deprecated/i);
        assert.match(output, /\$autoresearch/i);
        assert.match(output, /Direct CLI launch, resume, run, bare mission-dir aliases, and tmux split-pane launch are no longer supported/i);
      } finally {
        await rm(cwd, { recursive: true, force: true });
      }
    });
  }

  it('never invokes codex or tmux on the deprecated path', async () => {
    const cwd = await initRepo();
    const fakeBin = await mkdtemp(join(tmpdir(), 'omx-autoresearch-noexec-bin-'));
    const codexLog = join(cwd, 'codex.log');
    const tmuxLog = join(cwd, 'tmux.log');
    try {
      await writeFile(join(fakeBin, 'codex'), `#!/bin/sh\necho codex >> ${JSON.stringify(codexLog)}\nexit 99\n`, 'utf-8');
      await writeFile(join(fakeBin, 'tmux'), `#!/bin/sh\necho tmux >> ${JSON.stringify(tmuxLog)}\nexit 99\n`, 'utf-8');
      execFileSync('chmod', ['+x', join(fakeBin, 'codex')], { stdio: 'ignore' });
      execFileSync('chmod', ['+x', join(fakeBin, 'tmux')], { stdio: 'ignore' });

      const result = runOmx(cwd, ['autoresearch', 'run', 'missions/demo'], {
        PATH: `${fakeBin}:${process.env.PATH || ''}`,
      });
      assert.notEqual(result.status, 0);
      assert.equal(existsSync(codexLog), false);
      assert.equal(existsSync(tmuxLog), false);
    } finally {
      await rm(cwd, { recursive: true, force: true });
      await rm(fakeBin, { recursive: true, force: true });
    }
  });

  it('throws the same deprecation guidance from the command entrypoint', async () => {
    await assert.rejects(
      async () => autoresearchCommand(['run', 'missions/demo']),
      (error: unknown) => {
        assert.match(String(error), new RegExp(AUTORESEARCH_DEPRECATION_MESSAGE.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
        return true;
      },
    );
  });
});
