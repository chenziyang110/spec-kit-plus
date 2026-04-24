import { spawnSync } from 'node:child_process';
const result = spawnSync('node', ['--test', 'dist/cli/__tests__/autoresearch.test.js', 'dist/autoresearch/__tests__/runtime.test.js'], {
  encoding: 'utf-8',
});
process.stdout.write(JSON.stringify({ pass: result.status === 0 }));
if (result.stdout) process.stderr.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
process.exit(result.status ?? 1);
