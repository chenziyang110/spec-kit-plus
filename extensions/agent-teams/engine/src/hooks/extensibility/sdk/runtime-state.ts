import { existsSync } from 'fs';
import { readFile } from 'fs/promises';
import type {
  HookPluginOmxHudState,
  HookPluginOmxNotifyFallbackState,
  HookPluginOmxSessionState,
  HookPluginOmxUpdateCheckState,
  HookPluginSdk,
} from '../types.js';
import { omxRootStateFilePath } from './paths.js';
import { getReadScopedStateFilePaths } from '../../../mcp/state-paths.js';

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

async function readOmxStateFile<T extends Record<string, unknown>>(
  path: string,
  normalize?: (value: Record<string, unknown>) => T | null,
): Promise<T | null> {
  if (!existsSync(path)) return null;
  try {
    const parsed = JSON.parse(await readFile(path, 'utf-8')) as unknown;
    if (!isRecord(parsed)) return null;
    return normalize ? normalize(parsed) : parsed as T;
  } catch {
    return null;
  }
}

function normalizeSessionState(value: Record<string, unknown>): HookPluginOmxSessionState | null {
  return typeof value.session_id === 'string' && value.session_id.trim()
    ? value as HookPluginOmxSessionState
    : null;
}

export function createHookPluginOmxApi(cwd: string): HookPluginSdk['omx'] {
  return {
    session: {
      read: () => readOmxStateFile<HookPluginOmxSessionState>(
        omxRootStateFilePath(cwd, 'session.json'),
        normalizeSessionState,
      ),
    },
    hud: {
      read: async () => {
        const [hudStatePath] = await getReadScopedStateFilePaths('hud-state.json', cwd, undefined, {
          rootFallback: false,
        });
        return readOmxStateFile<HookPluginOmxHudState>(hudStatePath);
      },
    },
    notifyFallback: {
      read: () => readOmxStateFile<HookPluginOmxNotifyFallbackState>(
        omxRootStateFilePath(cwd, 'notify-fallback-state.json'),
      ),
    },
    updateCheck: {
      read: () => readOmxStateFile<HookPluginOmxUpdateCheckState>(
        omxRootStateFilePath(cwd, 'update-check.json'),
      ),
    },
  };
}
