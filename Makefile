# Environment variables
DEV_MONGO_USER=admin
DEV_MONGO_PASSWORD=gngdevpass12
DEV_MONGO_URI=mongodb://$(DEV_MONGO_USER):$(DEV_MONGO_PASSWORD)@localhost:27017/

# Install dependencies using uv
install:
	uv pip install -e .

# Or install from requirements.txt
install-req:
	uv pip install -r requirements.txt

# Run development server with uv
dev-up: dev-mongo-up
	DB_URI=$(DEV_MONGO_URI) DB_NAME=gngdb uv run uvicorn app.server:app --port 8000 --reload

dev-up-agent: dev-mongo-up
	DB_URI=$(DEV_MONGO_URI) DB_NAME=gngdb uv run uvicorn app.server:app --port 8009 --reload

# Start MongoDB container
dev-mongo-up:
	@if [ "$$(docker ps -q -f name=mongodb-dev)" ]; then \
		echo "✅ MongoDB is already running"; \
	else \
		echo "🚀 Starting MongoDB..."; \
		docker run --name mongodb-dev -d -p 27017:27017 \
			-e MONGO_INITDB_ROOT_USERNAME=$(DEV_MONGO_USER) \
			-e MONGO_INITDB_ROOT_PASSWORD=$(DEV_MONGO_PASSWORD) \
			mongo:latest; \
		echo "✅ MongoDB started"; \
	fi

# Stop MongoDB container
dev-mongo-down:
	@echo "🛑 Stopping MongoDB..."
	@docker stop mongodb-dev || true
	@docker rm mongodb-dev || true
	@echo "✅ MongoDB stopped"

# Clean up MongoDB
dev-mongo-clean:
	@echo "🧹 Cleaning up MongoDB..."
	@docker stop mongodb-dev || true
	@docker rm mongodb-dev || true
	@docker rmi mongo:latest || true
	@echo "✅ MongoDB cleaned"

# Start MinIO for development
dev-minio-up:
	@if [ "$$(docker ps -q -f name=minio-dev)" ]; then \
		echo "✅ MinIO is already running"; \
	else \
		echo "🚀 Starting MinIO..."; \
		docker run -d \
			--name minio-dev \
			-p 9000:9000 \
			-p 9001:9001 \
			-e MINIO_ROOT_USER=minioadmin \
			-e MINIO_ROOT_PASSWORD=minioadmin \
			quay.io/minio/minio server /data --console-address ":9001"; \
		echo "✅ MinIO started (console: http://localhost:9001)"; \
		echo "⏳ Waiting for MinIO to be ready..."; \
		sleep 3; \
	fi
	@echo "📦 Setting up MinIO buckets..."
	@docker exec minio-dev sh -c 'mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null || true'
	@docker exec minio-dev sh -c 'mc mb local/artifacts 2>/dev/null || echo "  ℹ️  Bucket artifacts already exists"'
	@echo "✅ MinIO buckets ready"

# Stop MinIO
dev-minio-down:
	@echo "🛑 Stopping MinIO..."
	@docker stop minio-dev || true
	@docker rm minio-dev || true
	@echo "✅ MinIO stopped"

# Start all services
dev-services-up: dev-mongo-up dev-minio-up
	@echo "✅ All development services started"

# Stop all services
dev-services-down: dev-mongo-down dev-minio-down
	@echo "✅ All development services stopped"

# Spin everything down (services only, not API)
down: dev-services-down

# Spin everything up (services only, not API)
up: dev-services-up dev-up

# Spin everything up (services only, not API)
up-agent: dev-services-up dev-up-agent

# Run tests
test:
	uv run pytest

# Show help
help:
	@echo "Griot and Grits Backend - Make Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install dependencies with uv"
	@echo "  make sync             - Sync dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev-up           - Start API server"
	@echo "  make dev-services-up  - Start MongoDB + MinIO"
	@echo ""
	@echo "Services:"
	@echo "  make dev-mongo-up     - Start MongoDB"
	@echo "  make dev-minio-up     - Start MinIO"
	@echo "  make dev-services-down- Stop all services"
	@echo ""

.PHONY: install dev-up dev-mongo-up dev-mongo-down dev-minio-up dev-minio-down \
        dev-services-up dev-services-down up down test help