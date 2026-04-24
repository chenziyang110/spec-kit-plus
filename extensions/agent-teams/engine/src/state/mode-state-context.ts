export interface ModeStateContextLike {
  active?: unknown;
  tmux_pane_id?: unknown;
  tmux_pane_set_at?: unknown;
  [key: string]: unknown;
}

export function captureTmuxPaneFromEnv(env: NodeJS.ProcessEnv = process.env): string | null {
  const value = env.TMUX_PANE;
  if (typeof value !== 'string') return null;
  const pane = value.trim();
  return pane.length > 0 ? pane : null;
}

function hasNonEmptyString(value: unknown): boolean {
  return typeof value === 'string' && value.trim() !== '';
}

export function withModeRuntimeContext<T extends ModeStateContextLike>(
  existing: ModeStateContextLike,
  next: T,
  options?: { env?: NodeJS.ProcessEnv; nowIso?: string }
): T {
  const env = options?.env ?? process.env;
  const nowIso = options?.nowIso ?? new Date().toISOString();
  const wasActive = existing.active === true;
  const isActive = next.active === true;
  const hasPane = hasNonEmptyString(next.tmux_pane_id);

  if (isActive && (!wasActive || !hasPane)) {
    const pane = captureTmuxPaneFromEnv(env);
    if (pane) {
      next.tmux_pane_id = pane;
      if (!hasNonEmptyString(next.tmux_pane_set_at)) {
        next.tmux_pane_set_at = nowIso;
      }
    }
  }

  return next;
}
