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
export BLENDER_ADDON_PATH=$(HOME)/Library/Application\ Support/Blender/$(BLENDER_VERSION)/scripts/addons
STAGE ?= production

###################################################################################################
## GENERAL COMMANDS
###################################################################################################

help: ## show this message
	@$(PYTHON) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)


clean: ## clean blender Hana3D addons
	rm -r $(BLENDER_ADDON_PATH)/hana3d* || true


build: ## build addon according to stage
	rm -r hana3d_$(STAGE) || true
	mkdir hana3d_$(STAGE)
	find . \( -name '*.py' -o -name '*.png' -o -name '*.blend' \) | xargs cp --parents -t hana3d_$(STAGE)
	find hana3d_$(STAGE) -type f -name autothumb.py -print0 | LC_ALL=C xargs -0 sed -i.bak "s/from \. /from hana3d_$(STAGE) /g"
	find hana3d_$(STAGE) -type f -name autothumb.py -print0 | LC_ALL=C xargs -0 sed -i.bak "s/from \./from hana3d_$(STAGE)./g"
	zip -rq hana3d_$(STAGE).zip hana3d_$(STAGE)
	rm -r hana3d_$(STAGE)


install: ## install the addon on blender
	mkdir -p $(BLENDER_ADDON_PATH)
	unzip -q hana3d_$(STAGE).zip -d $(BLENDER_ADDON_PATH)
