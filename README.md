# FastOnBoard-API

This is a simple api to manage users for the laboinfra cloud

with this api you can:

- register yourself
- get your vpn
- config your account in openstack
- manage your projects
- manage your quotas

## How to use

### Environment Variables

> Check the Makefile for more information

- SECRET_KEY: a secret key to encrypt the tokens (required) use (`openssl rand -hex 32`)
- DATABASE_URL: the database url (not required) default `sqlite:///db.sqlite3`
- CELERY_BROKER_URL: the celery broker url (not required) default `redis://localhost:6379`
- CELERY_RESULT_BACKEND: the celery result backend (not required) default `redis://localhost:6379`

Dev environment:

```bash
SECRET_KEY=dev_secret_key
CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379
```
