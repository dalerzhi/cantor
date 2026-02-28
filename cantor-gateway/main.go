package main

import (
	"context"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all origins for simplicity, update for production
	},
}

// ConnectionManager manages active WebSocket connections.
type ConnectionManager struct {
	mu          sync.RWMutex
	connections map[*websocket.Conn]string // conn -> device_id
}

func NewConnectionManager() *ConnectionManager {
	return &ConnectionManager{
		connections: make(map[*websocket.Conn]string),
	}
}

func (cm *ConnectionManager) Add(conn *websocket.Conn, deviceID string) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	cm.connections[conn] = deviceID
	log.Printf("Client connected: %s. Total clients: %d", deviceID, len(cm.connections))
}

func (cm *ConnectionManager) Remove(conn *websocket.Conn) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	if deviceID, ok := cm.connections[conn]; ok {
		delete(cm.connections, conn)
		_ = conn.Close()
		log.Printf("Client disconnected: %s. Total clients: %d", deviceID, len(cm.connections))
	}
}

func handleWebSocket(cm *ConnectionManager, rdb *redis.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Extract device_id from query parameters
		deviceID := r.URL.Query().Get("device_id")
		if deviceID == "" {
			deviceID = "unknown-device" 
		}

		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("Failed to upgrade connection: %v", err)
			return
		}

		cm.Add(conn, deviceID)
		defer cm.Remove(conn)

		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()

		// Start Redis subscriber for this device
		commandTopic := "cantor:commands:" + deviceID
		pubsub := rdb.Subscribe(ctx, commandTopic)
		defer pubsub.Close()

		go func() {
			ch := pubsub.Channel()
			for {
				select {
				case <-ctx.Done():
					return
				case msg, ok := <-ch:
					if !ok {
						return
					}
					// Write the received command to the websocket
					cm.mu.Lock()
					err := conn.WriteMessage(websocket.TextMessage, []byte(msg.Payload))
					cm.mu.Unlock()
					if err != nil {
						log.Printf("Error writing to websocket for device %s: %v", deviceID, err)
					}
				}
			}
		}()

		// Read loop to receive events from device and publish to Redis
		eventTopic := "device:events:" + deviceID
		for {
			messageType, message, err := conn.ReadMessage()
			if err != nil {
				if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
					log.Printf("Unexpected close error for device %s: %v", deviceID, err)
				}
				break // Exit the loop, which triggers defer cm.Remove(conn) and defer cancel()
			}
			log.Printf("Received message from %s: %s (type %d)", deviceID, string(message), messageType)
			
			// Publish to Redis
			err = rdb.Publish(ctx, eventTopic, message).Err()
			if err != nil {
				log.Printf("Failed to publish event for device %s to Redis: %v", deviceID, err)
			}
		}
	}
}

func main() {
	// Connect to local Redis (redis://localhost:6379/0)
	opts, err := redis.ParseURL("redis://localhost:6379/0")
	if err != nil {
		log.Fatalf("Failed to parse Redis URL: %v", err)
	}
	rdb := redis.NewClient(opts)
	
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	log.Println("Connected to Redis successfully.")

	cm := NewConnectionManager()

	http.HandleFunc("/ws", handleWebSocket(cm, rdb))

	port := ":8766"
	log.Printf("WebSocket server starting on %s...", port)
	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}