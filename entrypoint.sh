#!/bin/bash

# if any of the commands in your code fails for any reason, the entire script fails
set -o errexit
# fail exit if one of your pipe command fails
set -o pipefail

app=$(echo $APP | tr '[:upper:]' '[:lower:]')

ENVS=("APP" "CELERY_BROKER_URL" "CELERY_RESULT_BACKEND")
# check if all ENV var are set
for env in ${ENVS[@]}; do
  if [ -z "${!env}" ]; then
    echo "Missing $env env variable"
    exit 1
  fi
done

export DISABLE_DOTENV=True

# switch
case $app in
  "worker")
    echo "Starting worker"
    exec celery -A fob_api.worker worker --loglevel=info -E $@
    ;;
  "beat")
    echo "Starting beat"
    exec celery -A fob_api.worker beat --loglevel=info $@
    ;;
  "flower")
    echo "Starting flower"
    exec celery -A fob_api.worker flower $@
    ;;
  "api")
    echo "Starting web"
    # make migrations
    alembic upgrade head
    exec uvicorn fob_api.main:app --host 0.0.0.0 --port 8000 $@
    ;;
    *)
        echo "Invalid APP env variable"
        echo "Please set APP env variable to one of the following values: worker, beat, flower, api"
        exit 1
        ;;
    esac

echo "Container exited (why?) :3"
