from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pathlib import Path

SERVICE_ACCOUNT_FILE = Path('~/pysensor/.pysensor-service-creds.json').expanduser()
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

class Sheets:

    def __init__(self, sheetId):
        """Builds the sheet service and stores the ID of the current targeted sheet."""
        self.service = build('sheets','v4',credentials=creds, cache_discovery=False)
        self.sheetId = sheetId
        
    #append module
    def append(self, range_, valueInputOption_ = 'USER_ENTERED', insertDataOption_ ='OVERWRITE', **kwargs):
        """Wraps the append() model and takes a range and body input."""
        res = self.service.spreadsheets().values().append(
        spreadsheetId=self.sheetId,
        range=range_,
        valueInputOption=valueInputOption_,
        insertDataOption=insertDataOption_,
        **kwargs
        ).execute()      
        
        return res
    
    #Generic ValueRange body
    @staticmethod
    def get_value_body(values, majorDimension_ = 'Rows'):
        """Takes values and returns a ValueRange object for it.
        Defaults to Rows majorDimension"""

        value_range_body = {
            'majorDimension':majorDimension_,
            'values':[values]
        }
        
        return value_range_body
    
    #update module        
    def update(self, range_, valueInputOption_ = 'USER_ENTERED', **kwargs):
        """Wraps the update model and takes a range and body input."""
        res = self.service.spreadsheets().values().update(
        spreadsheetId = self.sheetId,
        range = range_,
        valueInputOption=valueInputOption_,
        **kwargs
        ).execute()
        
        return res
        
    def get_cell(self, cell):
        """Returns the value contained in a specified cell."""
        res = self.service.spreadsheets().values().get(
        spreadsheetId=self.sheetId,
        range=cell
        ).execute()
        value = res.get('values',[])
        
        return value[0][0]

    def get_row(self, index):
        """Returns the row at the specified index."""
        res = self.service.spreadsheets().values().get(
        spreadsheetId=self.sheetId,
        range=f'{index}:{index}'
        ).execute()
        value = res.get('values',[])
        return value[0]
        
    def get_last_index(self):
        """Specifically used to get the last index number in a column A"""
        next_row = self.append('A1:Q1').get('updates',[]).get('updatedRange',[])
        last_row = int(next_row[-1]) - 1
        last_index = self.get_cell(f"A{last_row}")
        
        return int(last_index)

    def get_last_row(self):
        next_row = self.append('A1:Q1').get('updates',[]).get('updatedRange',[])
        last_row_index = int(next_row[-1]) - 1
        last_row = self.get_row(last_row_index)
        return last_row


class Drive:

    def __init__(self, folderId):
        """Builds the drive service and stores the ID of the current targeted drive folder."""
        self.service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        self.folderId = folderId
    
    def create_sheet(self, filename):
        """Creates a sheet with the specified filename in the folder."""
        file_metadata = {
            'name': filename, 
            'parents': [self.folderId], 
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        res = self.service.files().create(body=file_metadata).execute()
        
        return res  

    def trash_file(self, fileID):
        """Moves file with file ID to Trash"""
        update_body = {'trashed': True}

        res = drive_service.files().update(
        supportsAllDrives=True,
        fileId=fileID,
        body=update_body
        ).execute()

        return res

    
    def get_sheets(self):
        """Get list of sheets in the folder sorted by name descending."""
        res = self.service.files().list(
        q=f'"{self.folderId}" in parents and mimeType = "application/vnd.google-apps.spreadsheet"',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        spaces='drive',
        orderBy='name desc',
        pageSize=32,
        fields='files(id, name)'
        ).execute()
        
        return res.get('files', [])
    
    def get_file_by_name(self, filename):
        """Get File object by its name. Returns File(id,name) dict."""
        res = self.service.files().list(
        q=f'"{self.folderId}" in parents and name = "{filename}"',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        spaces='drive',
        fields='files(id, name)'
        ).execute()
        
        return res.get('files', [])
        
        
