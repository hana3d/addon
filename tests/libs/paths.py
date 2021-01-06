import os

API_URL_DEV = 'https://staging-api.hana3d.com'
API_URL_PRODUCTION = 'https://api.hana3d.com'

AUTH_AUDIENCE_DEV = "https://staging-hana3d.com"
AUTH_AUDIENCE_PRODUCTION = "https://hana3d.com"

HANA3D_NAME_DEV = 'hana3d_dev'
HANA3D_NAME_PRODUCTION = 'hana3d_production'


def get_api_url():
    if os.getenv('HANA3D_ENV') == 'dev':
        return API_URL_DEV

    if os.getenv('HANA3D_ENV') == 'production':
        return API_URL_PRODUCTION


def get_audience_url():
    if os.getenv('HANA3D_ENV') == 'dev':
        return AUTH_AUDIENCE_DEV

    if os.getenv('HANA3D_ENV') == 'production':
        return AUTH_AUDIENCE_PRODUCTION


def get_addon_name():
    if os.getenv('HANA3D_ENV') == 'dev':
        return HANA3D_NAME_DEV

    if os.getenv('HANA3D_ENV') == 'production':
        return HANA3D_NAME_PRODUCTION
