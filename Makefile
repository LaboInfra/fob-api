init:
    # api config
	rm -rf db.sqlite3
	poetry install
	poetry run python -m fob_api admin@laboinfra.net admin admin

    # firezone config
	sudo docker exec -it firezone bin/migrate
	sudo docker exec -it firezone bin/create-or-reset-admin
	sudo docker exec -it firezone bin/create-api-token > .token

serv:
	poetry run python -m uvicorn fob_api.main:app --reload

worker:
	poetry run celery -A fob_api.worker worker --loglevel=debug
