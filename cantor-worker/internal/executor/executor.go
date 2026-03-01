package executor

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"cantor-worker/internal/ws"
)

// TaskType 任务类型
type TaskType string

const (
	TaskTypeShell  TaskType = "shell"
	TaskTypeScript TaskType = "script"
	TaskTypeADB    TaskType = "adb"
	TaskTypeClick  TaskType = "click"
	TaskTypeInput  TaskType = "input"
	TaskTypeSwipe  TaskType = "swipe"
	TaskTypeScreenshot TaskType = "screenshot"
)

// Task 任务
type Task struct {
	ID        string
	Type      TaskType
	Script    string
	ScriptLang string
	Command   string
	Params    map[string]interface{}
	Timeout   time.Duration
	Status    string
	Progress  int
	Output    string
	Error     string
	Cancel    context.CancelFunc
}

// Executor 任务执行器
type Executor struct {
	tasks     map[string]*Task
	mu        sync.RWMutex
	maxTasks  int
	wsClient  *ws.Client
	shellExec *ShellExecutor
	adbExec   *ADBExecutor
}

// NewExecutor 创建执行器
func NewExecutor(maxTasks int, wsClient *ws.Client) *Executor {
	return &Executor{
		tasks:     make(map[string]*Task),
		maxTasks:  maxTasks,
		wsClient:  wsClient,
		shellExec: NewShellExecutor(),
		adbExec:   NewADBExecutor(),
	}
}

// Execute 执行任务
func (e *Executor) Execute(msg *ws.Message) error {
	var payload ws.TaskPayload
	if err := json.Unmarshal(msg.Payload, &payload); err != nil {
		return fmt.Errorf("parse task payload: %w", err)
	}

	// 检查并发限制
	e.mu.RLock()
	if len(e.tasks) >= e.maxTasks {
		e.mu.RUnlock()
		return fmt.Errorf("max concurrent tasks reached")
	}
	e.mu.RUnlock()

	// 创建任务
	task := &Task{
		ID:      payload.TaskID,
		Type:    TaskType(payload.TaskType),
		Script:  payload.Script,
		ScriptLang: payload.ScriptLang,
		Command: payload.Command,
		Timeout: time.Duration(payload.Timeout) * time.Second,
		Status:  "running",
	}

	// 解析参数
	if len(payload.Params) > 0 {
		if err := json.Unmarshal(payload.Params, &task.Params); err != nil {
			log.Printf("parse task params: %v", err)
		}
	}

	// 保存任务
	e.mu.Lock()
	e.tasks[task.ID] = task
	e.mu.Unlock()

	// 发送状态更新
	e.wsClient.SendTaskStatus(&ws.TaskStatusPayload{
		TaskID: task.ID,
		Status: "running",
	})

	// 执行任务
	go e.runTask(task)

	return nil
}

// runTask 运行任务
func (e *Executor) runTask(task *Task) {
	ctx, cancel := context.WithTimeout(context.Background(), task.Timeout)
	task.Cancel = cancel
	defer cancel()

	defer func() {
		e.mu.Lock()
		delete(e.tasks, task.ID)
		e.mu.Unlock()
	}()

	var output string
	var err error

	switch task.Type {
	case TaskTypeShell:
		output, err = e.shellExec.Execute(ctx, task.Command)

	case TaskTypeADB:
		output, err = e.adbExec.Execute(ctx, task.Command)

	case TaskTypeScript:
		output, err = e.executeScript(ctx, task)

	case TaskTypeClick:
		x, _ := task.Params["x"].(float64)
		y, _ := task.Params["y"].(float64)
		err = e.adbExec.Tap(ctx, int(x), int(y))

	case TaskTypeInput:
		text, _ := task.Params["text"].(string)
		err = e.adbExec.InputText(ctx, text)

	case TaskTypeSwipe:
		x1, _ := task.Params["x1"].(float64)
		y1, _ := task.Params["y1"].(float64)
		x2, _ := task.Params["x2"].(float64)
		y2, _ := task.Params["y2"].(float64)
		duration, _ := task.Params["duration"].(float64)
		err = e.adbExec.Swipe(ctx, int(x1), int(y1), int(x2), int(y2), int(duration))

	case TaskTypeScreenshot:
		var imgData []byte
		imgData, err = e.adbExec.Screenshot(ctx)
		if err == nil {
			e.wsClient.SendScreenshot(&ws.ScreenshotPayload{
				TaskID:    task.ID,
				ImageData: imgData,
			})
			output = "screenshot captured"
		}

	default:
		err = fmt.Errorf("unknown task type: %s", task.Type)
	}

	// 发送结果
	status := "completed"
	if err != nil {
		status = "failed"
		task.Error = err.Error()
	}
	task.Output = output
	task.Status = status

	e.wsClient.SendTaskStatus(&ws.TaskStatusPayload{
		TaskID:   task.ID,
		Status:   status,
		Output:   output,
		Error:    task.Error,
	})
}

// executeScript 执行脚本
func (e *Executor) executeScript(ctx context.Context, task *Task) (string, error) {
	switch task.ScriptLang {
	case "lua":
		return e.executeLuaScript(ctx, task.Script)
	case "python":
		return e.executePythonScript(ctx, task.Script)
	case "shell":
		return e.shellExec.Execute(ctx, task.Script)
	default:
		return "", fmt.Errorf("unsupported script language: %s", task.ScriptLang)
	}
}

// executeLuaScript 执行 Lua 脚本 (通过 shell 调用)
func (e *Executor) executeLuaScript(ctx context.Context, script string) (string, error) {
	// 将脚本写入临时文件并执行
	cmd := fmt.Sprintf("lua -e %q", script)
	return e.shellExec.Execute(ctx, cmd)
}

// executePythonScript 执行 Python 脚本 (通过 shell 调用)
func (e *Executor) executePythonScript(ctx context.Context, script string) (string, error) {
	// 注意: Android 通常没有 Python，需要 Termux 或其他环境
	cmd := fmt.Sprintf("python3 -c %q", script)
	return e.shellExec.Execute(ctx, cmd)
}

// GetTask 获取任务
func (e *Executor) GetTask(taskID string) *Task {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.tasks[taskID]
}

// CancelTask 取消任务
func (e *Executor) CancelTask(taskID string) error {
	e.mu.Lock()
	defer e.mu.Unlock()

	task, ok := e.tasks[taskID]
	if !ok {
		return fmt.Errorf("task not found: %s", taskID)
	}

	if task.Cancel != nil {
		task.Cancel()
	}

	task.Status = "cancelled"
	e.wsClient.SendTaskStatus(&ws.TaskStatusPayload{
		TaskID: taskID,
		Status: "cancelled",
	})

	return nil
}
