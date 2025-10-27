# Makefile for AI4Pricing (Windows-friendly)

# Variables
YEARS ?= 2025
LOGS_DIR ?= logs
OUTPUT_DIR ?= outputData
COMPARISON_DIR ?= comparison_results
ECONOMIC_DIR ?= economic_analysis

# Colores desactivados en Windows
GREEN :=
YELLOW :=
BLUE :=
RESET :=

ifeq ($(OS),Windows_NT)
    MKDIR_P = if not exist "$(1)" mkdir "$(1)"
    RM_RF = rmdir /S /Q "$(1)"
    SHELL := cmd.exe
    .SHELLFLAGS := /C
else
    MKDIR_P = mkdir -p $(1)
    RM_RF = rm -rf $(1)
endif

# Default target
help:
	@echo "AI4Pricing Makefile (Windows)"
	@echo "Available commands:"
	@echo "  make start-api           - Starts the API stack"
	@echo "  make stop-api            - Stops the API stack"
	@echo "  make transform           - Runs the pricing transformation script"
	@echo "  make compare             - Runs the pricing comparison script"
	@echo "  make economic-analysis   - Runs the economic analysis"
	@echo "  make full-pipeline       - Runs the full pipeline"
	@echo "  make clean               - Cleans output directories"
	@echo "  make help                - Shows this help"

# Starts the API stack
start-api:
	@echo "Starting the API stack..."
	@docker network create a-mint-network || echo "Network already exists"
	@docker compose -f docker-compose.yml up -d
	@echo "A-MINT running at http://localhost:8001"
	@echo "Choco API at http://localhost:8000"
	@echo "Analysis API at http://localhost:8002"
	@echo "Frontend at http://localhost:80"

# Stops the API stack
stop-api:
	@echo "Stopping the API stack..."
	@docker compose -f docker-compose.yml down
	@docker compose -f scripts/docker-compose.yml down --remove-orphans
	@docker network rm a-mint-network || echo "No network"
	@echo "API stopped"

# Runs the transformation script
transform:
	@echo "Running transformation for years: $(YEARS)..."
	@$(call MKDIR_P,$(OUTPUT_DIR))
	@$(call MKDIR_P,$(LOGS_DIR))
	@docker compose -f scripts/docker-compose.yml run transform /app/scripts/transform_all_pricings.py --years $(YEARS)
	@echo "Transformation completed. Results in $(OUTPUT_DIR)"

# Runs the comparison script
compare:
	@echo "Running comparison for years: $(YEARS)..."
	@$(call MKDIR_P,$(COMPARISON_DIR))
	@docker compose -f scripts/docker-compose.yml run compare /app/scripts/compare_pricings.py --years $(YEARS)
	@echo "Comparison completed. Results in $(COMPARISON_DIR)"

# Runs the economic analysis
economic-analysis:
	@echo "Running economic analysis..."
	@$(call MKDIR_P,$(ECONOMIC_DIR))
	@docker compose -f scripts/docker-compose.yml run economic-analysis /app/scripts/economic_analysis.py --logs-dir /app/$(LOGS_DIR) --output-dir /app/$(ECONOMIC_DIR)
	@echo "Economic analysis completed. Results in $(ECONOMIC_DIR)"

# Runs the full pipeline
full-pipeline:
	@echo "Starting full pipeline for years: $(YEARS)..."
	@make transform YEARS=$(YEARS)
	@make compare YEARS=$(YEARS)
	@make economic-analysis
	@echo "Full pipeline finished. Results in:"
	@echo "- Transformation: $(OUTPUT_DIR)"
	@echo "- Comparison: $(COMPARISON_DIR)"
	@echo "- Economic analysis: $(ECONOMIC_DIR)"

# Cleans output directories
clean:
	@echo "Cleaning output directories..."
	@$(call RM_RF,$(OUTPUT_DIR))
	@$(call RM_RF,$(COMPARISON_DIR))
	@$(call RM_RF,$(ECONOMIC_DIR))
	@echo "Directories cleaned"