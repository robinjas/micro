from cmd import PROMPT
from utilities8102.general_utility import setup_log
from netmiko import ConnectHandler, NetmikoTimeoutException, file_transfer
import paramiko, time

#qc_log = setup_log(__name__) 


def netmiko_connection(ip_address: str, username: str, password: str, device_type: str, qc_log, port=22):

    '''Connection to a device using netmiko
    ip_address = the ip address of the device being passed through
    username = username of the device
    password = password of the device
    device_type = the device type of the device mostly linux

    returns = either return the netmiko object or a False value saying
              it did not connect
    '''

    device = {
        "device_type": device_type,
        "ip": ip_address,
        "username": username,
        "password": password,
        "global_delay_factor": 2,
        "fast_cli": False,  
        "port": port
    }

    try:
        connection = ConnectHandler(**device)
        qc_log.info(f"IP connected: {ip_address} with netmiko")
        return connection

    except NetmikoTimeoutException:
        qc_log.warning(f"IP not connected: {ip_address} with netmiko")
        return False

def find_netmiko_prompt(netmiko_connection, qc_log):
    for i in range(0, 10):
        if i != 10:
            prompt = netmiko_connection.find_prompt()
            if prompt != False:
                netmiko_prompt = prompt
                return netmiko_prompt
        else:
            qc_log.warning("netmiko prompt timeout")

def netmiko_scp(Connection, source, dest, qc_log, fileSystem='/tmp/', direction='put'):
    ''' This will handle the scp from a device to another using netmiko file_transfer

    Connection = Netmiko Connection that we will be using
    source = sorce file that we will be copying over
    dest = destiantion of the folder that we are transforing to
    filesystem = defualt is linux as this is a linux system technically
    direction = I had a hard time finding more about this, but put seems to be defualt

    return = bool if it scp was successfull or not
    '''

    transfer_dict = file_transfer(
    Connection,
    source_file=source,
    dest_file=dest,
    file_system=fileSystem,
    direction=direction,
    # Force an overwrite of the file if it already exists
    overwrite_file=True,
    )
    # {'file_exists': True, 'file_transferred': True, 'file_verified': True}
    status = False
    
    try:
        if transfer_dict['file_exists'] and transfer_dict['file_verified']: 
            qc_log.info(f"Successfully copied over {source} to {fileSystem}{dest}")
            return True
        else:
            qc_log.warning(f"Did not copy over {source} to {dest} got the following {transfer_dict}")

    except OSError as e:
        qc_log.warning(f"SCP Copy Error got the following {e}")

    except EOFError as e:
        qc_log.warning(f"SCP Copy Error got the following {e}")
        Connection.disconnect()

    except Exception as e:
        qc_log.warning(f"SCP Copy Error got the following {e}")

    return status


def device_login(ip, envDict, qc_log):
    '''Login in to the avocent using netmiko

    ip: the ip that we are logging on to

    returns: netmiko connection object
    '''
    
    try:
        device = netmiko_connection(ip, envDict["SONICUSERNAME"], envDict["SONICPASSWORD"], "linux", qc_log)
    except:
        device = netmiko_connection(ip, envDict["SONICDEFAULTUSERNAME"], envDict["SONICDEFAULTPASSWORD"], "linux", qc_log)
    if device == False:
        device = netmiko_connection(ip, envDict["SONICDEFAULTUSERNAME"], envDict["SONICDEFAULTPASSWORD"], "linux", qc_log)

    return device


class paramiko_connect():
    ''' Class for establishing a connection to the SSH of the Nexus
    switches and scripting server. It handles sending, receiving, and 
    closing the session. admin / Ch@se123 for the switches.'''

    def __init__(self, ip, username, password, port=''):
        self.ip = ip
        self.port = port
        self.ssh_client = paramiko.SSHClient()

        # This is needed for unknown hosts, which is everything in the lab
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if port == '':
            self.ssh_client.connect(hostname=ip, username=username, password=password)
        else:
            self.ssh_client.connect(hostname=ip, port=self.port, username=username, password=password)

    def send(self, command, qc_log):

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=50)
        except paramiko.SSHException:
            qc_log.warning(f"ERROR: Failed to run command {command}")
            return False
       
        received = stdout.readlines() + stderr.readlines()
        
        try:
            if "Syntax error while parsing" in received[0]:
                qc_log.warning("ERROR: Syntax error on switch")
                return False
        except:
            pass

        return received # Returns a list

    def expect(self, command, expect, qc_log):
        ''' Expect a specific result and return. This is to get
        around the bug of no end of file from the device on the
        other end. '''

        gatheredRead = ''

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=30)
            stdout.channel.recv_exit_status()
            
        except paramiko.SSHException:
            qc_log.warning("ERROR: Failed to run command")
            return False
        

        then = time.time()
        while True:
            time.sleep(3)
            response = stdout.readline()
            print(response)
            gatheredRead += response

            # Break if we found what we're looking for
            if expect in response:
                return gatheredRead, True

            # If 5 seconds have passed with no results, break from loop
            now = time.time()
            if now - then > 25:
                break

        return gatheredRead, False

    def close(self):
        self.ssh_client.close()

