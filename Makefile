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
HANA3D_DESCRIPTION=$(shell sed -e 's/HANA3D_DESCRIPTION.*"\(.*\)\"/\1/' -e 'tx' -e 'd' -e ':x' config/$(STAGE).py)

###################################################################################################
## GENERAL COMMANDS
###################################################################################################

help: ## show this message
	@$(PYTHON) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)


clean: ## clean blender Hana3D addons
	rm -r $(BLENDER_ADDON_PATH)/hana3d_$(STAGE) || true


build: ## build addon according to stage
	rm -r hana3d_$(STAGE) || true
	# create addon folder
	mkdir hana3d_$(STAGE)
	# copy relevant files to addon folder
	find . \( -name '*.py' -o -name '*.png' -o -name '*.blend' \) | xargs cp --parents -t hana3d_$(STAGE)
	# replace config file with appropriate stage
	LC_ALL=C sed -i "" "s/from \.production/from .$(STAGE)/g" hana3d_$(STAGE)/config/__init__.py
	# replace addon description on __init__ file, as static properties are evaluated before runtime
	LC_ALL=C sed -i "" "s/\(\".*\)Hana3D\(.*\"\)/\1$(HANA3D_DESCRIPTION)\2/g" hana3d_$(STAGE)/__init__.py
	# background processes must NOT have relative imports
	find hana3d_$(STAGE) -type f -name '*_bg.py' -print0 | LC_ALL=C xargs -0 sed -i "" "s/from \. /from hana3d_$(STAGE) /g"
	find hana3d_$(STAGE) -type f -name '*_bg.py' -print0 | LC_ALL=C xargs -0 sed -i "" "s/from \./from hana3d_$(STAGE)./g"
	# zip addon folder
	zip -rq hana3d_$(STAGE).zip hana3d_$(STAGE)
	cp hana3d_$(STAGE).zip ~/Downloads
	rm -r hana3d_$(STAGE)


install: ## install the addon on blender
	mkdir -p $(BLENDER_ADDON_PATH)
	unzip -q hana3d_$(STAGE).zip -d $(BLENDER_ADDON_PATH)
