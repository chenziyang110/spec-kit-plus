import { existsSync } from 'fs';
import { mkdir, readFile, unlink, writeFile } from 'fs/promises';
import { dirname, join } from 'path';
import type { HookPluginSdk } from '../types.js';
import { hookPluginDataPath, hookPluginRootDir, sanitizeHookPluginName } from './paths.js';

async function readJsonIfExists<T>(path: string, fallback: T): Promise<T> {
  if (!existsSync(path)) return fallback;
  try {
    return JSON.parse(await readFile(path, 'utf-8')) as T;
  } catch {
    return fallback;
  }
}

export function normalizeHookPluginStateKey(key: string): string {
  const trimmed = key.trim();
  if (!trimmed) throw new Error('state key is required');
  if (trimmed.includes('..') || trimmed.startsWith('/')) {
    throw new Error('invalid state key');
  }
  return trimmed;
}

export function createHookPluginStateApi(
  cwd: string,
  pluginName: string,
): HookPluginSdk['state'] {
  const dataPath = hookPluginDataPath(cwd, pluginName);

  async function readData(): Promise<Record<string, unknown>> {
    return readJsonIfExists<Record<string, unknown>>(dataPath, {});
  }

  async function writeData(value: Record<string, unknown>): Promise<void> {
    await mkdir(dirname(dataPath), { recursive: true });
    await writeFile(dataPath, JSON.stringify(value, null, 2));
  }

  return {
    read: async <T = unknown>(key: string, fallback?: T): Promise<T | undefined> => {
      const safeKey = normalizeHookPluginStateKey(key);
      const data = await readData();
      if (!(safeKey in data)) return fallback;
      return data[safeKey] as T;
    },
    write: async (key: string, value: unknown): Promise<void> => {
      const safeKey = normalizeHookPluginStateKey(key);
      const data = await readData();
      data[safeKey] = value;
      await writeData(data);
    },
    delete: async (key: string): Promise<void> => {
      const safeKey = normalizeHookPluginStateKey(key);
      const data = await readData();
      if (safeKey in data) {
        delete data[safeKey];
        await writeData(data);
      }
    },
    all: async <T extends Record<string, unknown> = Record<string, unknown>>(): Promise<T> => {
      const data = await readData();
      return data as T;
    },
  };
}

export async function clearHookPluginStateFiles(cwd: string, pluginName: string): Promise<void> {
  const root = hookPluginRootDir(cwd, sanitizeHookPluginName(pluginName));
  await unlink(join(root, 'data.json')).catch(() => {});
  await unlink(join(root, 'tmux.json')).catch(() => {});
}
