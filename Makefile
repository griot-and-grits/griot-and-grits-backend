DEV_MONGO_USER=admin
DEV_MONGO_PASSWORD=gngdevpass12
DEV_MONGO_URI=mongodb://$(DEV_MONGO_USER):$(DEV_MONGO_PASSWORD)@localhost:27017/
dev-up: dev-mongo-up
	source .venv/bin/activate && DB_URI=$(DEV_MONGO_URI) DB_NAME=gngdb uvicorn app.server:app --port 8000 --reload

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