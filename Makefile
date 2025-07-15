dev-up: dev-mongo-up
	source .venv/bin/activate && uvicorn app.server:app --port 8000 --reload

dev-mongo-up:
	if [ "$$(docker ps -q -f name=mongodb-test)" ]; then \
		echo "MongoDB is already running"; \
	else \
		docker run --name mongodb-dev -d -p 27017:27017 \
			-e MONGO_INITDB_ROOT_USERNAME=admin \
			-e MONGO_INITDB_ROOT_PASSWORD=gngdevpass12 \
			mongo:latest; \
	fi

dev-mongo-down:
	docker stop mongodb-test
	docker rm mongodb-test

dev-mongo-clean:
	docker stop mongodb-test
	docker rm mongodb-test
	docker rmi mongo:latest