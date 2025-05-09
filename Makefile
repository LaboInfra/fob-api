init:
	@make dev

clean:
	@echo "Cleaning up..."
	@echo "Removing .env"
	@rm -rf .env
	@echo "Removing tmp_headscale_secret"
	@rm -rf tmp_headscale_secret
	@echo "Removing __pycache__ and *.pyc files"
	@find . -name "__pycache__" -type d -exec rm -fr {} + -o -name "*.pyc" -exec rm -rf {} +
	@echo "Removing celerybeat-schedule files"
	@rm -rf celerybeat-schedule.*
	@echo "Removing .pytest_cache"
	@rm -rf .pytest_cache
	@echo "Removing .coverage"
	@rm -rf .coverage

dev:
	@make clean

	@echo "Create .env"
	@echo "DATABASE_URL=mysql+pymysql://fastonboard:fastonboard@mariadb:3306/fastonboard" >> .env
	@echo "JWT_SECRET_KEY=dev_secret_key" >> .env
	@echo "CELERY_BROKER_URL=redis://redis:6379" >> .env
	@echo "CELERY_RESULT_BACKEND=redis://redis:6379" >> .env
	@echo "MAIL_PORT=1025" >> .env
	@echo "MAIL_SERVER=maildev" >> .env
	@echo "MAIL_USERNAME=dev@laboinfra.net" >> .env
	@echo "MAIL_STARTTLS=no" >> .env
	@sudo docker exec -it headscale headscale --config /etc/headscale/headscale.yml apikeys create -o json | tr -d '"' > tmp_headscale_secret
	@cat tmp_headscale_secret
	@echo HEADSCALE_TOKEN=$(shell cat tmp_headscale_secret) >> .env
	@echo "HEADSCALE_ENDPOINT=http://headscale:8080" >> .env
	@rm -rfv tmp_headscale_secret

	@echo "Add adminrc in .env"
	@cat adminrc >> .env
	@sed -i 's/export //g' .env

	@make deps

prod:
	@make clean

	@if [ ! -f .prod.env ]; then \
		echo "❌ .prod.env is missing. Aborting."; \
		exit 1; \
	fi
	@echo ".prod.env found"
	@echo "Replacing .env with .prod.env"
	@cp -v .prod.env .env
	@echo "Warning you are using production env variables"

	@make deps

deps:
	@echo "Poetry install libs for api"
	@poetry install
	
admin:
	@echo "Create default superuser"
	poetry run python -m fob_api contact@laboinfra.net laboinfra_admin laboinfra_admin

serv:
	poetry run python -m uvicorn fob_api.main:app --reload

worker:
	poetry run celery -A fob_api.worker worker --loglevel=info

beat:
	poetry run celery -A fob_api.worker beat --loglevel=info

flower:
	poetry run celery -A fob_api.worker flower

migrate:
	@echo "Run database migration"
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
