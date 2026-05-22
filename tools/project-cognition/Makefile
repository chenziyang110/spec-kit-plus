.PHONY: test build vet fmt

test:
	go test ./...

build:
	go build -o bin/project-cognition .

vet:
	go vet ./...

fmt:
	gofmt -w .
