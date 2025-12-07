WEBHOOK_SECRET ?= testsecret

.PHONY: up down logs test

up:
	@echo "Building and starting Docker Compose stack..."
	docker compose up -d --build

down:
	@echo "Stopping and removing Docker Compose stack and volumes..."
	docker compose down 

logs:
	@echo "Tailing logs for 'api' service..."
	docker compose logs -f api

test:
	@echo "Running tests..."
	WEBHOOK_SECRET=$(WEBHOOK_SECRET) DATABASE_URL="sqlite:///./test.db" python -m pytest