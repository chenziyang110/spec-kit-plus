import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { runUntilTerminal } from '../run-loop.js';

describe('runUntilTerminal', () => {
  it('continues through non-terminal outcomes until finish', async () => {
    const seen: string[] = [];
    const result = await runUntilTerminal(
      async (iteration) => ({
        outcome: iteration < 3 ? 'continue' : 'finish',
        state: { iteration },
      }),
      {
        onIteration(step) {
          seen.push(`${step.iteration}:${step.outcome}`);
        },
      },
    );

    assert.equal(result.iteration, 3);
    assert.equal(result.outcome, 'finish');
    assert.deepEqual(result.history, ['continue', 'continue', 'finish']);
    assert.deepEqual(seen, ['1:continue', '2:continue', '3:finish']);
  });

  it('normalizes legacy terminal labels before returning', async () => {
    const result = await runUntilTerminal(async () => ({
      outcome: 'completed',
      state: { ok: true },
    }));

    assert.equal(result.outcome, 'finish');
    assert.deepEqual(result.history, ['finish']);
  });

  it('throws when maxIterations is exceeded without terminal progress', async () => {
    await assert.rejects(
      () =>
        runUntilTerminal(
          async (iteration) => ({
            outcome: iteration % 2 === 0 ? 'progress' : 'continue',
            state: { iteration },
          }),
          { maxIterations: 3 },
        ),
      /maxIterations=3/,
    );
  });
});
