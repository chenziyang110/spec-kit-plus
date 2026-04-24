#!/usr/bin/env node
import { readFileSync, statSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';

function usage(): void {
  console.error('Usage: node scripts/verify-native-release-assets.mjs --manifest <path> --artifacts-dir <dir>');
  process.exit(1);
}
function arg(name: string): string | undefined {
  const index = process.argv.indexOf(name);
  if (index === -1) return undefined;
  return process.argv[index + 1];
}
function walk(dir: string): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) files.push(...walk(full));
    else files.push(full);
  }
  return files;
}
function sha256(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex');
}

function archiveContainsBinary(members: string[], binaryPath: string): boolean {
  return members.includes(binaryPath)
    || members.some((member) => member.endsWith(`/${binaryPath}`))
    || members.some((member) => member.replace(/\\/g, '/').endsWith(`/${binaryPath.replace(/\\/g, '/')}`));
}

const manifestPath = arg('--manifest');
const artifactsDir = arg('--artifacts-dir');
if (!manifestPath || !artifactsDir) usage();

interface ManifestAsset {
  archive: string;
  size?: number;
  sha256: string;
  binary_path: string;
}

const manifest = JSON.parse(readFileSync(resolve(manifestPath!), 'utf-8')) as { assets: ManifestAsset[] };
const byName = new Map(walk(resolve(artifactsDir!)).map((file) => [file.split('/').pop()!, file]));

for (const asset of manifest.assets) {
  const archivePath = byName.get(asset.archive);
  if (!archivePath) throw new Error(`missing archive ${asset.archive}`);
  if (typeof asset.size === 'number' && statSync(archivePath).size !== asset.size) {
    throw new Error(`size mismatch for ${asset.archive}`);
  }
  if (sha256(archivePath) !== asset.sha256) {
    throw new Error(`checksum mismatch for ${asset.archive}`);
  }
  const list = asset.archive.endsWith('.zip')
    ? spawnSync('python3', ['-c', 'import sys, zipfile; z=zipfile.ZipFile(sys.argv[1]); print("\\n".join(z.namelist()))', archivePath], { encoding: 'utf-8' })
    : spawnSync('tar', ['-tf', archivePath], { encoding: 'utf-8' });
  if (list.status !== 0) throw new Error(`unable to inspect archive ${asset.archive}: ${list.stderr || list.stdout}`);
  const members = String(list.stdout || '').split(/\r?\n/).filter(Boolean);
  if (!archiveContainsBinary(members, asset.binary_path)) {
    throw new Error(`archive ${asset.archive} is missing ${asset.binary_path}`);
  }
}

console.log(`[native-release-assets] verified ${manifest.assets.length} assets`);
