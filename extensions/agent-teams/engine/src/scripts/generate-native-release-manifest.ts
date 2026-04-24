#!/usr/bin/env node
import { readFileSync, writeFileSync, statSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';

function usage(): void {
  console.error('Usage: node scripts/generate-native-release-manifest.mjs --plan <path> --artifacts-dir <dir> --out <path> --release-base-url <url> [--require-products a,b]');
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

function parseChecksum(raw: string): string {
  return String(raw).trim().split(/\s+/)[0];
}

interface TripleMapping {
  platform: string;
  arch: string;
  libc?: string;
}

function mapTriple(triple: string): TripleMapping | undefined {
  switch (triple) {
    case 'x86_64-unknown-linux-gnu': return { platform: 'linux', arch: 'x64', libc: 'glibc' };
    case 'aarch64-unknown-linux-gnu': return { platform: 'linux', arch: 'arm64', libc: 'glibc' };
    case 'x86_64-unknown-linux-musl': return { platform: 'linux', arch: 'x64', libc: 'musl' };
    case 'aarch64-unknown-linux-musl': return { platform: 'linux', arch: 'arm64', libc: 'musl' };
    case 'x86_64-apple-darwin': return { platform: 'darwin', arch: 'x64' };
    case 'aarch64-apple-darwin': return { platform: 'darwin', arch: 'arm64' };
    case 'x86_64-pc-windows-msvc': return { platform: 'win32', arch: 'x64' };
    case 'aarch64-pc-windows-msvc': return { platform: 'win32', arch: 'arm64' };
    default: return undefined;
  }
}

const planPath = arg('--plan');
const artifactsDir = arg('--artifacts-dir');
const outPath = arg('--out');
const releaseBaseUrl = arg('--release-base-url');
const requireProducts = (arg('--require-products') || '').split(',').map((value) => value.trim()).filter(Boolean);
if (!planPath || !artifactsDir || !outPath || !releaseBaseUrl) usage();

interface PlanArtifact {
  kind: string;
  name: string;
  checksum: string;
  target_triples?: string[];
  assets?: Array<{ kind: string; name: string; path: string; id?: string }>;
}

interface PlanRelease {
  app_name: string;
  app_version: string;
}

interface Plan {
  artifacts: Record<string, PlanArtifact>;
  releases: PlanRelease[];
  announcement_tag: string;
}

interface ManifestAsset {
  product: string;
  version: string;
  platform: string;
  arch: string;
  target: string;
  libc?: string;
  archive: string;
  binary: string;
  binary_path: string;
  sha256: string;
  size: number;
  download_url: string;
}

const plan = JSON.parse(readFileSync(resolve(planPath!), 'utf-8')) as Plan;
const files = walk(resolve(artifactsDir!));
const byName = new Map(files.map((file) => [file.split('/').pop()!, file]));
const assets: ManifestAsset[] = [];

for (const artifact of Object.values(plan.artifacts)) {
  if (artifact.kind !== 'executable-zip') continue;
  const triple = artifact.target_triples?.[0];
  const mapped = triple ? mapTriple(triple) : undefined;
  if (!mapped) continue;
  const executable = (artifact.assets || []).find((asset) => asset.kind === 'executable');
  if (!executable) continue;
  const archivePath = byName.get(artifact.name);
  const checksumPath = byName.get(artifact.checksum);
  if (!archivePath || !checksumPath) {
    throw new Error(`missing artifact files for ${artifact.name}`);
  }

  const release = plan.releases.find((item) => item.app_name === executable.name || item.app_name === executable.id?.split('-exe-')[0]);
  const version = release?.app_version || plan.announcement_tag.replace(/^v/, '');
  assets.push({
    product: executable.name,
    version,
    platform: mapped.platform,
    arch: mapped.arch,
    target: triple!,
    ...(mapped.libc ? { libc: mapped.libc } : {}),
    archive: artifact.name,
    binary: executable.name,
    binary_path: executable.path,
    sha256: parseChecksum(readFileSync(checksumPath, 'utf-8')),
    size: statSync(archivePath).size,
    download_url: `${releaseBaseUrl!.replace(/\/$/, '')}/${artifact.name}`,
  });
}

const manifest = {
  manifest_version: 1,
  version: plan.announcement_tag.replace(/^v/, ''),
  tag: plan.announcement_tag,
  generated_at: new Date().toISOString(),
  assets: assets.sort((a, b) => {
    const keyCompare = `${a.product}-${a.platform}-${a.arch}`.localeCompare(`${b.product}-${b.platform}-${b.arch}`);
    if (keyCompare !== 0) return keyCompare;
    const libcOrder: Record<string, number> = { musl: 0, glibc: 1 };
    const libcCompare = (libcOrder[a.libc ?? ''] ?? 2) - (libcOrder[b.libc ?? ''] ?? 2);
    if (libcCompare !== 0) return libcCompare;
    return a.archive.localeCompare(b.archive);
  }),
};
for (const product of requireProducts) {
  if (!manifest.assets.some((asset) => asset.product === product)) {
    throw new Error(`missing required product in release manifest: ${product}`);
  }
}
writeFileSync(resolve(outPath!), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(resolve(outPath!));
