import { spawnSync } from 'node:child_process';

const build = spawnSync('npm', ['run', 'build'], { encoding: 'utf-8' });
if (build.stdout) process.stderr.write(build.stdout);
if (build.stderr) process.stderr.write(build.stderr);
if (build.status !== 0) {
  process.stdout.write(JSON.stringify({ pass: false }));
  process.exit(build.status ?? 1);
}

const testArgs = [
  '--test',
  'dist/cli/__tests__/autoresearch.test.js',
  'dist/cli/__tests__/index.test.js',
  'dist/cli/__tests__/nested-help-routing.test.js',
  'dist/cli/__tests__/session-search-help.test.js',
  'dist/autoresearch/__tests__/contracts.test.js',
  'dist/autoresearch/__tests__/runtime.test.js',
  'dist/team/__tests__/worktree.test.js',
  'dist/modes/__tests__/base-autoresearch-contract.test.js',
];
const test = spawnSync('node', testArgs, { encoding: 'utf-8' });
if (test.stdout) process.stderr.write(test.stdout);
if (test.stderr) process.stderr.write(test.stderr);
process.stdout.write(JSON.stringify({ pass: test.status === 0 }));
process.exit(test.status ?? 1);
