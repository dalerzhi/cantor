package ws

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// MessageType 消息类型
type MessageType string

const (
	TypeRegister   MessageType = "register"
	TypeHeartbeat  MessageType = "heartbeat"
	TypeTaskAssign MessageType = "task_assign"
	TypeTaskStatus MessageType = "task_status"
	TypeScreenshot MessageType = "screenshot"
	TypeLog        MessageType = "log"
	TypeError      MessageType = "error"
)

// Message 通用消息结构
type Message struct {
	Type      MessageType     `json:"type"`
	DeviceID  string          `json:"device_id"`
	Timestamp int64           `json:"timestamp"`
	Payload   json.RawMessage `json:"payload,omitempty"`
}

// RegisterPayload 注册消息
type RegisterPayload struct {
	DeviceName string `json:"device_name"`
	Token      string `json:"token"`
}

// TaskPayload 任务消息
type TaskPayload struct {
	TaskID      string          `json:"task_id"`
	TaskType    string          `json:"task_type"`
	Script      string          `json:"script,omitempty"`
	ScriptLang  string          `json:"script_lang,omitempty"`
	Command     string          `json:"command,omitempty"`
	Params      json.RawMessage `json:"params,omitempty"`
	Timeout     int             `json:"timeout,omitempty"`
}

// TaskStatusPayload 任务状态
type TaskStatusPayload struct {
	TaskID    string `json:"task_id"`
	Status    string `json:"status"` // running, completed, failed
	Progress  int    `json:"progress"`
	Output    string `json:"output,omitempty"`
	Error     string `json:"error,omitempty"`
}

// ScreenshotPayload 截图
type ScreenshotPayload struct {
	TaskID    string `json:"task_id,omitempty"`
	ImageData []byte `json:"image_data"`
	Width     int    `json:"width"`
	Height    int    `json:"height"`
}

// Handler 消息处理器
type Handler func(msg *Message) error

// Client WebSocket 客户端
type Client struct {
	url         string
	deviceID    string
	deviceName  string
	token       string
	conn        *websocket.Conn
	handlers    map[MessageType]Handler
	sendChan    chan *Message
	reconnectInt time.Duration
	mu          sync.RWMutex
	ctx         context.Context
	cancel      context.CancelFunc
}

// NewClient 创建客户端
func NewClient(url, deviceID, deviceName, token string, reconnectInt int) *Client {
	ctx, cancel := context.WithCancel(context.Background())
	return &Client{
		url:          url,
		deviceID:     deviceID,
		deviceName:   deviceName,
		token:        token,
		handlers:     make(map[MessageType]Handler),
		sendChan:     make(chan *Message, 100),
		reconnectInt: time.Duration(reconnectInt) * time.Second,
		ctx:          ctx,
		cancel:       cancel,
	}
}

// On 注册消息处理器
func (c *Client) On(msgType MessageType, handler Handler) {
	c.handlers[msgType] = handler
}

// Connect 连接服务器
func (c *Client) Connect() error {
	conn, _, err := websocket.DefaultDialer.Dial(c.url, nil)
	if err != nil {
		return fmt.Errorf("dial failed: %w", err)
	}

	c.mu.Lock()
	c.conn = conn
	c.mu.Unlock()

	// 注册设备
	if err := c.register(); err != nil {
		return fmt.Errorf("register failed: %w", err)
	}

	return nil
}

// register 发送注册消息
func (c *Client) register() error {
	payload, _ := json.Marshal(RegisterPayload{
		DeviceName: c.deviceName,
		Token:      c.token,
	})

	msg := &Message{
		Type:      TypeRegister,
		DeviceID:  c.deviceID,
		Timestamp: time.Now().UnixMilli(),
		Payload:   payload,
	}

	return c.Send(msg)
}

// Send 发送消息
func (c *Client) Send(msg *Message) error {
	c.mu.RLock()
	conn := c.conn
	c.mu.RUnlock()

	if conn == nil {
		return fmt.Errorf("not connected")
	}

	return conn.WriteJSON(msg)
}

// SendTaskStatus 发送任务状态
func (c *Client) SendTaskStatus(status *TaskStatusPayload) error {
	payload, _ := json.Marshal(status)
	return c.Send(&Message{
		Type:      TypeTaskStatus,
		DeviceID:  c.deviceID,
		Timestamp: time.Now().UnixMilli(),
		Payload:   payload,
	})
}

// SendLog 发送日志
func (c *Client) SendLog(logMsg string) error {
	return c.Send(&Message{
		Type:      TypeLog,
		DeviceID:  c.deviceID,
		Timestamp: time.Now().UnixMilli(),
		Payload:   json.RawMessage(fmt.Sprintf(`{"message":%q}`, logMsg)),
	})
}

// SendScreenshot 发送截图
func (c *Client) SendScreenshot(screenshot *ScreenshotPayload) error {
	payload, _ := json.Marshal(screenshot)
	return c.Send(&Message{
		Type:      TypeScreenshot,
		DeviceID:  c.deviceID,
		Timestamp: time.Now().UnixMilli(),
		Payload:   payload,
	})
}

// Run 运行客户端
func (c *Client) Run() error {
	// 启动心跳
	go c.heartbeatLoop()

	// 启动发送循环
	go c.sendLoop()

	// 读取消息
	for {
		select {
		case <-c.ctx.Done():
			return nil
		default:
			c.mu.RLock()
			conn := c.conn
			c.mu.RUnlock()

			if conn == nil {
				c.reconnect()
				continue
			}

			msg := &Message{}
			if err := conn.ReadJSON(msg); err != nil {
				log.Printf("read error: %v", err)
				c.reconnect()
				continue
			}

			// 处理消息
			if handler, ok := c.handlers[msg.Type]; ok {
				if err := handler(msg); err != nil {
					log.Printf("handler error: %v", err)
				}
			}
		}
	}
}

// sendLoop 发送循环
func (c *Client) sendLoop() {
	for {
		select {
		case <-c.ctx.Done():
			return
		case msg := <-c.sendChan:
			if err := c.Send(msg); err != nil {
				log.Printf("send error: %v", err)
			}
		}
	}
}

// heartbeatLoop 心跳循环
func (c *Client) heartbeatLoop() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-c.ctx.Done():
			return
		case <-ticker.C:
			msg := &Message{
				Type:      TypeHeartbeat,
				DeviceID:  c.deviceID,
				Timestamp: time.Now().UnixMilli(),
			}
			if err := c.Send(msg); err != nil {
				log.Printf("heartbeat error: %v", err)
			}
		}
	}
}

// reconnect 重连
func (c *Client) reconnect() {
	c.mu.Lock()
	if c.conn != nil {
		c.conn.Close()
		c.conn = nil
	}
	c.mu.Unlock()

	for {
		select {
		case <-c.ctx.Done():
			return
		default:
			log.Printf("reconnecting to %s...", c.url)
			if err := c.Connect(); err != nil {
				log.Printf("reconnect failed: %v", err)
				time.Sleep(c.reconnectInt)
				continue
			}
			log.Println("reconnected successfully")
			return
		}
	}
}

// Close 关闭客户端
func (c *Client) Close() {
	c.cancel()
	c.mu.Lock()
	if c.conn != nil {
		c.conn.Close()
	}
	c.mu.Unlock()
}
