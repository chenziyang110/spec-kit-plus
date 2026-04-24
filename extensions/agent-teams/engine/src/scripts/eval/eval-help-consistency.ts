import { spawnSync } from 'node:child_process';

const result = spawnSync('node', ['--test', 'dist/cli/__tests__/session-search-help.test.js'], {
  encoding: 'utf-8',
});

const pass = result.status === 0;
process.stdout.write(JSON.stringify({ pass }));
if (result.stdout) process.stderr.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
process.exit(result.status ?? 1);
