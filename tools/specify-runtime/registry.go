package main

import (
	"fmt"
	"io"
	"sort"
)

type Command interface {
	Name() string
	Capabilities() []string
	Run(args []string, stdout, stderr io.Writer) int
}

type Registry struct {
	commands map[string]Command
}

func NewRegistry() *Registry {
	return &Registry{commands: map[string]Command{}}
}

func (registry *Registry) Register(command Command) error {
	if command == nil {
		return fmt.Errorf("register command: nil command")
	}
	name := command.Name()
	if name == "" {
		return fmt.Errorf("register command: empty name")
	}
	if _, exists := registry.commands[name]; exists {
		return fmt.Errorf("register command %q: already registered", name)
	}
	registry.commands[name] = command
	return nil
}

func (registry *Registry) Lookup(name string) (Command, bool) {
	command, ok := registry.commands[name]
	return command, ok
}

func (registry *Registry) Names() []string {
	names := make([]string, 0, len(registry.commands))
	for name := range registry.commands {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func (registry *Registry) Capabilities() []string {
	seen := map[string]bool{}
	for _, command := range registry.commands {
		for _, capability := range command.Capabilities() {
			if capability != "" {
				seen[capability] = true
			}
		}
	}
	capabilities := make([]string, 0, len(seen))
	for capability := range seen {
		capabilities = append(capabilities, capability)
	}
	sort.Strings(capabilities)
	return capabilities
}
