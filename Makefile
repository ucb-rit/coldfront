# Per-clone overrides (gitignored). Create with: echo "PROJECT := brc-dev" > local.mk
-include local.mk

# Fallback if local.mk doesn't set PROJECT
PROJECT ?= brc-dev

COMPOSE_FILE = bootstrap/development/docker/docker-compose.yml
COMPOSE      = docker compose -f $(COMPOSE_FILE) -p $(PROJECT)

.PHONY: up up-d down restart logs shell db-shell setup build load-db check help

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

up: ## Start the stack (foreground)
	$(COMPOSE) up

up-d: ## Start the stack (detached)
	$(COMPOSE) up -d

down: ## Stop and remove containers
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

logs: ## Tail logs for all services
	$(COMPOSE) logs -f

shell: ## Shell into the app-shell container
	$(COMPOSE) exec app-shell bash

db-shell: ## Shell into the db-postgres-shell container
	$(COMPOSE) exec db-postgres-shell bash

setup: ## Run Django setup scripts (migrate, initial_setup, etc.)
	sh bootstrap/development/docker/scripts/docker_run_django_scripts.sh $(PROJECT)

build: ## Build Docker images  (optional: make build TAG=my-tag)
	sh bootstrap/development/docker/scripts/build_images.sh $(TAG)

load-db: ## Load a DB dump  (usage: make load-db DUMP=YYYY_MM_DD-HH-MM.dump)
	sh bootstrap/development/docker/scripts/docker_load_database_backup.sh $(PROJECT) $(DUMP)

check: ## Run pre-commit hooks on all files
	pre-commit run --all-files
