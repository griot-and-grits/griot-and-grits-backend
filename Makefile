DEV_MONGO_USER=admin
DEV_MONGO_PASSWORD=gngdevpass12
DEV_MONGO_URI=mongodb://$(DEV_MONGO_USER):$(DEV_MONGO_PASSWORD)@localhost:27017/
dev-up: dev-mongo-up
	source .venv/bin/activate && DB_URI=$(DEV_MONGO_URI) DB_NAME=gngdb uvicorn app.server:app --port 8000 --reload

dev-down: dev-mongo-down

dev-mongo-up:
	if [ "$$(docker ps -q -f name=mongodb-dev)" ]; then \
		echo "✅ MongoDB is already running"; \
	else \
		docker run --name mongodb-dev -d -p 27017:27017 \
			-e MONGO_INITDB_ROOT_USERNAME=$(DEV_MONGO_USER) \
			-e MONGO_INITDB_ROOT_PASSWORD=$(DEV_MONGO_PASSWORD) \
			mongo:latest; \
	fi
dev-mongo-down:
	docker stop mongodb-test
	docker rm mongodb-test

dev-mongo-clean:
	docker stop mongodb-test
	docker rm mongodb-test
	docker rmi mongo:latest

download-openapi:
	process_id=$(lsof -t -i:8000)
	if [ -z $(process_id) ]; then
		echo "Barta backend is not running on port 8000"
		exit 1
	fi
	curl -o openapi.json http://localhost:8000/openapi.json

download-json:
	curl -o openapi.json http://localhost:8000/openapi.json

install-eslint:
	npm install --save-dev eslint @eslint/js typescript typescript-eslint

generate-client: download-json
	docker run \
		--rm \
		-v $(PWD):/local \
		--network=host \
		--user $(shell id -u):$(shell id -g) \
		openapitools/openapi-generator-cli generate \
		-i /local/openapi.json \
		-g typescript-fetch \
		-o /local/npm/gng-client

lint:
	npx eslint npm/gng-client --ext .ts

lint-fix:
	npx eslint npm/gng-client --ext .ts --fix