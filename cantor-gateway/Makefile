.PHONY: all build run clean deps

APP_NAME = cantor-gateway
BIN_DIR = bin

all: build

build:
	@echo "Building $(APP_NAME)..."
	@mkdir -p $(BIN_DIR)
	@go build -o $(BIN_DIR)/$(APP_NAME) main.go

run: build
	@echo "Running $(APP_NAME)..."
	@./$(BIN_DIR)/$(APP_NAME)

clean:
	@echo "Cleaning up..."
	@rm -rf $(BIN_DIR)

deps:
	@echo "Tidying dependencies..."
	@go mod tidy
