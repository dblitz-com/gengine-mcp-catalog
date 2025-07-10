package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"path/filepath"
	"strconv"
	"strings"
)

// Server represents an MCP server
type Server struct {
	ID          string      `json:"id"`
	Name        string      `json:"name"`
	Description string      `json:"description"`
	Category    string      `json:"category"`
	Vendor      string      `json:"vendor"`
	Homepage    string      `json:"homepage"`
	License     string      `json:"license,omitempty"`
	Features    []string    `json:"features,omitempty"`
	Config      interface{} `json:"config,omitempty"`
}

// Global server registry
var servers map[string]interface{}

func loadServers() {
	// Try to load known_servers.json
	paths := []string{
		"../../mcp_catalog/known_servers.json",
		"known_servers.json",
	}
	
	for _, path := range paths {
		if data, err := ioutil.ReadFile(path); err == nil {
			if err := json.Unmarshal(data, &servers); err == nil {
				log.Printf("📚 Loaded %d servers from %s", len(servers), path)
				return
			}
		}
	}
	
	log.Println("⚠️  No known_servers.json found, using empty registry")
	servers = make(map[string]interface{})
}

func enableCORS(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	w.Header().Set("Content-Type", "application/json")
	
	response := map[string]interface{}{
		"status":          "healthy",
		"server_count":    len(servers),
		"catalog_version": "2.0.0",
		"api_version":     "v1",
	}
	
	json.NewEncoder(w).Encode(response)
}

func listServersHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	w.Header().Set("Content-Type", "application/json")
	
	var result []Server
	for serverID, configInterface := range servers {
		config := configInterface.(map[string]interface{})
		
		server := Server{
			ID:          serverID,
			Name:        getString(config, "name", serverID),
			Description: getString(config, "description", ""),
			Category:    getString(config, "category", "other"),
			Vendor:      getString(config, "vendor", "community"),
			Homepage:    getString(config, "homepage", ""),
		}
		result = append(result, server)
	}
	
	json.NewEncoder(w).Encode(result)
}

func getServerHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	w.Header().Set("Content-Type", "application/json")
	
	// Extract server ID from path
	pathParts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(pathParts) < 4 {
		http.Error(w, "Invalid path", http.StatusBadRequest)
		return
	}
	serverID := pathParts[3]
	
	configInterface, exists := servers[serverID]
	if !exists {
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{
			"error": fmt.Sprintf("Server '%s' not found", serverID),
		})
		return
	}
	
	config := configInterface.(map[string]interface{})
	
	server := Server{
		ID:          serverID,
		Name:        getString(config, "name", serverID),
		Description: getString(config, "description", ""),
		Category:    getString(config, "category", "other"),
		Vendor:      getString(config, "vendor", "community"),
		Homepage:    getString(config, "homepage", ""),
		License:     getString(config, "license", "Unknown"),
		Config:      config,
	}
	
	json.NewEncoder(w).Encode(server)
}

func searchServersHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	w.Header().Set("Content-Type", "application/json")
	
	query := r.URL.Query().Get("q")
	category := r.URL.Query().Get("category")
	
	if query == "" && category == "" {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{
			"error": "Query parameter 'q' or 'category' required",
		})
		return
	}
	
	var results []Server
	for serverID, configInterface := range servers {
		config := configInterface.(map[string]interface{})
		
		// Check query match
		matchesQuery := true
		if query != "" {
			queryLower := strings.ToLower(query)
			matchesQuery = strings.Contains(strings.ToLower(serverID), queryLower) ||
				strings.Contains(strings.ToLower(getString(config, "name", "")), queryLower) ||
				strings.Contains(strings.ToLower(getString(config, "description", "")), queryLower)
		}
		
		// Check category filter
		matchesCategory := category == "" || getString(config, "category", "other") == category
		
		if matchesQuery && matchesCategory {
			server := Server{
				ID:          serverID,
				Name:        getString(config, "name", serverID),
				Description: getString(config, "description", ""),
				Category:    getString(config, "category", "other"),
				Vendor:      getString(config, "vendor", "community"),
				Homepage:    getString(config, "homepage", ""),
			}
			results = append(results, server)
		}
	}
	
	response := map[string]interface{}{
		"results":  results,
		"total":    len(results),
		"query":    query,
		"category": category,
	}
	
	json.NewEncoder(w).Encode(response)
}

func generateConfigHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	w.Header().Set("Content-Type", "application/json")
	
	if r.Method == "OPTIONS" {
		return
	}
	
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	var requestData map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}
	
	serversInterface, ok := requestData["servers"]
	if !ok {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{
			"error": "Missing 'servers' in request body",
		})
		return
	}
	
	serversArray := serversInterface.([]interface{})
	formatType := getString(requestData, "format", "claude_desktop")
	
	config := map[string]interface{}{
		"mcpServers": make(map[string]interface{}),
	}
	mcpServers := config["mcpServers"].(map[string]interface{})
	
	for _, serverInterface := range serversArray {
		serverID := serverInterface.(string)
		if serverConfig, exists := servers[serverID]; exists {
			mcpConfig := map[string]interface{}{
				"command": "npx",
				"args":    []string{"-y", fmt.Sprintf("@modelcontextprotocol/server-%s", serverID)},
			}
			mcpServers[serverID] = mcpConfig
		}
	}
	
	response := map[string]interface{}{
		"format":             formatType,
		"config":             config,
		"servers_included":   serversArray,
		"installation_notes": fmt.Sprintf("Add this to your %s configuration file", formatType),
	}
	
	json.NewEncoder(w).Encode(response)
}

func categoriesHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	w.Header().Set("Content-Type", "application/json")
	
	categories := make(map[string]int)
	for _, configInterface := range servers {
		config := configInterface.(map[string]interface{})
		category := getString(config, "category", "other")
		categories[category]++
	}
	
	var result []map[string]interface{}
	for category, count := range categories {
		result = append(result, map[string]interface{}{
			"name":  category,
			"count": count,
		})
	}
	
	json.NewEncoder(w).Encode(result)
}

func getString(m map[string]interface{}, key, defaultValue string) string {
	if val, ok := m[key]; ok {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return defaultValue
}

func main() {
	loadServers()
	
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/api/v1/servers", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/v1/servers" {
			listServersHandler(w, r)
		} else {
			getServerHandler(w, r)
		}
	})
	http.HandleFunc("/api/v1/servers/", getServerHandler)
	http.HandleFunc("/api/v1/servers/search", searchServersHandler)
	http.HandleFunc("/api/v1/servers/generate-config", generateConfigHandler)
	http.HandleFunc("/api/v1/categories", categoriesHandler)
	
	fmt.Printf("🚀 Starting Go REST API with %d servers\n", len(servers))
	fmt.Println("📡 No OpenAPI generation built-in - use traffic capture!")
	fmt.Println("")
	fmt.Println("Available endpoints:")
	fmt.Println("  GET  /health")
	fmt.Println("  GET  /api/v1/servers")
	fmt.Println("  GET  /api/v1/servers/{id}")
	fmt.Println("  GET  /api/v1/servers/search?q=...")
	fmt.Println("  POST /api/v1/servers/generate-config")
	fmt.Println("  GET  /api/v1/categories")
	fmt.Println("")
	fmt.Println("Capture traffic with:")
	fmt.Println("  cd ../../generative-openapi && ./quick-capture.sh")
	fmt.Println("")
	
	log.Fatal(http.ListenAndServe(":8000", nil))
}