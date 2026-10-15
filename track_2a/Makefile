.DEFAULT_GOAL := run
DOCKER ?= docker
COMPOSE = $(DOCKER) compose

.PHONY: run test down logs verify-docker

run:
	$(COMPOSE) up --build --wait --wait-timeout 90
	@echo Open http://localhost:$(if $(SKONY_PORT),$(SKONY_PORT),8765)

test:
	$(COMPOSE) build workbench
	$(COMPOSE) run --rm --no-deps -e LLM_API_KEY= workbench python -m unittest discover -s tests

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs --follow workbench

verify-docker:
	python scripts/check_docker.py
