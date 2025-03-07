env:
	make init

init:
	make clean
	@echo "Remove old .env"
	rm -rfv .env

	@echo "Start keystone"
	sudo docker exec -it keystone /var/lib/openstack/bin/keystone-manage db_sync
	sudo docker exec -it keystone /var/lib/openstack/bin/keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone
	sudo docker exec -it keystone /var/lib/openstack/bin/keystone-manage credential_setup --keystone-user keystone --keystone-group keystone
	sudo docker exec -it keystone /var/lib/openstack/bin/keystone-manage bootstrap --bootstrap-password admin --bootstrap-admin-url http://keystone:8000/v3/ --bootstrap-internal-url http://keystone:8000/v3/ --bootstrap-public-url http://keystone:8000/v3/ --bootstrap-region-id LocalDev

	@echo "Create .env"
	@echo "DATABASE_URL=mysql+pymysql://fastonboard:fastonboard@mariadb:3306/fastonboard" >> .env
	@echo "JWT_SECRET_KEY=dev_secret_key" >> .env
	@echo "CELERY_BROKER_URL=redis://redis:6379" >> .env
	@echo "CELERY_RESULT_BACKEND=redis://redis:6379" >> .env
	@echo "MAIL_PORT=1025" >> .env
	@echo "MAIL_SERVER=maildev" >> .env
	@echo "MAIL_USERNAME=dev@laboinfra.net" >> .env
	@echo "MAIL_STARTTLS=no" >> .env

	@echo "Create keystone adminrc"
	@echo "export OS_USERNAME=admin" > adminrc
	@echo "export OS_PASSWORD=admin" >> adminrc
	@echo "export OS_PROJECT_NAME=admin" >> adminrc
	@echo "export OS_USER_DOMAIN_NAME=Default" >> adminrc
	@echo "export OS_PROJECT_DOMAIN_NAME=Default" >> adminrc
	@echo "export OS_AUTH_URL=http://keystone:8000/v3/" >> adminrc
	@echo "export OS_IDENTITY_API_VERSION=3" >> adminrc

	@echo "Add adminrc in .env"
	@cat adminrc >> .env
	@sed -i 's/export //g' .env

	@if [ -f .prod.env ]; then \
		echo ".prod.env found"; \
		echo "Replacing .env with .prod"; \
		cp -v .prod.env .env; \
	fi

	@echo "Poetry install libs for api"
	@poetry install
	@echo "Run database migration"
	poetry run alembic upgrade head


admin:
	@echo "Create default superuser"
	poetry run python -m fob_api admin@laboinfra.net admin admin

serv:
	poetry run python -m uvicorn fob_api.main:app --reload

worker:
	poetry run celery -A fob_api.worker worker --loglevel=info

beat:
	poetry run celery -A fob_api.worker beat --loglevel=info

flower:
	poetry run celery -A fob_api.worker flower

keystone:
	sudo docker exec -it keystone /var/lib/openstack/bin/keystone-wsgi-public

migrate:
	poetry run alembic upgrade head

clean:
	find . -name "__pycache__" -type d -exec rm -r {} + -o -name "*.pyc" -exec rm -f {} +
	rm -f celerybeat-schedule.*

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
