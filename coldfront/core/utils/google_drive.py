# taken from https://developers.google.com/drive/api/guides/folder#create
import google.auth
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from coldfront.core.utils.common import import_from_settings


def upload_to_folder(folder_id, name, content):
    """Upload a file to the specified folder and prints file ID, folder ID
    Args: Id of the folder
    Returns: ID of the file uploaded

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    settings_keyfile_path = import_from_settings('GOOGLE_DRIVE_STORAGE_KEYFILE_PATH')
    creds = Credentials.from_service_account_file(settings_keyfile_path)

    # try:
    # create drive api client
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': name,
        'parents': [folder_id]
    }
    media = MediaIoBaseUpload(content,
                            mimetype='application/pdf', resumable=True)
    # pylint: disable=maybe-no-member
    file = service.files().create(body=file_metadata, media_body=media,
                                    fields='id').execute()
    return file.get('id')

    # except HttpError as error:
    #     print(F'An error occurred: {error}')
    #     return None