init:
	poetry install

serv:
	poetry run python -m uvicorn fob_api.main:app --reload
