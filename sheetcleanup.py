from datetime import date,datetime,timedelta
from pathlib import Path

from logger import logger
from gwrapper import Drive
from driver import Send
from googleapiclient.errors import HttpError

def main():

    folder = Drive(Send.DRIVE_FOLDER_ID)
    sheets = folder.get_sheets()
    oldsheets = sheets[31::]
    if oldsheets:
        for sheet in oldsheets:
            sheetname = sheet.get('name')
            sheetID = sheet.get('id')
            folder.trash_file(sheetID)
            logger.info(f'Trashed sheet {sheetname}')


if __name__ == '__main__':
    try:
        main()
    except HttpError as error:
        logger.error(error)
        
