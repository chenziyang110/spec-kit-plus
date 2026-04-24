import { tryReadCatalogManifest } from '../catalog/reader.js';

export interface CatalogExpectations {
  promptMin: number;
  skillMin: number;
}

const SAFETY_BUFFER = 2;

function countInstallablePrompts(manifest: NonNullable<ReturnType<typeof tryReadCatalogManifest>>): number {
  return manifest.agents
    .filter((agent) => agent.status === 'active' || agent.status === 'internal')
    .length;
}

function countInstallableSkills(manifest: NonNullable<ReturnType<typeof tryReadCatalogManifest>>): number {
  return manifest.skills
    .filter((skill) => skill.status === 'active' || skill.status === 'internal')
    .length;
}

export function getCatalogExpectations(): CatalogExpectations {
  const manifest = tryReadCatalogManifest();
  if (!manifest) {
    return { promptMin: 25, skillMin: 30 };
  }

  const installablePromptCount = countInstallablePrompts(manifest);
  const installableSkillCount = countInstallableSkills(manifest);
  return {
    promptMin: Math.max(1, installablePromptCount - SAFETY_BUFFER),
    skillMin: Math.max(1, installableSkillCount - SAFETY_BUFFER),
  };
}

export function getCatalogHeadlineCounts(): { prompts: number; skills: number } | null {
  const manifest = tryReadCatalogManifest();
  if (!manifest) return null;
  return {
    prompts: countInstallablePrompts(manifest),
    skills: countInstallableSkills(manifest),
  };
}
