.PHONY: demo demo-down test

demo:
	docker compose up --build

demo-down:
	docker compose down

test:
	pnpm check
