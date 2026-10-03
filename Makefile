# Development tasks. `make` on its own lists them.
#
# Set your Pi once in local.mk (not committed), e.g.
#   PI = ringer@bathwick-towerboard.local
# or per command: make deploy PI=ringer@bathwick-towerboard.local

PI ?= ringer@towerboard.local
KEY ?= $(HOME)/.ssh/tower-release
-include local.mk
PI_HOST = $(lastword $(subst @, ,$(PI)))

.DEFAULT_GOAL := help
.PHONY: help setup test serve rt render build deploy status logs reboot ssh ssh-key

help: ## List the tasks
	@grep -E '^[a-z-]+:.*## ' $(firstword $(MAKEFILE_LIST)) | sed -E 's/^([^:]+):.*## /  make \1\t/' | expand -t 20
	@echo "  Pi: $(PI)"

setup: ## Install Python and dependencies for development
	uv sync

test: ## Run the test suite
	uv run python -m unittest discover -s tests

serve: ## Run the web app on the Mac at http://localhost:8080
	uv run python -m tower serve --dev

rt: ## Run the sound process on the Mac with pretend sensors (silent; drives the wall display)
	uv run python -m tower rt --dev --source synthetic

render: ## Render 30 s of synthetic ringing to touch.wav and play it
	uv run python -m tower rt --render touch.wav --seconds 30 && afplay touch.wav

build: ## Build a signed release into dist/
	uv run python -m tower.release build --key $(KEY)

deploy: test ## Test, build, install on the Pi and wait for its health check
	TOWER_SIGNING_KEY=$(KEY) scripts/deploy-dev.sh $(PI)

status: ## Show the Pi's services and health
	@ssh $(PI) 'systemctl --no-pager status tower tower-rt tower-kiosk | grep -E "●|Active"; curl -s localhost/api/health; echo'

logs: ## Follow the Pi's app and sound logs (Ctrl-C to stop)
	ssh -t $(PI) 'journalctl -f -u tower -u tower-rt -u tower-update'

reboot: ## Restart the Pi (asks for its sudo password) and wait until it's back
	@# -t gives sudo a terminal to ask for the password. The connection drops as the Pi goes down.
	@ssh -t $(PI) 'sudo systemctl reboot' || true
	@echo "waiting for the Pi to go down…"
	@for i in $$(seq 1 30); do curl -s --max-time 2 -o /dev/null http://$(PI_HOST)/api/health || break; sleep 2; done
	@echo "waiting for it to come back (usually about a minute)…"
	@start=$$(date +%s); \
	for i in $$(seq 1 60); do \
	  sleep 5; \
	  if curl -s --max-time 3 -o /dev/null http://$(PI_HOST)/api/health; then \
	    echo "back after $$(( $$(date +%s) - start + 5 )) s"; exit 0; fi; \
	done; \
	echo "not back after 5 minutes: check the Pi's screen, or that your Mac is on the same network"; exit 1

ssh: ## Log in to the Pi
	ssh $(PI)

ssh-key: ## Set up password-free SSH login to the Pi (once)
	@test -f $(HOME)/.ssh/id_ed25519.pub || ssh-keygen -t ed25519 -f $(HOME)/.ssh/id_ed25519 -N ""
	ssh-copy-id -i $(HOME)/.ssh/id_ed25519.pub $(PI)
