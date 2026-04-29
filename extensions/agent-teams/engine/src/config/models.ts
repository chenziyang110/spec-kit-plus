/**
 * Model Configuration
 *
 * Reads per-mode model overrides and default-env overrides from .specify-config.json.
 *
 * Config format:
 * {
 *   "env": {
 *     "SPECIFY_DEFAULT_FRONTIER_MODEL": "your-frontier-model",
 *     "SPECIFY_DEFAULT_STANDARD_MODEL": "your-standard-model",
 *     "SPECIFY_DEFAULT_SPARK_MODEL": "your-spark-model"
 *   },
 *   "models": {
 *     "default": "o4-mini",
 *     "team": "gpt-4.1"
 *   }
 * }
 *
 * Resolution: mode-specific > "default" key > SPECIFY_DEFAULT_FRONTIER_MODEL > DEFAULT_FRONTIER_MODEL
 */

import { parse as parseToml } from '@iarna/toml';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { codexConfigPath, codexHome } from '../utils/paths.js';

export interface ModelsConfig {
  [mode: string]: string | undefined;
}

export interface SpecifyConfigEnv {
  [key: string]: string | undefined;
}

interface SpecifyConfigFile {
  env?: SpecifyConfigEnv;
  models?: ModelsConfig;
}

interface CodexConfigFile {
  model?: unknown;
  model_provider?: unknown;
  model_providers?: Record<string, unknown>;
}

export const SPECIFY_DEFAULT_FRONTIER_MODEL_ENV = 'SPECIFY_DEFAULT_FRONTIER_MODEL';
export const SPECIFY_DEFAULT_STANDARD_MODEL_ENV = 'SPECIFY_DEFAULT_STANDARD_MODEL';
export const SPECIFY_DEFAULT_SPARK_MODEL_ENV = 'SPECIFY_DEFAULT_SPARK_MODEL';
export const SPECIFY_SPARK_MODEL_ENV = 'SPECIFY_SPARK_MODEL';

function readSpecifyConfigFile(codexHomeOverride?: string): SpecifyConfigFile | null {
  const configPath = join(codexHomeOverride || codexHome(), '.specify-config.json');
  if (!existsSync(configPath)) return null;
  try {
    const raw = JSON.parse(readFileSync(configPath, 'utf-8'));
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
    return raw as SpecifyConfigFile;
  } catch {
    return null;
  }
}

function readCodexConfigFile(codexHomeOverride?: string): CodexConfigFile | null {
  const configPath = codexHomeOverride
    ? join(codexHomeOverride, 'config.toml')
    : codexConfigPath();
  if (!existsSync(configPath)) return null;
  try {
    const raw = parseToml(readFileSync(configPath, 'utf-8'));
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
    return raw as CodexConfigFile;
  } catch {
    return null;
  }
}

function readModelsBlock(codexHomeOverride?: string): ModelsConfig | null {
  const config = readSpecifyConfigFile(codexHomeOverride);
  if (!config) return null;
  if (config.models && typeof config.models === 'object' && !Array.isArray(config.models)) {
    return config.models;
  }
  return null;
}

export const DEFAULT_FRONTIER_MODEL = 'gpt-5.5';
export const DEFAULT_STANDARD_MODEL = 'gpt-5.4-mini';
export const DEFAULT_SPARK_MODEL = 'gpt-5.3-codex-spark';

