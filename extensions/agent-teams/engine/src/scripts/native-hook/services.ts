import {
  SharedHookClient,
  type HookProcessRunner,
} from "../../hooks/shared-hook-client.js";
import { NativeHookEffectRecorder } from "./effects.js";

export interface NativeHookServicesOptions {
  cwd: string;
  env?: NodeJS.ProcessEnv;
  effects?: NativeHookEffectRecorder;
  sharedHooks?: SharedHookClient;
  runner?: HookProcessRunner;
  now?: () => number;
}

export interface NativeHookServices {
  effects: NativeHookEffectRecorder;
  sharedHooks: SharedHookClient;
}

export function createNativeHookServices(options: NativeHookServicesOptions): NativeHookServices {
  const effects = options.effects ?? new NativeHookEffectRecorder();
  const sharedHooks = options.sharedHooks ?? new SharedHookClient({
    cwd: options.cwd,
    env: options.env ?? process.env,
    runner: options.runner,
    now: options.now,
  });

  return {
    effects,
    sharedHooks,
  };
}
