import { existsSync } from 'fs'
import { mkdir, readFile } from 'fs/promises'
import { join, resolve } from 'path'
import type { TeamTask } from './state.js'
import { writeAtomic } from './state.js'

export type TeamOperationalCommitKind =
  | 'auto_checkpoint'
  | 'integration_merge'
  | 'integration_cherry_pick'
  | 'cross_rebase'
  | 'shutdown_checkpoint'
  | 'shutdown_merge'

export interface TeamOperationalCommitEntry {
  recorded_at: string;
  operation: TeamOperationalCommitKind;
  worker_name: string;
  task_id?: string;
  status: 'applied' | 'noop' | 'conflict' | 'skipped';
  operational_commit?: string | null;
  source_commit?: string | null;
  leader_head_before?: string | null;
  leader_head_after?: string | null;
  worker_head_before?: string | null;
  worker_head_after?: string | null;
  worktree_path?: string;
  report_path?: string;
  detail?: string;
}

export interface TeamCommitHygieneLedger {
  version: 1;
  team_name: string;
  updated_at: string;
  runtime_commits_are_scaffolding: true;
  entries: TeamOperationalCommitEntry[];
}

export interface TeamCommitHygieneTaskSummary {
  id: string;
  subject: string;
  owner?: string;
  status: string;
  description: string;
  result_excerpt?: string;
  error_excerpt?: string;
}

export interface TeamCommitHygieneContext {
  version: 1;
  team_name: string;
  generated_at: string;
  lore_commit_protocol_required: true;
  runtime_commits_are_scaffolding: true;
  task_summary: TeamCommitHygieneTaskSummary[];
  operational_entries: TeamOperationalCommitEntry[];
  recommended_next_steps: string[];
  leader_finalization_prompt: string;
}

export interface TeamCommitHygieneArtifactPaths {
  jsonPath: string;
  markdownPath: string;
}

function commitHygieneReportsDir(cwd: string): string {
  return join(resolve(cwd), '.omx', 'reports', 'team-commit-hygiene')
}

function ledgerPathFor(teamName: string, cwd: string): string {
  return join(commitHygieneReportsDir(cwd), `${teamName}.ledger.json`)
}

export function resolveTeamCommitHygieneArtifactPaths(teamName: string, cwd: string): TeamCommitHygieneArtifactPaths {
  const reportsDir = commitHygieneReportsDir(cwd)
  return {
    jsonPath: join(reportsDir, `${teamName}.context.json`),
    markdownPath: join(reportsDir, `${teamName}.md`),
  }
}

function excerpt(value: string | undefined, maxLength: number = 240): string | undefined {
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  if (!trimmed) return undefined
  return trimmed.length <= maxLength ? trimmed : `${trimmed.slice(0, maxLength - 1)}…`
}

function entryFingerprint(entry: TeamOperationalCommitEntry): string {
  return [
    entry.operation,
    entry.worker_name,
    entry.task_id ?? '',
    entry.status,
    entry.operational_commit ?? '',
    entry.source_commit ?? '',
    entry.leader_head_before ?? '',
    entry.leader_head_after ?? '',
    entry.worker_head_before ?? '',
    entry.worker_head_after ?? '',
    entry.report_path ?? '',
    entry.detail ?? '',
  ].join('|')
}

export async function readTeamCommitHygieneLedger(teamName: string, cwd: string): Promise<TeamCommitHygieneLedger> {
  const path = ledgerPathFor(teamName, cwd)
  if (!existsSync(path)) {
    return {
      version: 1,
      team_name: teamName,
      updated_at: new Date(0).toISOString(),
      runtime_commits_are_scaffolding: true,
      entries: [],
    }
  }

  try {
    const raw = await readFile(path, 'utf-8')
    const parsed = JSON.parse(raw) as Partial<TeamCommitHygieneLedger>
    return {
      version: 1,
      team_name: typeof parsed.team_name === 'string' && parsed.team_name.trim() !== '' ? parsed.team_name : teamName,
      updated_at: typeof parsed.updated_at === 'string' ? parsed.updated_at : new Date(0).toISOString(),
      runtime_commits_are_scaffolding: true,
      entries: Array.isArray(parsed.entries) ? parsed.entries : [],
    }
  } catch {
    return {
      version: 1,
      team_name: teamName,
      updated_at: new Date(0).toISOString(),
      runtime_commits_are_scaffolding: true,
      entries: [],
    }
  }
}

