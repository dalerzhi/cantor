package main

import (
	"encoding/json"
	"net/http"
	"strings"
	"time"
)

func AdminMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		if !strings.HasPrefix(authHeader, "Bearer ") {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		token := strings.TrimPrefix(authHeader, "Bearer ")
		// In a real app, validate with a secret or token. Hardcoded for stub.
		if token != "admin-secret-token" {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		next(w, r)
	}
}

type TrialRequest struct {
	TenantID string `json:"tenant_id"`
}

func adminSetupTrialHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req TrialRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	trialEndsAt := time.Now().UTC().AddDate(0, 0, 7)

	query := `
		UPDATE organizations 
		SET plan_tier = 'trial', status = 'active', trial_ends_at = $1, max_nodes = 5, vlm_quota_remaining = 1000 
		WHERE id = $2`

	res, err := DB.ExecContext(r.Context(), query, trialEndsAt, req.TenantID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	rows, _ := res.RowsAffected()
	if rows == 0 {
		http.Error(w, "Tenant not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": "success",
		"tenant_id": req.TenantID,
		"trial_ends_at": trialEndsAt,
	})
}

type UpdateTenantRequest struct {
	TenantID string `json:"tenant_id"`
	PlanTier string `json:"plan_tier,omitempty"`
	Status   string `json:"status,omitempty"`
}

func adminUpdateTenantHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req UpdateTenantRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	query := `UPDATE organizations SET `
	var args []interface{}
	idx := 1

	if req.PlanTier != "" {
		query += "plan_tier = $" + string(rune(idx+'0')) + ", "
		args = append(args, req.PlanTier)
		idx++
	}
	if req.Status != "" {
		query += "status = $" + string(rune(idx+'0')) + ", "
		args = append(args, req.Status)
		idx++
	}

	// Remove trailing comma
	query = strings.TrimSuffix(query, ", ")
	query += " WHERE id = $" + string(rune(idx+'0'))
	args = append(args, req.TenantID)

	if len(args) == 1 {
		http.Error(w, "No fields to update", http.StatusBadRequest)
		return
	}

	res, err := DB.ExecContext(r.Context(), query, args...)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	rows, _ := res.RowsAffected()
	if rows == 0 {
		http.Error(w, "Tenant not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{"status": "success"})
}
