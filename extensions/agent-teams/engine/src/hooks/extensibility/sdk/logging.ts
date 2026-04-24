import { appendFile, mkdir } from 'fs/promises';
import { dirname } from 'path';
import type { HookEventEnvelope, HookPluginSdk } from '../types.js';
import { hookPluginLogPath } from './paths.js';

type HookPluginLogLevel = 'info' | 'warn' | 'error';

export async function appendHookPluginLog(
  cwd: string,
  pluginName: string,
  level: HookPluginLogLevel,
  message: string,
  meta: Record<string, unknown>,
): Promise<void> {
  const logPath = hookPluginLogPath(cwd);
  await mkdir(dirname(logPath), { recursive: true });
  await appendFile(logPath, `${JSON.stringify({
    timestamp: new Date().toISOString(),
    type: 'hook_plugin_log',
    plugin: pluginName,
    level,
    message,
    ...meta,
  })}\n`).catch(() => {});
}

export function createHookPluginLogger(
  cwd: string,
  pluginName: string,
  event: HookEventEnvelope,
): HookPluginSdk['log'] {
  return {
    info: (message: string, meta: Record<string, unknown> = {}) => appendHookPluginLog(cwd, pluginName, 'info', message, {
      hook_event: event.event,
      ...meta,
    }),
    warn: (message: string, meta: Record<string, unknown> = {}) => appendHookPluginLog(cwd, pluginName, 'warn', message, {
      hook_event: event.event,
      ...meta,
    }),
    error: (message: string, meta: Record<string, unknown> = {}) => appendHookPluginLog(cwd, pluginName, 'error', message, {
      hook_event: event.event,
      ...meta,
    }),
  };
}
