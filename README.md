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

- SECRET_KEY: a secret key to encrypt the tokens (required) `openssl rand -hex 32`
- DATABASE_URL: the database url (not required) default `sqlite:///db.sqlite3`
