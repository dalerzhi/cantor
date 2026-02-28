package main

import (
	"log"
	"net/http"
	"sync"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all origins for simplicity, update for production
	},
}

// ConnectionManager manages active WebSocket connections.
type ConnectionManager struct {
	mu          sync.RWMutex
	connections map[*websocket.Conn]bool
}

func NewConnectionManager() *ConnectionManager {
	return &ConnectionManager{
		connections: make(map[*websocket.Conn]bool),
	}
}

func (cm *ConnectionManager) Add(conn *websocket.Conn) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	cm.connections[conn] = true
	log.Printf("Client connected. Total clients: %d", len(cm.connections))
}

func (cm *ConnectionManager) Remove(conn *websocket.Conn) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	if _, ok := cm.connections[conn]; ok {
		delete(cm.connections, conn)
		_ = conn.Close()
		log.Printf("Client disconnected. Total clients: %d", len(cm.connections))
	}
}

func handleWebSocket(cm *ConnectionManager) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("Failed to upgrade connection: %v", err)
			return
		}

		cm.Add(conn)
		defer cm.Remove(conn)

		// Read loop to keep the connection alive and detect disconnects
		for {
			messageType, message, err := conn.ReadMessage()
			if err != nil {
				if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
					log.Printf("Unexpected close error: %v", err)
				}
				break // Exit the loop and trigger defer cm.Remove(conn)
			}
			log.Printf("Received message: %s (type %d)", string(message), messageType)
		}
	}
}

func main() {
	cm := NewConnectionManager()

	http.HandleFunc("/ws", handleWebSocket(cm))

	port := ":8766"
	log.Printf("WebSocket server starting on %s...", port)
	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
