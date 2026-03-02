package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

var DB *sql.DB

func InitDB() {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "postgres://postgres:postgres@localhost:5432/cantor?sslmode=disable"
	}

	var err error
	DB, err = sql.Open("pgx", dsn)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v\n", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := DB.PingContext(ctx); err != nil {
		log.Fatalf("Unable to ping database: %v\n", err)
	}

	log.Println("Connected to PostgreSQL successfully.")
}

// CheckTenant validates if a tenant has active trial and is within limits
func CheckTenant(ctx context.Context, tenantID string, currentNodes int) error {
	query := `SELECT status, plan_tier, trial_ends_at, max_nodes FROM organizations WHERE id = $1`
	
	var status, planTier string
	var trialEndsAt sql.NullTime
	var maxNodes int

	err := DB.QueryRowContext(ctx, query, tenantID).Scan(&status, &planTier, &trialEndsAt, &maxNodes)
	if err != nil {
		if err == sql.ErrNoRows {
			return fmt.Errorf("tenant not found")
		}
		return fmt.Errorf("database error: %v", err)
	}

	if status != "active" {
		return fmt.Errorf("tenant is not active (status: %s)", status)
	}

	if planTier == "trial" {
		if trialEndsAt.Valid && time.Now().UTC().After(trialEndsAt.Time) {
			return fmt.Errorf("trial period has expired")
		}
	}

	if currentNodes >= maxNodes {
		return fmt.Errorf("maximum concurrent nodes limit reached (%d)", maxNodes)
	}

	return nil
}
