# Cantor Worker Makefile

.PHONY: all build build-android build-linux build-darwin clean test

BINARY_NAME=cantor-worker
VERSION?=dev
COMMIT?=$(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

# Go 参数
GOCMD=go
GOBUILD=$(GOCMD) build
GOCLEAN=$(GOCMD) clean
GOTEST=$(GOCMD) test
GOGET=$(GOCMD) get
GOMOD=$(GOCMD) mod

# 构建标志
LDFLAGS=-ldflags "-X main.version=$(VERSION) -X main.commit=$(COMMIT) -X main.date=$(DATE)"

# Android 目标
ANDROID_ARM64=GOOS=android GOARCH=arm64 CGO_ENABLED=0
ANDROID_ARM=GOOS=android GOARCH=arm CGO_ENABLED=0

# Linux 目标
LINUX_AMD64=GOOS=linux GOARCH=amd64 CGO_ENABLED=0
LINUX_ARM64=GOOS=linux GOARCH=arm64 CGO_ENABLED=0

# Darwin 目标
DARWIN_AMD64=GOOS=darwin GOARCH=amd64 CGO_ENABLED=0
DARWIN_ARM64=GOOS=darwin GOARCH=arm64 CGO_ENABLED=0

all: deps build

deps:
	$(GOMOD) download
	$(GOMOD) tidy

build:
	$(GOBUILD) $(LDFLAGS) -o bin/$(BINARY_NAME) ./cmd/worker

# Android 构建 (主要目标)
build-android: deps
	mkdir -p bin
	$(ANDROID_ARM64) $(GOBUILD) $(LDFLAGS) -o bin/$(BINARY_NAME)-android-arm64 ./cmd/worker
	@echo "Android build complete:"
	@ls -lh bin/$(BINARY_NAME)-android-*

# 服务器端构建
build-linux: deps
	mkdir -p bin
	$(LINUX_AMD64) $(GOBUILD) $(LDFLAGS) -o bin/$(BINARY_NAME)-linux-amd64 ./cmd/worker
	$(LINUX_ARM64) $(GOBUILD) $(LDFLAGS) -o bin/$(BINARY_NAME)-linux-arm64 ./cmd/worker

build-darwin: deps
	mkdir -p bin
	$(DARWIN_AMD64) $(GOBUILD) $(LDFLAGS) -o bin/$(BINARY_NAME)-darwin-amd64 ./cmd/worker
	$(DARWIN_ARM64) $(GOBUILD) $(LDFLAGS) -o bin/$(BINARY_NAME)-darwin-arm64 ./cmd/worker

# 构建所有平台
build-all: build-android build-linux build-darwin
	@echo "All builds complete"
	@ls -lh bin/

# Docker 构建
docker-build:
	docker build -t cantor-worker:$(VERSION) .

# 测试
test:
	$(GOTEST) -v -race ./...

# 清理
clean:
	$(GOCLEAN)
	rm -rf bin/

# 安装到设备
install-android:
	adb push bin/$(BINARY_NAME)-android-arm64 /data/local/tmp/$(BINARY_NAME)
	adb shell chmod +x /data/local/tmp/$(BINARY_NAME)

# 运行
run:
	./bin/$(BINARY_NAME)

# 帮助
help:
	@echo "Cantor Worker Build System"
	@echo ""
	@echo "Targets:"
	@echo "  make build          - Build for current platform"
	@echo "  make build-android  - Build for Android (arm64, arm)"
	@echo "  make build-linux    - Build for Linux (amd64, arm64)"
	@echo "  make build-darwin   - Build for macOS (amd64, arm64)"
	@echo "  make build-all      - Build for all platforms"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make install-android- Install to connected Android device"
	@echo ""
	@echo "Variables:"
	@echo "  VERSION=x.x.x       - Set version (default: dev)"