function normalizeConfiguredValue(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function readConfigEnvValue(key: string, codexHomeOverride?: string): string | undefined {
  const config = readSpecifyConfigFile(codexHomeOverride);
  if (!config || !config.env || typeof config.env !== 'object' || Array.isArray(config.env)) {
    return undefined;
  }
  return normalizeConfiguredValue(config.env[key]);
}

function readTeamLowComplexityOverride(codexHomeOverride?: string): string | undefined {
  const models = readModelsBlock(codexHomeOverride);
  if (!models) return undefined;
  for (const key of TEAM_LOW_COMPLEXITY_MODEL_KEYS) {
    const value = normalizeConfiguredValue(models[key]);
    if (value) return value;
  }
  return undefined;
}

function readCodexConfiguredMainModel(codexHomeOverride?: string): string | undefined {
  const config = readCodexConfigFile(codexHomeOverride);
  if (!config) return undefined;
  return normalizeConfiguredValue(config.model);
}

export function readConfiguredEnvOverrides(codexHomeOverride?: string): NodeJS.ProcessEnv {
  const config = readSpecifyConfigFile(codexHomeOverride);
  if (!config || !config.env || typeof config.env !== 'object' || Array.isArray(config.env)) {
    return {};
  }

  const resolved: NodeJS.ProcessEnv = {};
  for (const [key, value] of Object.entries(config.env)) {
    const normalized = normalizeConfiguredValue(value);
    if (normalized) resolved[key] = normalized;
  }
  return resolved;
}

export function readActiveProviderEnvOverrides(
  env: NodeJS.ProcessEnv = process.env,
  codexHomeOverride?: string,
): NodeJS.ProcessEnv {
  const config = readCodexConfigFile(codexHomeOverride);
  if (!config) return {};

  const activeProvider = normalizeConfiguredValue(config.model_provider);
  if (!activeProvider) return {};

  const providers = config.model_providers;
  if (!providers || typeof providers !== 'object' || Array.isArray(providers)) {
    return {};
  }

  const providerConfig = providers[activeProvider];
  if (!providerConfig || typeof providerConfig !== 'object' || Array.isArray(providerConfig)) {
    return {};
  }

  const envKey = normalizeConfiguredValue((providerConfig as Record<string, unknown>).env_key);
  if (!envKey) return {};

  const envValue = normalizeConfiguredValue(env[envKey]);
  return envValue ? { [envKey]: envValue } : {};
}

export function getEnvConfiguredMainDefaultModel(
  env: NodeJS.ProcessEnv = process.env,
  codexHomeOverride?: string,
): string | undefined {
  return normalizeConfiguredValue(env[SPECIFY_DEFAULT_FRONTIER_MODEL_ENV])
    ?? readConfigEnvValue(SPECIFY_DEFAULT_FRONTIER_MODEL_ENV, codexHomeOverride);
}

export function getEnvConfiguredStandardDefaultModel(
  env: NodeJS.ProcessEnv = process.env,
  codexHomeOverride?: string,
): string | undefined {
  return normalizeConfiguredValue(env[SPECIFY_DEFAULT_STANDARD_MODEL_ENV])
    ?? readConfigEnvValue(SPECIFY_DEFAULT_STANDARD_MODEL_ENV, codexHomeOverride);
}

export function getEnvConfiguredSparkDefaultModel(
  env: NodeJS.ProcessEnv = process.env,
  codexHomeOverride?: string,
): string | undefined {
  return normalizeConfiguredValue(env[SPECIFY_DEFAULT_SPARK_MODEL_ENV])
    ?? normalizeConfiguredValue(env[SPECIFY_SPARK_MODEL_ENV])
    ?? readConfigEnvValue(SPECIFY_DEFAULT_SPARK_MODEL_ENV, codexHomeOverride)
    ?? readConfigEnvValue(SPECIFY_SPARK_MODEL_ENV, codexHomeOverride);
}

/**
 * Get the envvar-backed main/default model.
 * Resolution: SPECIFY_DEFAULT_FRONTIER_MODEL > config.toml model > DEFAULT_FRONTIER_MODEL
 */
export function getMainDefaultModel(codexHomeOverride?: string): string {
  return getEnvConfiguredMainDefaultModel(process.env, codexHomeOverride)
    ?? readCodexConfiguredMainModel(codexHomeOverride)
    ?? DEFAULT_FRONTIER_MODEL;
}

/**
 * Get the envvar-backed standard/default subagent model.
 * Resolution: SPECIFY_DEFAULT_STANDARD_MODEL > DEFAULT_STANDARD_MODEL
 */
export function getStandardDefaultModel(codexHomeOverride?: string): string {
  return getEnvConfiguredStandardDefaultModel(process.env, codexHomeOverride)
    ?? DEFAULT_STANDARD_MODEL;
}

/**
 * Get the configured model for a specific mode.
 * Resolution: mode-specific override > "default" key > SPECIFY_DEFAULT_FRONTIER_MODEL > DEFAULT_FRONTIER_MODEL
 */
export function getModelForMode(mode: string, codexHomeOverride?: string): string {
  const models = readModelsBlock(codexHomeOverride);
  const modeValue = normalizeConfiguredValue(models?.[mode]);
  if (modeValue) return modeValue;

  const defaultValue = normalizeConfiguredValue(models?.default);
  if (defaultValue) return defaultValue;

  return getMainDefaultModel(codexHomeOverride);
}

const TEAM_LOW_COMPLEXITY_MODEL_KEYS = [
  'team_low_complexity',
  'team-low-complexity',
  'teamLowComplexity',
];

/**
 * Get the envvar-backed spark/low-complexity default model.
 * Resolution: SPECIFY_DEFAULT_SPARK_MODEL > SPECIFY_SPARK_MODEL > explicit low-complexity key(s) > DEFAULT_SPARK_MODEL
 */
export function getSparkDefaultModel(codexHomeOverride?: string): string {
  return getEnvConfiguredSparkDefaultModel(process.env, codexHomeOverride)
    ?? readTeamLowComplexityOverride(codexHomeOverride)
    ?? DEFAULT_SPARK_MODEL;
}

/**
 * Get the low-complexity team worker model.
 * Resolution: explicit low-complexity key(s) > SPECIFY_DEFAULT_SPARK_MODEL > SPECIFY_SPARK_MODEL > DEFAULT_SPARK_MODEL
 */
export function getTeamLowComplexityModel(codexHomeOverride?: string): string {
  return readTeamLowComplexityOverride(codexHomeOverride) ?? getSparkDefaultModel(codexHomeOverride);
}
