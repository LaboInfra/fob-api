FROM python:3.12-slim-bullseye AS builder

WORKDIR /app

## Install poetry
RUN apt-get update && \
    apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 -

## generate requirements.txt
COPY pyproject.toml poetry.lock ./
RUN /root/.local/bin/poetry self add poetry-plugin-export && \
    /root/.local/bin/poetry export --format=requirements.txt --output=requirements.txt

# Build the final image
FROM python:3.12-slim-bullseye

# default port for Flask
EXPOSE 8000
# default port for Flower
EXPOSE 5555

WORKDIR /app

## requirements
COPY --from=builder /app/requirements.txt .
RUN pip install -r requirements.txt && rm requirements.txt

## copy entrypoint
COPY . .
RUN chmod +x entrypoint.sh && \
    rm -rfv poetry.lock pyproject.toml

## copy app
WORKDIR /app/fob_api
COPY fob_api .

## create user
RUN useradd -m fob && chown -Rv fob:fob /app
USER fob

## run
WORKDIR /app
ENTRYPOINT ["./entrypoint.sh"]
