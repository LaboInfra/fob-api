env:
	make init

init:
	@echo "Remove old .env"
	rm -rfv .env

	@echo "Create .env"
	@echo "DATABASE_URL=mysql+pymysql://fastonboard:fastonboard@mariadb:3306/fastonboard" >> .env
	@echo "JWT_SECRET_KEY=dev_secret_key" >> .env
	@echo "CELERY_BROKER_URL=redis://redis:6379" >> .env
	@echo "CELERY_RESULT_BACKEND=redis://redis:6379" >> .env
	@echo "MAIL_PORT=1025" >> .env
	@echo "MAIL_SERVER=maildev" >> .env
	@echo "MAIL_USERNAME=dev@laboinfra.net" >> .env
	@echo "MAIL_STARTTLS=no" >> .env
	#@docker exec -it headscale headscale --config /etc/headscale/headscale.yml apikeys create -o json | tr -d '"' > tmp_headscale_secret
	#@echo "HEADSCALE_TOKEN=$(cat tmp_headscale_secret)" >> .env
	@echo "HEADSCALE_ENDPOINT=http://headscale:8080" >> .env


	@echo "Add adminrc in .env"
	@cat adminrc >> .env
	@sed -i 's/export //g' .env

	@echo "Poetry install libs for api"
	@poetry install
	@echo "Run database migration"
	poetry run alembic upgrade head

admin:
	@echo "Create default superuser"
	poetry run python -m fob_api contact@laboinfra.net contact contact

serv:
	poetry run python -m uvicorn fob_api.main:app --reload

worker:
	poetry run celery -A fob_api.worker worker --loglevel=info

beat:
	poetry run celery -A fob_api.worker beat --loglevel=info

flower:
	poetry run celery -A fob_api.worker flower

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

docker:
	@echo "Build docker image"
	@sudo docker build -t fastonboard .

test:
	poetry run pytest -v -W ignore::DeprecationWarning
