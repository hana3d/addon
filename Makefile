.DEFAULT_GOAL := help
.PHONY: update

###################################################################################################
## SCRIPTS
###################################################################################################

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([\w-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		line = '{: <20} {}'.format(target, help)
		line = re.sub(r'^({})'.format(target), '\033[96m\\1\033[m', line)
		print(line)
endef

###################################################################################################
## VARIABLES
###################################################################################################

export PYTHON=python
export PRINT_HELP_PYSCRIPT
export BLENDER_VERSION=2.90
BLENDER_SCRIPTS_PATH ?= $(shell dirname $(shell readlink -f $(shell which blender)))/$(BLENDER_VERSION)/scripts/
STAGE ?= production
HANA3D_DESCRIPTION=$(shell sed -e 's/HANA3D_DESCRIPTION: \(.*\)/\1/' -e 'tx' -e 'd' -e ':x' config/$(STAGE).yml)
HANA3D_NAME=$(shell sed -e 's/HANA3D_NAME: \(.*\)/\1/' -e 'tx' -e 'd' -e ':x' config/$(STAGE).yml)

###################################################################################################
## GENERAL COMMANDS
###################################################################################################

help: ## show this message
	@$(PYTHON) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)


lint: ## lint code
	git diff -U0 $(STAGE).. | flake8 --diff
	flake8 --diff .
	isort .
	xenon --max-absolute C --max-modules B --max-average A *.py --exclude addon_updater.py,addon_updater_ops.py,ui.py,search.py


test: ## test code
	HANA3D_ENV=$(STAGE) blender -b -P tests/install.py -noaudio


clean: ## clean blender Hana3D addons
	rm -r $(BLENDER_SCRIPTS_PATH)/addons/hana3d_$(STAGE) || true
	rm -r $(BLENDER_SCRIPTS_PATH)/presets/hana3d_$(STAGE) || true


build: ## build addon according to stage
	rm -r hana3d_$(STAGE) || true
	# create addon folder
	mkdir hana3d_$(STAGE)
	# copy relevant files to addon folder
	find . \( -name '*.py' -o -name '*.png' -o -name '*.blend' -o -name '*.yml' \) | xargs cp --parents -t hana3d_$(STAGE)
	# replace addon description strings: static properties are evaluated before runtime
	LC_ALL=C sed -i "s/\(\".*\)Hana3D\(.*\"\)/\1$(HANA3D_DESCRIPTION)\2/g" hana3d_$(STAGE)/__init__.py
	# zip addon folder
	zip -rq hana3d_$(STAGE).zip hana3d_$(STAGE)
	# copy to ~/Downloads for easy manual install
	cp hana3d_$(STAGE).zip ~/Downloads || true
	rm -r hana3d_$(STAGE)


install: ## install the addon on blender
	mkdir -p $(BLENDER_SCRIPTS_PATH)/addons
	unzip -q hana3d_$(STAGE).zip -d $(BLENDER_SCRIPTS_PATH)/addons


e2e: ## run E2E tests
	curl -H "Authorization: token $(HANA3D_BOT_ACCESS_TOKEN)" --request POST --data '{"event_type": "$(STAGE)"}' https://api.github.com/repos/hana3d/e2e-tests/dispatches