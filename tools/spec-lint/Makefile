.PHONY: build build-all clean test

BINARY := spec-lint
OUT_DIR := bin
MODULE := github.com/chenziyang110/spec-kit-plus/tools/spec-lint

VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
COMMIT  ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
DATE    ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown")

LDFLAGS := -s -w \
	-X 'main.version=$(VERSION)' \
	-X 'main.commit=$(COMMIT)' \
	-X 'main.date=$(DATE)'

# build for current platform
build:
	@mkdir -p $(OUT_DIR)
	go build -ldflags "$(LDFLAGS)" -o $(OUT_DIR)/$(BINARY) .

# build a single platform
build-one:
	@mkdir -p $(OUT_DIR)
	GOOS=$(GOOS) GOARCH=$(GOARCH) go build -ldflags "$(LDFLAGS)" -o $(OUT_DIR)/$(BINARY)-$(GOOS)-$(GOARCH)$(if $(findstring windows,$(GOOS)),.exe,) .

# cross-compile for all supported platforms
build-all: clean
	@echo "Building spec-lint $(VERSION)..."
	GOOS=linux   GOARCH=amd64 $(MAKE) build-one
	GOOS=linux   GOARCH=arm64 $(MAKE) build-one
	GOOS=darwin  GOARCH=amd64 $(MAKE) build-one
	GOOS=darwin  GOARCH=arm64 $(MAKE) build-one
	GOOS=windows GOARCH=amd64 $(MAKE) build-one
	@echo ""
	@echo "Binaries:"
	@ls -lh $(OUT_DIR)/

clean:
	rm -rf $(OUT_DIR)

test:
	go vet ./...
	go build -o /dev/null .
