package executor

import (
	"bytes"
	"context"
	"os/exec"
	"time"
)

// ShellExecutor Shell 命令执行器
type ShellExecutor struct{}

// NewShellExecutor 创建 Shell 执行器
func NewShellExecutor() *ShellExecutor {
	return &ShellExecutor{}
}

// Execute 执行 Shell 命令
func (e *ShellExecutor) Execute(ctx context.Context, command string) (string, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()

	cmd := exec.CommandContext(ctx, "sh", "-c", command)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()

	output := stdout.String()
	if stderr.Len() > 0 {
		output += "\n[stderr]\n" + stderr.String()
	}

	return output, err
}
