package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"

	"cantor-worker/internal/executor"
	"cantor-worker/internal/ws"
	"cantor-worker/pkg/config"
)

var (
	version = "dev"
	commit  = "none"
	date    = "unknown"
)

func main() {
	// 解析命令行参数
	showVersion := flag.Bool("version", false, "Show version information")
	_ = flag.String("config", "", "Config file path")
	flag.Parse()

	if *showVersion {
		log.Printf("Cantor Worker v%s (commit: %s, built: %s)\n", version, commit, date)
		os.Exit(0)
	}

	// 加载配置
	cfg := config.Load()
	log.Printf("Starting Cantor Worker v%s", version)
	log.Printf("Device ID: %s", cfg.DeviceID)
	log.Printf("Gateway: %s", cfg.GatewayURL)

	// 创建 WebSocket 客户端
	wsClient := ws.NewClient(
		cfg.GatewayURL,
		cfg.DeviceID,
		cfg.DeviceName,
		cfg.DeviceToken,
		cfg.ReconnectInt,
	)

	// 创建任务执行器
	executor := executor.NewExecutor(cfg.MaxTasks, wsClient)

	// 注册消息处理器
	wsClient.On(ws.TypeTaskAssign, func(msg *ws.Message) error {
		log.Printf("Received task assignment")
		return executor.Execute(msg)
	})

	// 连接 Gateway
	if err := wsClient.Connect(); err != nil {
		log.Fatalf("Failed to connect to gateway: %v", err)
	}
	log.Println("Connected to gateway successfully")

	// 启动 WebSocket 客户端
	go func() {
		if err := wsClient.Run(); err != nil {
			log.Printf("WebSocket client error: %v", err)
		}
	}()

	// 等待退出信号
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down...")
	wsClient.Close()
	log.Println("Goodbye!")
}
