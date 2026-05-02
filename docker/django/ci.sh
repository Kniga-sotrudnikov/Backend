#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

# Initializing global variables and functions:
: "${DJANGO_ENV:=development}"

# Fail CI if `DJANGO_ENV` is not set to `development`:
if [ "$DJANGO_ENV" != 'development' ]; then
  echo 'DJANGO_ENV is not set to development. Running tests is not safe.'
  exit 1
fi

pyclean () {
  # Cleaning cache:
  find . \
    | grep -E '(__pycache__|\.(mypy_|pytest_)?cache|\.(hypothesis|perm|static)|\.py[cod]$)' \
    | xargs rm -rf \
  || true
}

run_ci () {
  echo '[ci started]'
  set -x  # we want to print commands during the CI process.

  # Testing filesystem and permissions:
  touch .perm && rm -f .perm
  touch '/var/www/django/media/.perm' && rm -f '/var/www/django/media/.perm'
  touch '/var/www/django/static/.perm' && rm -f '/var/www/django/static/.perm'

  # Checking `.env` files:
  dotenv-linter .env .env.example

  # Running linting for all python files in the project:
  ruff check --exit-non-zero-on-fix
  ruff format --check --diff
  ## flake8 .

  # Running type checking, see https://github.com/typeddjango/django-stubs
  # mypy .

  # Running tests:
  pytest

  # Run checks to be sure we follow all django's best practices:
  python backend/manage.py check --fail-level WARNING

  # Check that all migrations are made:
  python backend/manage.py makemigrations --dry-run --check

  # Check that all migrations are backwards compatible:
  # python manage.py lintmigrations

  # Check production settings for gunicorn:
  gunicorn --check-config --config python:docker.django.gunicorn_config employeebook.wsgi

  # Checking dependencies status:
  pip check

  # Checking docs:
  ## doc8 -q docs

  # Checking `yaml` files:
  # yamllint -d '{"extends": "default", "ignore": ".venv"}'  .

  set +x
  echo '[ci finished]'
}

# Remove any cache before the script:
pyclean

# Clean everything up:
trap pyclean EXIT INT TERM

# Run the CI process:
run_ci
