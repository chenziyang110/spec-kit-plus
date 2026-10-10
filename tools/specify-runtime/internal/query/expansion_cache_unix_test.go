//go:build linux || darwin || freebsd || openbsd || netbsd || dragonfly

package query

import (
	"fmt"
	"reflect"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
)

func TestExpansionCacheConcurrentReadersSeeCompleteSnapshots(t *testing.T) {
	paths, initial := expansionCacheFixture(t)
	initial.SectionPayloads = map[string]any{"related_paths": []string{"seed"}}
	if _, err := writeExpansionBundle(paths, initial); err != nil {
		t.Fatal(err)
	}
	const writers, readers, iterations = 4, 4, 80
	start := make(chan struct{})
	failures := make(chan error, writers+readers)
	var wg sync.WaitGroup
	var readCount atomic.Int64
	for w := 0; w < writers; w++ {
		wg.Add(1)
		go func(w int) {
			defer wg.Done()
			<-start
			for i := 0; i < iterations; i++ {
				marker := fmt.Sprintf("writer-%d-revision-%d-", w, i) + strings.Repeat("x", 128+(i%5)*100)
				rows := make([]string, 50)
				for j := range rows {
					rows[j] = marker
				}
				bundle := initial
				bundle.SectionPayloads = map[string]any{"related_paths": rows}
				if _, err := writeExpansionBundle(paths, bundle); err != nil {
					failures <- err
					return
				}
			}
		}(w)
	}
	for r := 0; r < readers; r++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start
			for i := 0; i < iterations*2; i++ {
				got, err := Expand(paths, ExpandInput{ID: initial.ID})
				if err != nil || got.Status != expansionStatusOK {
					failures <- fmt.Errorf("read partial/invalid snapshot: %v %#v", err, got)
					return
				}
				rows, ok := got.Data.([]any)
				if !ok || (len(rows) != 1 && len(rows) != 50) {
					failures <- fmt.Errorf("invalid snapshot shape: %#v", got.Data)
					return
				}
				if len(rows) == 1 && rows[0] != "seed" {
					failures <- fmt.Errorf("invalid seed: %#v", rows)
					return
				}
				for _, row := range rows {
					if !reflect.DeepEqual(row, rows[0]) {
						failures <- fmt.Errorf("mixed writer snapshots")
						return
					}
				}
				readCount.Add(1)
			}
		}()
	}
	close(start)
	wg.Wait()
	close(failures)
	for err := range failures {
		t.Error(err)
	}
	if got := readCount.Load(); got != readers*iterations*2 {
		t.Errorf("only %d/%d reads validated", got, readers*iterations*2)
	}
	t.Logf("validated %d reads against %d concurrent publications", readCount.Load(), writers*iterations)
}
