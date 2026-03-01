package config

import (
	"os"
	"strconv"
)

// Config Worker 配置
type Config struct {
	// 设备信息
	DeviceID     string
	DeviceName   string
	DeviceToken  string // API Key

	// Gateway 连接
	GatewayURL   string
	ReconnectInt int // 重连间隔(秒)

	// Brain API
	BrainURL     string

	// 执行配置
	MaxTasks     int // 最大并发任务数
	TaskTimeout  int // 任务超时(秒)

	// 截图配置
	ScreenshotDir string
}

// Load 从环境变量加载配置
func Load() *Config {
	return &Config{
		DeviceID:      getEnv("CANTOR_DEVICE_ID", "device-001"),
		DeviceName:    getEnv("CANTOR_DEVICE_NAME", "Cloud Phone"),
		DeviceToken:   getEnv("CANTOR_DEVICE_TOKEN", ""),
		GatewayURL:    getEnv("CANTOR_GATEWAY_URL", "ws://localhost:8766/ws"),
		ReconnectInt:  getEnvInt("CANTOR_RECONNECT_INTERVAL", 5),
		BrainURL:      getEnv("CANTOR_BRAIN_URL", "http://localhost:8000"),
		MaxTasks:      getEnvInt("CANTOR_MAX_TASKS", 10),
		TaskTimeout:   getEnvInt("CANTOR_TASK_TIMEOUT", 300),
		ScreenshotDir: getEnv("CANTOR_SCREENSHOT_DIR", "/data/cantor/screenshots"),
	}
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

func getEnvInt(key string, defaultVal int) int {
	if val := os.Getenv(key); val != "" {
		if i, err := strconv.Atoi(val); err == nil {
			return i
		}
	}
	return defaultVal
}
