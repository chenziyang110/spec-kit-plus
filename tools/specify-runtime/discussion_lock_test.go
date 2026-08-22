package main

import "testing"

func installDiscussionMutationBarrierForTest(t *testing.T, wantMode, wantSlug string) (<-chan struct{}, chan struct{}, func()) {
	t.Helper()
	entered := make(chan struct{}, 1)
	release := make(chan struct{})
	previous := discussionMutationBarrierForTest
	discussionMutationBarrierForTest = func(mode, slug string) {
		if mode != wantMode || slug != wantSlug {
			return
		}
		entered <- struct{}{}
		<-release
	}
	restore := func() {
		discussionMutationBarrierForTest = previous
	}
	t.Cleanup(restore)
	return entered, release, restore
}
