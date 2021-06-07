import os

from .. import wheels

wheels.load_wheels()

config_dirname = os.path.dirname(os.path.abspath(__file__))
addon_dirname = os.path.dirname(config_dirname)
hana3d_stage = os.path.basename(addon_dirname)
_, stage = hana3d_stage.split('_')

with open(f'{config_dirname}/{stage}.yml') as f:
    lines = f.read().splitlines()

config = {}
for line in lines:
    key, value = line.split(': ')
    config[key] = value


HANA3D_NAME = config['HANA3D_NAME']
HANA3D_UI = config['HANA3D_UI']
HANA3D_ASSET = config['HANA3D_ASSET']
HANA3D_RENDER = config['HANA3D_RENDER']
HANA3D_MODELS = config['HANA3D_MODELS']
HANA3D_SCENES = config['HANA3D_SCENES']
HANA3D_MATERIALS = config['HANA3D_MATERIALS']
HANA3D_PROFILE = config['HANA3D_PROFILE']
HANA3D_DESCRIPTION = config['HANA3D_DESCRIPTION']
HANA3D_AUTH_URL = config['HANA3D_AUTH_URL']
HANA3D_AUTH_CLIENT_ID = config['HANA3D_AUTH_CLIENT_ID']
HANA3D_AUTH_AUDIENCE = config['HANA3D_AUTH_AUDIENCE']
HANA3D_PLATFORM_URL = config['HANA3D_PLATFORM_URL']
HANA3D_AUTH_LANDING = config['HANA3D_AUTH_LANDING']
HANA3D_URL = config['HANA3D_URL']
HANA3D_LOG_LEVEL = config['HANA3D_LOG_LEVEL']
