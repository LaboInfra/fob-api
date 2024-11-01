init:
	@echo "Clean db and .env"
	@rm -rf db.sqlite3 .env

	@echo "Create .env"
	@echo "SECRET_KEY=dev_secret_key" > .env
	@echo "CELERY_BROKER_URL=redis://redis:6379" >> .env
	@echo "CELERY_RESULT_BACKEND=redis://redis:6379" >> .env
	@echo "FIREZONE_ENDPOINT=http://firezone:13000/v0" >> .env
	@echo "FIREZONE_DOMAIN=dev" >> .env

	@echo "Create Install libs and setup default account"
	@poetry install
	@poetry run python -m fob_api admin@laboinfra.net admin admin

	@echo "Config firezone for dev"
	@sudo docker exec -it firezone bin/migrate
	@sudo docker exec -it firezone bin/create-or-reset-admin
	@sudo docker exec -it firezone bin/create-api-token > .token

	@echo "Patch .env by adding FIREZONE TOKEN"
	@echo "FIREZONE_TOKEN=$$(cat .token)" >> .env



serv:
	poetry run python -m uvicorn fob_api.main:app --reload

worker:
	celery -A fob_api.worker worker --loglevel=info

flower:
	celery -A fob_api.worker flower