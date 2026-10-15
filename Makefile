.DEFAULT_GOAL := run
.PHONY: run test down logs verify-docker

run test down logs verify-docker:
	$(MAKE) -C track_2a $@