export async function appendTeamCommitHygieneEntries(
  teamName: string,
  entries: TeamOperationalCommitEntry[],
  cwd: string,
): Promise<TeamCommitHygieneLedger> {
  const nextEntries = entries.filter(Boolean)
  const ledger = await readTeamCommitHygieneLedger(teamName, cwd)
  if (nextEntries.length === 0) return ledger

  await mkdir(commitHygieneReportsDir(cwd), { recursive: true })
  const seen = new Set(ledger.entries.map(entryFingerprint))
  const deduped = nextEntries.filter((entry) => {
    const fingerprint = entryFingerprint(entry)
    if (seen.has(fingerprint)) return false
    seen.add(fingerprint)
    return true
  })
  if (deduped.length === 0) return ledger

  const updated: TeamCommitHygieneLedger = {
    ...ledger,
    updated_at: new Date().toISOString(),
    entries: [...ledger.entries, ...deduped],
  }
  await writeAtomic(ledgerPathFor(teamName, cwd), JSON.stringify(updated, null, 2))
  return updated
}

function summarizeTasks(tasks: TeamTask[]): TeamCommitHygieneTaskSummary[] {
  return tasks.map((task) => ({
    id: task.id,
    subject: task.subject,
    owner: task.owner,
    status: task.status,
    description: task.description,
    result_excerpt: excerpt(task.result),
    error_excerpt: excerpt(task.error),
  }))
}

function buildLeaderFinalizationPrompt(teamName: string, taskSummary: TeamCommitHygieneTaskSummary[]): string {
  const completedSubjects = taskSummary
    .filter((task) => task.status === 'completed')
    .map((task) => task.subject)
    .slice(0, 8)

  const scopeHint = completedSubjects.length > 0
    ? `Completed task subjects: ${completedSubjects.join(' | ')}.`
    : 'Use the completed task descriptions and resulting diffs to infer semantic commit boundaries.'

  return [
    `Team "${teamName}" is ready for commit finalization.`,
    'Treat runtime-originated commits (auto-checkpoints, merge/cherry-picks, cross-rebases, shutdown checkpoints) as temporary scaffolding rather than final history.',
    'Do not reuse operational commit subjects verbatim.',
    `${scopeHint}`,
    'Rewrite or squash the operational history into clean Lore-format final commit(s) with intent-first subjects and relevant trailers.',
    'Use task subjects/results and shutdown diff reports to choose semantic commit boundaries and rationale.',
  ].join(' ')
}

export function buildTeamCommitHygieneContext(params: {
  teamName: string;
  tasks: TeamTask[];
  ledger: TeamCommitHygieneLedger;
}): TeamCommitHygieneContext {
  const taskSummary = summarizeTasks(params.tasks)
  const recommendedNextSteps = [
    'Inspect the current branch diff/log and identify which runtime-originated commits should be squashed or rewritten.',
    'Derive semantic commit boundaries from completed task subjects, code diffs, and shutdown reports rather than from omx(team) operational commit subjects.',
    'Create final commit messages in Lore format with intent-first subjects and only the trailers that add decision context.',
  ]

  return {
    version: 1,
    team_name: params.teamName,
    generated_at: new Date().toISOString(),
    lore_commit_protocol_required: true,
    runtime_commits_are_scaffolding: true,
    task_summary: taskSummary,
    operational_entries: params.ledger.entries,
    recommended_next_steps: recommendedNextSteps,
    leader_finalization_prompt: buildLeaderFinalizationPrompt(params.teamName, taskSummary),
  }
}

