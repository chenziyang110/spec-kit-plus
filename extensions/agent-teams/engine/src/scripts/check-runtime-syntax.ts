#!/usr/bin/env node
// @ts-nocheck

import { readdirSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import process from 'node:process';

const root = process.cwd();
const scriptsRoot = join(root, 'scripts');
const includeExtensions = new Set(['.js', '.mjs']);

function shouldCheck(path) {
  return [...includeExtensions].some((ext) => path.endsWith(ext));
}

function walk(dir: string): string[] {
  const entries = readdirSync(dir, { withFileTypes: true })
    .sort((a, b) => a.name.localeCompare(b.name));
  const files = [];
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(fullPath));
      continue;
    }
    if (entry.isFile() && shouldCheck(fullPath)) {
      files.push(fullPath);
    }
  }
  return files;
}

const files = walk(scriptsRoot);
if (files.length === 0) {
  console.error('No script files found under scripts/.');
  process.exit(1);
}

const failures = [];
for (const file of files) {
  const result = spawnSync(process.execPath, ['--check', resolve(file)], {
    cwd: root,
    encoding: 'utf-8',
  });
  if (result.status !== 0) {
    failures.push({
      file: relative(root, file),
      output: (result.stderr || result.stdout || '').trim(),
    });
  }
}

if (failures.length > 0) {
  console.error(`Runtime script syntax check failed for ${failures.length} file(s):`);
  for (const failure of failures) {
    console.error(`\n--- ${failure.file} ---`);
    if (failure.output) console.error(failure.output);
  }
  process.exit(1);
}

console.log(`Syntax OK: checked ${files.length} runtime script file(s).`);
