import dropbox
from ..secret import Secret

def refresh_access_token():
    dbx = dropbox.Dropbox(
        app_key=Secret.dropbox_app_key,
        app_secret=Secret.dropbox_app_secret,
        oauth2_access_token=Secret.dropbox_oauth2_accesstoken,
    )
    # The Dropbox client will automatically refresh the access token
    # Use dbx as usual for any Dropbox API calls here
    print(dbx.check_app("Authenticated"))


refresh_access_token()
