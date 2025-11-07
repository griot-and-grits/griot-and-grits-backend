# Environment variables
DEV_MONGO_USER=admin
DEV_MONGO_PASSWORD=gngdevpass12
DEV_MONGO_URI=mongodb://$(DEV_MONGO_USER):$(DEV_MONGO_PASSWORD)@localhost:27017/

# Container image variables
IMAGE_NAME=gng-api
IMAGE_TAG?=latest
NAMESPACE=griot-grits-aa488b

# OpenShift registry (does not work without access on NERC Cluster)
OPENSHIFT_REGISTRY=$(shell oc get route default-route -n openshift-image-registry -o jsonpath='{.spec.host}' 2>/dev/null)

QUAY_USER?=griot-and-grits
QUAY_REGISTRY=quay.io/$(QUAY_USER)

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

# ============================================
# Container Build and Deploy
# ============================================

# Build container image
build:
	@echo "🔨 Building container image..."
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo "✅ Built $(IMAGE_NAME):$(IMAGE_TAG)"

# Push to OpenShift internal registry
push-openshift: build
	@if [ -z "$(OPENSHIFT_REGISTRY)" ]; then \
		echo "❌ OpenShift registry route not found."; \
		echo "   Ask admin to expose registry or use 'make push-quay' instead"; \
		exit 1; \
	fi
	@echo "📤 Pushing to OpenShift registry..."
	docker login -u $(shell oc whoami) -p $(shell oc whoami -t) $(OPENSHIFT_REGISTRY)
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(OPENSHIFT_REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(OPENSHIFT_REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "✅ Pushed to $(OPENSHIFT_REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)"

# Push to Quay.io
push-quay: build
	@echo "📤 Pushing to Quay.io..."
	@echo "   Note: Run 'docker login quay.io' first if not already logged in"
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(QUAY_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(QUAY_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "✅ Pushed to $(QUAY_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)"
	@echo ""
	@echo "⚠️  Don't forget to update deployment.yaml with:"
	@echo "   image: $(QUAY_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)"

# Build and push (auto-detect registry)
push: build
	@if [ -n "$(OPENSHIFT_REGISTRY)" ]; then \
		$(MAKE) push-openshift; \
	else \
		echo "⚠️  OpenShift registry not available, using Quay.io"; \
		$(MAKE) push-quay; \
	fi

# Show help
help:
	@echo "Griot and Grits Backend - Make Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install dependencies with uv"
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
	@echo "Container Build & Deploy:"
	@echo "  make build            - Build container image"
	@echo "  make push             - Build and push (auto-detect registry)"
	@echo "  make push-openshift   - Build and push to OpenShift registry"
	@echo "  make push-quay        - Build and push to Quay.io"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run pytest"
	@echo ""

.PHONY: install dev-up dev-mongo-up dev-mongo-down dev-minio-up dev-minio-down \
        dev-services-up dev-services-down up down test help \
        build push push-openshift push-quay