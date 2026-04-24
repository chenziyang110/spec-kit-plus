#!/usr/bin/env node
import { spawnSync } from 'node:child_process';

const checks: [string, string[]][] = [
  ['node', ['--test', 'dist/mcp/__tests__/path-traversal.test.js']],
  ['node', ['--test', 'dist/mcp/__tests__/state-paths.test.js']],
];

function run(command: string, args: string[]) {
  const result = spawnSync(command, args, {
    encoding: 'utf-8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  return {
    command: [command, ...args].join(' '),
    status: result.status ?? 1,
    stdout: (result.stdout || '').trim(),
    stderr: (result.stderr || '').trim(),
  };
}

const build = run('npm', ['run', 'build']);
const results = [build, ...checks.map(([command, args]) => run(command, args))];
const passed = results.filter((result) => result.status === 0).length;
const score = Number((passed / results.length).toFixed(2));
const pass = results.every((result) => result.status === 0);

console.log(JSON.stringify({
  pass,
  score,
  summary: 'Security path-traversal pilot evaluator',
  details: results.map(({ command, status, stderr }) => ({
    command,
    ok: status === 0,
    status,
    stderr: stderr || undefined,
  })),
}));
