##NOTICE##
# You are now editing the MAIN SCRIPT of the sensor reader!

# Improper changes may cause the program  to malfunction. 
# Before making any changes, please make sure there is a backup of this script.

import time
from datetime import date, datetime, timedelta
import os
import csv
import json

from pymodbus import pymodbus_apply_logging_config
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
from pymodbus.transaction import ModbusRtuFramer
from pymodbus.register_read_message import ReadHoldingRegistersResponse

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from logger import logger
from gwrapper import Drive, Sheets

class Send:
    """This class writes data to the local CSV and to Google Sheets."""

    BACKUP_FOLDER = os.path.expanduser('~/pysensor/backup/')
    DRIVE_FOLDER_ID = '1KeyIGI54eBDYrnC9PzsltUjwaczyEC1_'
    COLUMN_RANGE = 'A1:Q1'
    HEADERS = ('PK_no','read_at','u_an','u_bn','u_cn','uln_avg','ull_avg','i_a','i_b','i_c','kw_t','kvar_t','kva_t','pf_a','pf_b','pf_c','freq')

    def __init__(self, values):
        """Group register values, set timestamps and backup information."""
        self.values = tuple(['{:.3f}'.format(i) for i in values])   
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.today = date.today().strftime("%Y-%m-%d")
        self._todayfile = os.path.expanduser(f'~/pysensor/backup/{self.today}.csv')
        self._sameday = os.path.exists(self._todayfile)
        self.pk_no = self.get_pk_no()
   

    def get_pk_no(self):
        """Gets PK number of new entry by incrementing last PK num by 1"""
        
        if self._sameday:
            lastfile = self._todayfile
        else:
            files = sorted(os.listdir(self.BACKUP_FOLDER), reverse=True)
            lastfile = os.path.expanduser(f'~/pysensor/backup/{files[0]}')

        with open(lastfile, 'r') as lastfile_:
            lastrow = tuple(lastfile_.readlines()[-1].split(','))
            
        return int(lastrow[0]) + 1 
        

    def to_cloud(self):
        """Connect to Google Drive folder. 
        If Google Sheets for today exists, appends to it. 
        If not, creates new Google Sheets with today's date and adds header and data values.
        """
        
        folder = Drive(self.DRIVE_FOLDER_ID)
        filename = self.today 
        entry = (self.pk_no, self.timestamp, *self.values)

        if self._sameday:
            sheet = folder.get_file_by_name(filename)
            sheetID = sheet[0].get('id')
            backup = Sheets(sheetID)
            value_body = backup.get_value_body(entry)
            backup.append(self.COLUMN_RANGE, body=value_body)
        else:
            newsheet = folder.create_sheet(filename)
            sheetID = newsheet.get('id')
            backup = Sheets(sheetID)
            header_body = backup.get_value_body(self.HEADERS)
            value_body = backup.get_value_body(entry)
            backup.update(self.COLUMN_RANGE, body=header_body)
            backup.append(self.COLUMN_RANGE, body=value_body)

        
    def to_local(self):
        """Backup to local CSV in /backup folder.
        If csv file for today exists, appends to it. 
        If not, write new file with headers and append to it.
        """
        
        entry = (self.pk_no, self.timestamp, *self.values)

        if self._sameday:
            with open(self._todayfile, 'a', newline='') as writefile:
                backup = csv.writer(writefile)
                backup.writerow(entry)

        else:
            with open(self._todayfile, 'w', newline='') as writefile:
                backup = csv.writer(writefile)
                backup.writerow(self.HEADERS)
                backup.writerow(entry)


class Retrieve:
    """This class retrieves raw register values from the sensor and converts to real numeric values."""

    def __init__(self, address, count, scale):
        """Specifies:
        address = register address
        count = number of bits to retrieve
        scale = multiplier (n). See explanation.
        
        Scale explanation: 
            The raw value from the sensor has been multiplied by 10^n.
            The true value is obtained by dividing by the multiplier 10^n.
        """
        self.address = address
        self.count = count
        self.scale = scale

    @staticmethod
    def client(port):
        """Configures and returns serial client object."""
        client = ModbusSerialClient(
        port,
        framer=ModbusRtuFramer,
        timeout=2,
        retry_on_empty=True,
        baudrate=9600,
        strict=False,
        )
        return client

    def read_double_bytes(self,client):
        """Reads and processes raw register values of double byte package.
        In cases where there is an empty byte as indicated by 0, the value is skipped.
        """
        raw = client.read_holding_registers(self.address,self.count,1)
        processed = []
        for package in zip(raw.registers[::2],raw.registers[1::2]):
            if(package[0] == 0):
                processed.append(package[1])
            else:
                strnum = "{}{}".format(package[0],package[1])
                num = int(strnum)
                processed.append(num)
        
        value = [(i/10**self.scale) for i in processed]
        return value
        
    def read_single_bytes(self, client):
        """Read raw register value of single byte package. 
        The raw value is converted to the true decimal value using its multiplier"""
        raw = client.read_holding_registers(self.address,self.count,1)
        value = [(i/10**self.scale) for i in raw.registers]
        return value


def meter_reader_main(port):
    """Main function run when script is called. 
    port = serial port (e.g /dev/ttyS0)
    """
    client = Retrieve.client(port)
    client.connect()

    REGISTERMAP = os.path.expanduser('~/pysensor/registermap.json') 

    with open(REGISTERMAP,'r') as rmap:
        registermap = json.load(rmap)

    # registermap.json contains list of register map values that will be specified in the Send __init__. 

    try:
        rr = client.read_holding_registers(0,2,1)
        # rr is the initial request to the sensor made to handle errors and exceptions.
        # If there is an error in the connection, rr will trigger it first.

        if rr.isError():
            logger.error(f"Received Modbus library error({rr})")
            client.close()
            return

        if isinstance(rr, ExceptionResponse):
            logger.exception(f"Received Modbus library exception ({rr})")
            # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
            client.close()
            return

        data = []

        for value, config in registermap.items(): 
            value = Retrieve(*config)
            if config[1]%2==0: # check if packet has double bytes 
                response = value.read_double_bytes(client)
                data.extend(response)
                time.sleep(0.1)
            else:
                response = value.read_single_bytes(client)
                data.extend(response)
                time.sleep(0.1)

        write = Send(data)
        
        try:
            write.to_cloud()
        except HttpError as error: #better error handling
            print(error)
        finally:           
            write.to_local()

        del data
        

    except ModbusException as modexc:
        logger.exception(f"Received ModbusException({modexc}) from library") 
        client.close()
        return
    
    except Exception as exc:
        logger.exception(f"Received Exception({exc})")
        client.close()
        return

    
    #print("close connection")
    client.close()


if __name__ == "__main__":

    meter_reader_main('/dev/ttyS0')
    