function renderTaskSummaryMarkdown(taskSummary: TeamCommitHygieneTaskSummary[]): string {
  if (taskSummary.length === 0) return '- No task metadata available.'

  return taskSummary.map((task) => {
    const lines = [
      `- task-${task.id} | status=${task.status} | owner=${task.owner ?? 'unassigned'} | subject=${task.subject}`,
      `  - description: ${task.description}`,
    ]
    if (task.result_excerpt) lines.push(`  - result_excerpt: ${task.result_excerpt}`)
    if (task.error_excerpt) lines.push(`  - error_excerpt: ${task.error_excerpt}`)
    return lines.join('\n')
  }).join('\n')
}

function renderOperationalEntriesMarkdown(entries: TeamOperationalCommitEntry[]): string {
  if (entries.length === 0) return '- No runtime-originated commit activity recorded.'

  return entries.map((entry) => {
    const parts = [
      `- [${entry.recorded_at}] ${entry.operation}`,
      `worker=${entry.worker_name}`,
      `status=${entry.status}`,
    ]
    if (entry.task_id) parts.push(`task=${entry.task_id}`)
    if (entry.operational_commit) parts.push(`operational_commit=${entry.operational_commit}`)
    if (entry.source_commit) parts.push(`source_commit=${entry.source_commit}`)
    if (entry.leader_head_before) parts.push(`leader_before=${entry.leader_head_before}`)
    if (entry.leader_head_after) parts.push(`leader_after=${entry.leader_head_after}`)
    if (entry.worker_head_before) parts.push(`worker_before=${entry.worker_head_before}`)
    if (entry.worker_head_after) parts.push(`worker_after=${entry.worker_head_after}`)
    if (entry.report_path) parts.push(`report_path=${entry.report_path}`)
    if (entry.detail) parts.push(`detail=${entry.detail}`)
    return parts.join(' | ')
  }).join('\n')
}

export function renderTeamCommitHygieneMarkdown(context: TeamCommitHygieneContext): string {
  return [
    '# Team Commit Hygiene Finalization Guide',
    '',
    `- team: ${context.team_name}`,
    `- generated_at: ${context.generated_at}`,
    '- lore_commit_protocol_required: true',
    '- runtime_commits_are_scaffolding: true',
    '',
    '## Suggested Leader Finalization Prompt',
    '',
    '```text',
    context.leader_finalization_prompt,
    '```',
    '',
    '## Task Summary',
    '',
    renderTaskSummaryMarkdown(context.task_summary),
    '',
    '## Runtime Operational Ledger',
    '',
    renderOperationalEntriesMarkdown(context.operational_entries),
    '',
    '## Finalization Guidance',
    '',
    '1. Treat `omx(team): ...` runtime commits as temporary scaffolding, not as the final PR history.',
    '2. Reconcile checkpoint, merge/cherry-pick, cross-rebase, and shutdown checkpoint activity into semantic Lore-format final commit(s).',
    '3. Use task outcomes, code diffs, and shutdown diff reports to name and scope the final commits.',
    '',
    '## Recommended Next Steps',
    '',
    ...context.recommended_next_steps.map((step, index) => `${index + 1}. ${step}`),
    '',
  ].join('\n')
}

export async function writeTeamCommitHygieneContext(
  teamName: string,
  context: TeamCommitHygieneContext,
  cwd: string,
): Promise<TeamCommitHygieneArtifactPaths> {
  const paths = resolveTeamCommitHygieneArtifactPaths(teamName, cwd)
  await mkdir(commitHygieneReportsDir(cwd), { recursive: true })
  await writeAtomic(paths.jsonPath, JSON.stringify(context, null, 2))
  await writeAtomic(paths.markdownPath, renderTeamCommitHygieneMarkdown(context))
  return paths
}
