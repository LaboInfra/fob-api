init:
	rm -rf db.sqlite3
	poetry install
	poetry run python -m fob_api admin@laboinfra.net admin admin

serv:
	poetry run python -m uvicorn fob_api.main:app --reload
