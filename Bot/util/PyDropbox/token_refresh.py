import requests
from ..secret import Secret

def refresh_access_token():
    # Dropbox token endpoint
    TOKEN_URL = 'https://api.dropbox.com/oauth2/token'

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': Secret.dropbox_refresh_token,
        'client_id': Secret.dropbox_app_key,
        'client_secret': Secret.dropbox_app_secret,
    }

    response = requests.post(TOKEN_URL, data=data)

    # Check if the request was successful
    if response.status_code == 200:
        new_tokens = response.json()
        access_token = new_tokens['access_token']
        Secret.dropbox_oauth2_accesstoken = access_token
        return access_token

    return None