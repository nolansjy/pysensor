##NOTICE##
# You are now editing the TEST SCRIPT of the sensor reader!
# This script is used to test SQL and serial connection.

from time import sleep
import os
import subprocess

from pymodbus import pymodbus_apply_logging_config
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
from pymodbus.transaction import ModbusRtuFramer
from pymodbus.register_read_message import ReadHoldingRegistersResponse

from logger import logger
from gwrapper import Drive, Sheets
from driver import Send

def sensorcheck(port):
    """Tests connection to meter reader and prints model information. 
    port = serial port (e.g /dev/ttyS0)
    """
    client=ModbusSerialClient(
    port,
    framer=ModbusRtuFramer,
    timeout=2,
    retry_on_empty=True,
    baudrate=9600,
    strict=False,
    )
    
    client.connect()
    if client.connected:
        print("Serial connection is UP.")

    try:

        rr = client.read_holding_registers(9800,27,1)

        if rr.isError():
            logger.error(f"Received Modbus library error({rr})")
            client.close()
            return

        if isinstance(rr, ExceptionResponse):
            logger.exception(f"Received Modbus library exception ({rr})")
            # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
            client.close()
            return

        model = ''.join(chr(i) for i in rr.registers[:9])
        fw = str(rr.registers[20])
        firmware = fw[:1] + '.' + fw[1:3] + '.' + fw[3:]
        protocol  = f'{rr.registers[21]/10}'
        update = '-'.join(map(str, rr.registers[22:25]))
        serial = ''.join(map(str, rr.registers[25:27]))
        sensor_status = (f"Meter model   {model}\t"
        f"\tFirmware V{firmware} (Updated {update})\n"
        f"Serial number {serial}"
        f"\tProtocol V{protocol}"
        )
        print(sensor_status)

    except ModbusException as modexc:
        logger.exception(f"Received ModbusException({modexc}) from library") 
        client.close()
        return

    except Exception as exc:
        logger.exception(f"Received Exception({exc})")
        client.close()
        return

    
    print("Closed serial connection.")
    client.close()
    sleep(1)

def csvcheck():
    """Read row from last CSV file"""
    BKPATH = os.path.expanduser('~/pysensor/backup')
    backuplist = sorted(os.listdir(BKPATH))
    lastbackup = backuplist[-1]
    with open(f"{BKPATH}/{lastbackup}",'r') as backupfile:
        lastrow = tuple(backupfile.readlines()[-1].split(','))

    print(f"Last CSV backup was at {lastbackup}.")
    print(f"Last record in CSV was PK {lastrow[0]} at {lastrow[1]}.")
    sleep(1)

def sheetcheck():
    """Read row from last Google Sheets"""
    folder = Drive(Send.DRIVE_FOLDER_ID)
    lastfile = folder.get_sheets()[0]
    sheetname = lastfile['name']
    sheetID = lastfile['id']
    sheet = Sheets(sheetID)
    lastrow = sheet.get_last_row()
    print(f"Last Sheet backup was at {sheetname}.")
    print(f"Last record in Sheet was PK {lastrow[0]} at {lastrow[1]}.")
    sleep(1)
    
def croncheck():
    """Check cron status."""
    is_active = subprocess.run(["systemctl","is-active","--quiet","cron"])
    cronlog = subprocess.run(["journalctl","--unit=cron","--no-hostname","--lines=5","--quiet"], 
                            capture_output=True, text=True) 
    if is_active.returncode == 0:
        print("CRON is active.")
    else: 
        print("CRON is inactive.")
    print("-- Last 5 lines from CRON log --")
    print(cronlog.stdout)
    sleep(1)

def pysensor_status(port):
    """Run all status checks"""
    print("Testing connection to sensor...")
    sensorcheck(port)
    print("\nTesting connection to Google Drive...")
    sheetcheck()
    print("\nViewing last local CSV backup...")
    csvcheck()
    print("\nViewing CRON status...")
    croncheck()

    
