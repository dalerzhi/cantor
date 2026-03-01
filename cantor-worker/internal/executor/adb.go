package executor

import (
	"bytes"
	"context"
	"encoding/base64"
	"fmt"
	"os/exec"
	"time"
)

// ADBExecutor ADB 命令执行器
type ADBExecutor struct{}

// NewADBExecutor 创建 ADB 执行器
func NewADBExecutor() *ADBExecutor {
	return &ADBExecutor{}
}

// Execute 执行 ADB 命令
func (e *ADBExecutor) Execute(ctx context.Context, command string) (string, error) {
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "sh", "-c", "input "+command)

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

// Tap 点击屏幕
func (e *ADBExecutor) Tap(ctx context.Context, x, y int) error {
	cmd := exec.CommandContext(ctx, "input", "tap", fmt.Sprintf("%d", x), fmt.Sprintf("%d", y))
	return cmd.Run()
}

// InputText 输入文本
func (e *ADBExecutor) InputText(ctx context.Context, text string) error {
	cmd := exec.CommandContext(ctx, "input", "text", text)
	return cmd.Run()
}

// Swipe 滑动屏幕
func (e *ADBExecutor) Swipe(ctx context.Context, x1, y1, x2, y2, durationMs int) error {
	cmd := exec.CommandContext(ctx, "input", "swipe",
		fmt.Sprintf("%d", x1),
		fmt.Sprintf("%d", y1),
		fmt.Sprintf("%d", x2),
		fmt.Sprintf("%d", y2),
		fmt.Sprintf("%d", durationMs),
	)
	return cmd.Run()
}

// KeyEvent 发送按键事件
func (e *ADBExecutor) KeyEvent(ctx context.Context, keyCode int) error {
	cmd := exec.CommandContext(ctx, "input", "keyevent", fmt.Sprintf("%d", keyCode))
	return cmd.Run()
}

// Screenshot 截屏
func (e *ADBExecutor) Screenshot(ctx context.Context) ([]byte, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	// 方法1: 使用 screencap 命令
	cmd := exec.CommandContext(ctx, "screencap", "-p")
	var stdout bytes.Buffer
	cmd.Stdout = &stdout

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("screencap failed: %w", err)
	}

	// 转换为 base64 (PNG 格式)
	pngData := stdout.Bytes()

	// 如果需要 base64 编码
	encoded := make([]byte, base64.StdEncoding.EncodedLen(len(pngData)))
	base64.StdEncoding.Encode(encoded, pngData)

	return encoded, nil
}

// StartApp 启动应用
func (e *ADBExecutor) StartApp(ctx context.Context, packageName string) error {
	cmd := exec.CommandContext(ctx, "am", "start", "-n", packageName)
	return cmd.Run()
}

// StopApp 停止应用
func (e *ADBExecutor) StopApp(ctx context.Context, packageName string) error {
	cmd := exec.CommandContext(ctx, "am", "force-stop", packageName)
	return cmd.Run()
}

// GetCurrentApp 获取当前应用
func (e *ADBExecutor) GetCurrentApp(ctx context.Context) (string, error) {
	cmd := exec.CommandContext(ctx, "dumpsys", "window", "windows", "|", "grep", "-E", "mCurrentFocus")
	var stdout bytes.Buffer
	cmd.Stdout = &stdout

	if err := cmd.Run(); err != nil {
		return "", err
	}

	return stdout.String(), nil
}

// GetScreenSize 获取屏幕尺寸
func (e *ADBExecutor) GetScreenSize(ctx context.Context) (width, height int, err error) {
	cmd := exec.CommandContext(ctx, "wm", "size")
	var stdout bytes.Buffer
	cmd.Stdout = &stdout

	if err = cmd.Run(); err != nil {
		return 0, 0, err
	}

	// 解析输出: "Physical size: 1080x2400"
	_, err = fmt.Sscanf(stdout.String(), "Physical size: %dx%d", &width, &height)
	return width, height, err
}

// LongPress 长按
func (e *ADBExecutor) LongPress(ctx context.Context, x, y, durationMs int) error {
	return e.Swipe(ctx, x, y, x, y, durationMs)
}

// Drag 拖拽
func (e *ADBExecutor) Drag(ctx context.Context, x1, y1, x2, y2, durationMs int) error {
	return e.Swipe(ctx, x1, y1, x2, y2, durationMs)
}

// MultiTouch 多点触控 (需要 root 或特殊权限)
func (e *ADBExecutor) MultiTouch(ctx context.Context, points [][2]int) error {
	// Android 的 input 命令不支持多点触控
	// 需要使用 sendevent 或其他方式
	return fmt.Errorf("multi-touch not implemented")
}
