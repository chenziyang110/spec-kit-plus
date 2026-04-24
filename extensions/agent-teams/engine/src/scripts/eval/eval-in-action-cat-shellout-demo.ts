import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const source = readFileSync('src/cli/autoresearch.ts', 'utf-8');
const stillUsesCatShellout = /execFileSync\('cat',\s*\[runtime\.manifestFile\]/.test(source);

if (stillUsesCatShellout) {
  process.stderr.write('Evaluator: src/cli/autoresearch.ts still shells out to cat for the manifest.\n');
  process.stdout.write(JSON.stringify({ pass: false, score: 0 }));
  process.exit(1);
}

const build = spawnSync('npm', ['run', 'build'], { encoding: 'utf-8' });
if (build.stdout) process.stderr.write(build.stdout);
if (build.stderr) process.stderr.write(build.stderr);
if (build.status !== 0) {
  process.stdout.write(JSON.stringify({ pass: false, score: 0 }));
  process.exit(build.status ?? 1);
}

const test = spawnSync('node', [
  '--test',
  'dist/cli/__tests__/autoresearch.test.js',
  'dist/autoresearch/__tests__/runtime.test.js',
], { encoding: 'utf-8' });
if (test.stdout) process.stderr.write(test.stdout);
if (test.stderr) process.stderr.write(test.stderr);

const pass = test.status === 0;
process.stdout.write(JSON.stringify({ pass, score: pass ? 1 : 0 }));
process.exit(test.status ?? 1);
