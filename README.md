# SecurePR Order and Account Management API

A compact, layered FastAPI application for managing customer accounts and
orders. This fictional service is a standalone test repository for SecurePR
integration testing. It contains no production credentials or real customer
data and is not intended to be deployed as a production service.

## Architecture

The API routers validate HTTP requests with Pydantic schemas and call services
for business rules. Services use repositories to access SQLite through a small
database abstraction. Passwords are stored as salted PBKDF2 hashes; login
creates short-lived, in-memory bearer sessions. Roles are assigned on the
server, so public registration cannot create an administrator.

```text
HTTP request
  -> app/api/          authentication, authorization, HTTP mapping
  -> app/services/     account, order, and notification behavior
  -> app/repositories/ persistence queries
  -> app/database/     SQLite connection and transaction boundary
  -> migrations/       initial relational schema
```

### Folder structure

```text
app/
  api/          auth, users, orders, and admin endpoints
  core/         environment configuration, domain errors, and security
  database/     SQLite connection abstraction
  models/       internal user and order entities
  repositories/ data access
  schemas/      validated request and response models
  services/     business logic and notifications
migrations/     initial SQLite schema
tests/          API and service tests
docs/           SecurePR risk-testing scenarios
.github/        pull-request CI workflow
```

## Setup

Use Python 3.10 or newer. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Settings are read from environment variables: `DATABASE_PATH`,
`SESSION_TTL_SECONDS`, and `LOG_LEVEL`. The application reads the process
environment directly; copy `.env.example` as a reference and set the variables
in your shell or IDE. Do not put credentials in the example file.

## Run the application

```powershell
uvicorn app.main:app --reload
```

The local API is available at `http://127.0.0.1:8000`; interactive API
documentation is at `/docs`. The default SQLite file is created in the current
working directory and is excluded from Git.

Register with `POST /auth/register`, then log in with `POST /auth/login` to
receive a bearer token. Use it in the `Authorization: Bearer <token>` header
for account and order endpoints. Administrator accounts are not created by
public registration; tests create one directly through the service layer.

## Run tests and lint

```powershell
python -m pytest
python -m ruff check app tests
```

The GitHub Actions workflow runs dependency installation, unit tests, and Ruff
linting as separate, named checks on pull requests targeting `main`.

## SecurePR integration testing

This repository is designed to be pushed independently and connected to the
existing SecurePR GitHub App as a safe test target. It provides realistic
changes across API, authentication, authorization, data access, migrations,
configuration, and CI. Suggested PR changes at three risk levels are in
[docs/SECUREPR_TEST_SCENARIOS.md](docs/SECUREPR_TEST_SCENARIOS.md). High-risk
examples are described as hypothetical review scenarios only; no deliberately
vulnerable code or real secrets are included.

test023
