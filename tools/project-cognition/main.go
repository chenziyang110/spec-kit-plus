package main

import (
	"os"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/cli"
)

var version = "dev"

func main() {
	os.Exit(cli.Run(os.Args[1:], os.Stdout, os.Stderr, version))
}
