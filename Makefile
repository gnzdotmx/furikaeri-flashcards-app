.PHONY: run stop logs fmt lint test audit reset-data

run:
	docker compose up --build

stop:
	docker compose down

logs:
	docker compose logs -f --tail=200

# Format/lint use the api container with host source mounted so changes persist.
fmt:
	docker compose run --rm -v "$(PWD)/flashcards/app/api/app:/app/app:rw" api sh -c "python -m ruff format ."
	docker run --rm -v "$(PWD)/flashcards/app/web:/app" -w /app node:20-alpine sh -c "npm install --silent && npm run fmt"

lint:
	docker compose run --rm -v "$(PWD)/flashcards/app/api/app:/app/app:ro" -v "$(PWD)/flashcards/app/api/scripts:/app/scripts:ro" api sh -c "python -m ruff check ."
	docker run --rm -v "$(PWD)/flashcards/app/web:/app" -w /app node:20-alpine sh -c "npm install --silent && npm run lint"

# API: pytest in api container with host app mounted. Web: vitest in node container.
test:
	docker compose run --rm -e TESTING=1 -e COVERAGE_FILE=/tmp/.coverage -v "$(PWD)/flashcards/app/api/app:/app/app:ro" api sh -c "pytest -q --cov=app --cov-report=term-missing"
	docker run --rm -v "$(PWD)/flashcards/app/web:/app" -w /app node:20-alpine sh -c "npm install --silent && npm test --silent"

audit:
	docker compose run --rm -v "$(PWD)/flashcards/app/api/app:/app/app:ro" api sh -c "sh scripts/audit.sh"
	docker run --rm -v "$(PWD)/flashcards/app/web:/app" -w /app node:20-alpine sh -c "npm install --silent && sh scripts/audit.sh"

# Clear all deck/user data in the DB. Prompts for "yes" to confirm.
reset-data:
	docker compose run --rm api python scripts/reset_data.py

