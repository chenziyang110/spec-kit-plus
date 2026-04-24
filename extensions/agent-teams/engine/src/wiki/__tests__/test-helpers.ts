import assert from 'node:assert/strict';

const ARRAY_CONTAINING = Symbol('arrayContaining');

type ArrayContaining = { __matcher: typeof ARRAY_CONTAINING; expected: unknown[] };

function normalize(value: unknown): unknown {
  return value;
}

function matchesArrayContaining(actual: unknown, expected: ArrayContaining): boolean {
  if (!Array.isArray(actual)) return false;
  return expected.expected.every((item) => actual.some((candidate) => {
    try {
      assert.deepEqual(candidate, item);
      return true;
    } catch {
      return false;
    }
  }));
}

export function expect(actual: unknown) {
  const actualString = typeof actual === 'string' ? actual : String(actual);
  const actualArray = actual as unknown[];

  return {
    toBe(expected: unknown) {
      assert.equal(actual, expected);
    },
    toEqual(expected: unknown) {
      if (expected && typeof expected === 'object' && (expected as Partial<ArrayContaining>).__matcher === ARRAY_CONTAINING) {
        assert.ok(matchesArrayContaining(actual, expected as ArrayContaining));
        return;
      }
      assert.deepEqual(actual, expected);
    },
    toContain(expected: unknown) {
      if (typeof actual === 'string') {
        assert.ok(actual.includes(String(expected)));
        return;
      }
      assert.ok(Array.isArray(actualArray));
      assert.ok(actualArray.includes(expected));
    },
    toBeNull() {
      assert.equal(actual, null);
    },
    toHaveLength(expected: number) {
      assert.equal((actual as { length?: number })?.length, expected);
    },
    toBeGreaterThan(expected: number) {
      assert.ok(typeof actual === 'number' && actual > expected);
    },
    toBeGreaterThanOrEqual(expected: number) {
      assert.ok(typeof actual === 'number' && actual >= expected);
    },
    toBeLessThanOrEqual(expected: number) {
      assert.ok(typeof actual === 'number' && actual <= expected);
    },
    toBeDefined() {
      assert.notEqual(actual, undefined);
    },
    toBeUndefined() {
      assert.equal(actual, undefined);
    },
    toHaveProperty(property: string) {
      assert.ok(actual !== null && typeof actual === 'object' && property in (actual as object));
    },
    toMatch(pattern: RegExp) {
      assert.match(actualString, pattern);
    },
    toThrow(expected?: string | RegExp) {
      assert.equal(typeof actual, 'function');
      if (expected === undefined) {
        assert.throws(actual as () => unknown);
      } else if (typeof expected === 'string') {
        assert.throws(actual as () => unknown, new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
      } else {
        assert.throws(actual as () => unknown, expected);
      }
    },
    get not() {
      return {
        toBeNull() {
          assert.notEqual(actual, null);
        },
        toBe(expected: unknown) {
          assert.notEqual(actual, expected);
        },
        toContain(expected: unknown) {
          if (typeof actual === 'string') {
            assert.ok(!actual.includes(String(expected)));
            return;
          }
          assert.ok(Array.isArray(actualArray));
          assert.ok(!actualArray.includes(expected));
        },
        toThrow() {
          assert.equal(typeof actual, 'function');
          assert.doesNotThrow(actual as () => unknown);
        },
      };
    },
  };
}

expect.arrayContaining = (expected: unknown[]): ArrayContaining => ({
  __matcher: ARRAY_CONTAINING,
  expected: expected.map(normalize),
});
