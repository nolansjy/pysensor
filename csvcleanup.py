from datetime import date,datetime,timedelta
from pathlib import Path

from logger import logger

def main():
    source = Path('~/pysensor/backup/').expanduser()
    backup_files = sorted(source.iterdir(),reverse=True)
    oldfiles = backup_files[31::]

    if oldfiles:

        for oldfile in oldfiles:
            filename = oldfile.stem 
            oldfile.unlink()
            logger.info(f"Deleted {filename}")



if __name__ == '__main__':
    main()
        
