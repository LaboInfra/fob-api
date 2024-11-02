init:
	@echo "Remove old .env"
	rm -rfv .env

	@echo "Create .env"
	@echo "DATABASE_URL=mysql+pymysql://fastonboard:fastonboard@mariadb:3306/fastonboard" >> .env
	@echo "SECRET_KEY=dev_secret_key" >> .env
	@echo "CELERY_BROKER_URL=redis://redis:6379" >> .env
	@echo "CELERY_RESULT_BACKEND=redis://redis:6379" >> .env
	@echo "FIREZONE_ENDPOINT=http://firezone:13000/v0" >> .env
	@echo "FIREZONE_DOMAIN=dev" >> .env

	@echo "Create Install libs for api"
	poetry install
	@echo "Run database migration"
	poetry run alembic upgrade head
	@echo "Create default superuser"
	poetry run python -m fob_api admin@laboinfra.net admin admin

	@echo "Config firezone for dev"
	sudo docker exec -it firezone bin/migrate
	sudo docker exec -it firezone bin/create-or-reset-admin
	sudo docker exec -it firezone bin/create-api-token > .token

	@echo "Patch .env by adding FIREZONE TOKEN"
	@echo "FIREZONE_TOKEN=$$(cat .token)" >> .env
	rm -fv .token

serv:
	poetry run python -m uvicorn fob_api.main:app --reload

worker:
	celery -A fob_api.worker worker --loglevel=info

flower:
	celery -A fob_api.worker flower

migrate:
	poetry run alembic upgrade head

.PHONY: migration

migration:

	@if [ -z "$(name)" ]; then \
		echo "Error: name is not set"; \
		echo "Usage: make migration name=<name>"; \
		exit 1; \
	fi
	poetry run alembic revision --autogenerate -m "$(name)"
