import { resolve } from 'path';
import { specifyRuntimeStateDir } from '../utils/paths.js';

/**
 * Resolve the canonical team state root for a leader working directory.
 */
export function resolveCanonicalTeamStateRoot(
  leaderCwd: string,
  env: NodeJS.ProcessEnv = process.env,
): string {
  const explicit = env.SPECIFY_TEAM_STATE_ROOT || env.SP_TEAMS_STATE_ROOT;
  if (typeof explicit === 'string' && explicit.trim() !== '') {
    return resolve(leaderCwd, explicit.trim());
  }
  return resolve(specifyRuntimeStateDir(leaderCwd));
}

