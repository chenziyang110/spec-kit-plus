.PHONY: test build vet fmt

test:
	go test ./...

build:
	go build -o bin/specify-runtime .

vet:
	go vet ./...

fmt:
	gofmt -w .
