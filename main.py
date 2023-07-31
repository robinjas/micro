import os
import re
import time
import threading
from dotenv import load_dotenv
from utilities8102 import general_utility as GU
from utilities8102 import connection_handler as CH
from utilities8102 import send_error_email as EmailError
from utilities8102 import ios_handler as IH
from utilities8102 import aikido_firmware_handler as AH
from utilities8102 import sonic_handler as SH
from utilities8102 import find_dhcp_leases


load_dotenv()

mainLog = GU.setup_log("__main__")
utility_log = GU.setup_log("general_utility")
backend_log = GU.setup_log("linux_backend")
ios_log = GU.setup_log("ios_log")
aikido_firmware_log = GU.setup_log("aikido_firmware")

error_msg = {}
finished_serials = []


def add_environment_vars():
    """Adds the enviroment Variables in the .env file"""

    envDictionary = {}
    
    lst_var = [
        "QCFOLDERDIRECTORY",
        "LOCALQCFOLDERDIRECTORY",
        "REMOTESONICFILEPATH",
        "SONICIOSDESTPATH",
        "SONICIOS",
        "SONICUSERNAME",
        "SONICPASSWORD",
        "SONICVERSION",
        "AKIDOVERSION",
        "GATEWAYIP",
        "GATEWAYUSERNAME",
        "GATEWAYPASSWORD",
        "SONICDEFAULTUSERNAME",
        "SONICDEFAULTPASSWORD"
    ]

    for var in lst_var:
        envDictionary[var] = os.getenv(var)

    envDictionary["EMAILLIST"] = os.getenv("EMAILLIST").split(',')
    envDictionary["CSVFILE"] = envDictionary["QCFOLDERDIRECTORY"] + os.getenv("CSVFILE")
    envDictionary["LOGFILELOCATION"] = envDictionary["QCFOLDERDIRECTORY"] + os.getenv("LOGFILELOCATION")

    return envDictionary


def add_email_errors(keyVal, status):
    
    '''Sets up the email dictionary we will use for setup_format_email()

    keyVal: will be the header of the the body of errors
    status: the error message body of the keyval, there can be multiple
    '''

    if error_msg.get(keyVal, None):
        if not status in error_msg[keyVal]:
            error_msg[keyVal].append(status)
    else:
        error_msg[keyVal] = [status]
    
    mainLog.warning(f"{keyVal} {status}")


def check_for_essentials_docs(checkFile, typeFile):
    """Checks to make sure that there essential files and folders are present before starting
    
    checkFile: the path of the file/folder we are checking
    typeFile: right now, only does directory or a file option to detirmine how to check
    """
    
    if GU.verify_path_structure(checkFile, typeFile, utility_log) == False:
        time.sleep(4)
        if GU.verify_path_structure(checkFile, typeFile, utility_log) == False:
            add_email_errors("Essential", f"{typeFile} {checkFile} is not Present, please check the fstab file to make sure this is working correctly /etc/fstab")
            raise FileNotFoundError(f"{typeFile} {checkFile} not found please check that it is present")
        else:
            mainLog.info(f"Found the {typeFile} {checkFile} continuing...")
    else:
        mainLog.info(f"Found {typeFile} {checkFile} Continuing")


def copy_ios_to_sonic(connection, ip, src, destPath, ios):
    """
    Copies a file to the sonic router using netmiko file_transfer

    connection = netmiko connection
    ip = device ip
    src = local file path
    destPath = destionation of where we are copying to
    ios = the ios filename of the file
    """
    
    if not connection:
        time.sleep(200)
        connection.establish_connection()
        if not connection:
            mainLog.warning(f"{ip} could not sshnnect to server to copy ios over exiting out")
            return False

    output = connection.send_command("ls /tmp")

    iosPattern = re.escape(ios)
    findIos = re.findall(iosPattern, output)
    
    if len(findIos) > 0:
        mainLog.info("device has ios already transferred over, continuing...")

    else:
        scpStatus = CH.netmiko_scp(connection, src, ios, backend_log, fileSystem=destPath, direction='put')
        if scpStatus == False:
            add_email_errors(ip, "was not reachable before scp please check connection")
        else:
            mainLog.info(f"Device: {ip} has succesfully copied over {ios}")

        status = GU.local_check_ping(ip, utility_log, persistent=True)
        mainLog.info(f"{ip} Ping on device returned {status}")


def verify_sonic_prompt(netmiko_prompt):
    """ Verifies if the sonic prompt is correct or not

    netmiko_prompt = prompt given with running Backend.find_netmiko_prompt

    returns = bool if it is the prompt that we want
    """

    if netmiko_prompt == "cisco@localhost:~$":
        return True, False
    elif netmiko_prompt == "admin@sonic:~$":
        return False, True
    else:
        return False, False


def create_qc_folders(filePath, soNumber):
    """Creates Our Log file Directory based on what is found on the csv file

    filePath: the path of our home directory
    soNumber: the so number folder we are going to make 
    """

    desiredPath = f'{filePath}{soNumber}'

    if GU.verify_path_structure(desiredPath, "Directory", utility_log) == False:
        GU.create_directory_folder(desiredPath, utility_log)
        mainLog.info(f'Did not find QC directory {desiredPath} Creating Now')
        if GU.verify_path_structure(desiredPath ,"Directory", utility_log) == False:
            mainLog.warning(f"Did not create folder pleaese check that the name is valid returns {desiredPath}")
        else:
            mainLog.info(f"Folder was created at {desiredPath}")
    else:
        mainLog.info(f"Directory: {desiredPath} was found continuing")


def sonic_post_qc(dir_path, ip, soNumber, envDict):
    """this is after everything has been completed, we will run 
    qc and write it into a log file

    dir_path = directory in which we are saving to
    ip = ip address we are running the qc on

    returns a bool if the qc passed or not, also serial number
    """

    # Establish connection to router using SSH
    connect = CH.netmiko_connection(ip, envDict['SONICUSERNAME'], envDict["SONICPASSWORD"], "linux", backend_log)
    if connect != False:
        deviceSerial = connect.send_command("sudo dmidecode -s system-serial-number")
        netmikoPrompt = CH.find_netmiko_prompt(connect, backend_log)
        localPrompt, sonicPrompt = verify_sonic_prompt(netmikoPrompt)
        if sonicPrompt:
            show_version_output, sonicVersion = IH.IOS_Handler().verify_sonic_verison(connect, envDict["SONICVERSION"])
            if sonicVersion:
                #AKIDO is a firmware for the sonic devices being applied
                akido = AH.aikido_handler()
                versionCheck, fwutilList = akido.get_akido_version(connect, aikido_firmware_log, envDict["AKIDOVERSION"])
                if versionCheck:
                    # Akido version is correct, write to log file
                    with open(
                        f"{dir_path}{soNumber}/{deviceSerial}_QC.log", "w", encoding="utf-8"
                        ) as f:

                        f.write("\n")
                        f.write(show_version_output)
                        f.write("\n"+50*"="+"\n")
                        f.write(fwutilList)

                    # QC passed
                    return True, deviceSerial
                else:
                    # Akido verison is incorrect
                    add_email_errors(ip, "Akido verison is incorrect")
            else:
                # Incorrect Sonic version
                add_email_errors(ip, "Sonic version did not match on device")
        else:
            # No Sonic prompt
            add_email_errors(ip, "Device went through QC, was not reported as a Sonic device")
    else:
        # Cannot connect
        add_email_errors(ip, "Lost connection durring QC")

    return False, deviceSerial


def copy_log_files_over(src, dest):
    """This moves the Directory from one place to another

    src: the begining path that we will move
    dest: the path that we are going to move the file to
    """

    mainLog.debug(f"Copying {src} to {dest}")

    status = GU.copy_directory_over(src, dest, utility_log)    

    if status == False:
        mainLog.critical(f"Folder contents {src} did not copy over to {dest} Please make sure the folder has been created")
        error_msg[
            "Backend"
        ] = f"Folder contents {src} did not copy over to {dest} Please make sure the folder has been created"
    if status == True:
        mainLog.info(f"Succesfully Transfered {src} to {dest} Continuing")
    return status


def qc_check(soNumber, ip, envDict):
    """After IOS update, we qc check the device via avocent and grab qc data
    soNumber: serial number we will use for quality
    ip: ip address of the avocent
    envDict: enviorment variables dictionary
    """

    create_qc_folders(envDict['LOCALQCFOLDERDIRECTORY'], soNumber)
    status, serial = sonic_post_qc(envDict['LOCALQCFOLDERDIRECTORY'], ip, soNumber, envDict)
    # Copies a full directory over with contents in it
    # Next process takes about 10 mins per device
    copyStatus = copy_log_files_over(f"{envDict['LOCALQCFOLDERDIRECTORY']}{soNumber}", f"{envDict['LOGFILELOCATION']}")
    if status and copyStatus:
        finished_serials.append(serial)


def setup_format_email(emailList):
    '''Compiles email functionality to send off our errors'''

    settings = EmailError.Email.get_email_settings(emailList)
    
    if len(error_msg) > 0:
        EmailError.Email.format_email(
            error_msg, "The Following are errors found on a 8102 device", settings
        )


def main():
    
    envDict = add_environment_vars()
    
    # Check for Directory Make sure it is there
    check_for_essentials_docs(envDict['QCFOLDERDIRECTORY'], "Directory")

    # Check for csv file in the directory make sure it can find the csv 
    # also it is mounted correctly
    check_for_essentials_docs(envDict['CSVFILE'],'File') 

    mainLog.debug("Gathering csv and dhcp data")

    dhcpLeaseDict = find_dhcp_leases.filtered_active_leases(backend_log, envDict)
    
    if len(dhcpLeaseDict) <= 0:
        mainLog.warning("Nothing in the dhcp lease, nothing to do now, returning...")
        return

    csvContents = GU.get_csv_contents(envDict['CSVFILE'])

    if len(csvContents) <= 0:
        mainLog.warning("Nothing in the csv file, nothing to do now, returning...")
        return

    ios_dict = {}

    # List of ips to connect to
    selected_active_ips = []

    for ip, dictData in dhcpLeaseDict.items():
        for csvRow in csvContents:
            if dictData['device_serial'] in csvRow['Serial Number']:
                selected_active_ips.append(ip)
                soNumber = csvRow["SO Number"]
                ios_dict[csvRow["Serial Number"]]= {'remote_ip_address': ip, "deviceData":"", "soNumber": soNumber}

                mainLog.info(f"{dictData['device_serial']} was found in the csv and dhcp starting device configuration")

    mainLog.debug("Upgrading device now...")

    # List for copy ios threads
    copy_ios_threads = []

    sourcePath = f'{envDict["REMOTESONICFILEPATH"]}{envDict["SONICIOS"]}'

    for ip in selected_active_ips:
        connection = CH.device_login(ip, envDict, qc_log=ios_log)
        # Copy ios threads
        t = threading.Thread(target=copy_ios_to_sonic, args=(connection, ip, sourcePath, envDict["SONICIOSDESTPATH"], envDict["SONICIOS"]))
        copy_ios_threads.append(t)
        t.start()
        time.sleep(5)

    for t in copy_ios_threads:
        t.join()

    deviceIos = IH.IOS_Handler(envDict, ios_log, selected_active_ips)

    IOSQCRecords = deviceIos.thread_ios_upgrade_devices()

    print(ios_dict)
    print(IOSQCRecords)







    # threads = []

    # print('hey you guys')
    # for index, conn in enumerate(connection_list):
    #     print(f'Test Device #{index}: {conn.output}')
    #     threads.append(conn.send_reboot())
    #     print(f'Test Device #{index}: {conn.output}')
    
    # for index, thread in enumerate(threads):
    #     print(f'Thread #{index} joining...')
    #     thread.join()

    #     print(f'Thread {index} as joined.')

    # for index, conn in enumerate(connection_list):

    #     print(f'Test Device #{index}: {conn.output}')
        

    # TODO pass in IP list
    # for ip in selected_active_ips:
        # Passing in required netmiko params also sonic version for later
        # with SH.SonicSSHConnection(ip=ip, target_sonic_version=envDict["SONICVERSION"], username=envDict["SONICUSERNAME"], password=envDict["SONICPASSWORD"]) as sonic_handler:
        #     # Check version
        #     if sonic_handler.is_upgraded:
        #         print("worked")
        #     else:
                #do the upgrade
                #put the thread function( target=sonic_handler.upgrade_ios, args=('sj'))
        #         print(sonic_handler.is_upgraded)

    
    # qc_check()
    # IOS Handler

    # qc_threads = []

    # for SN in ios_dict:
    #     t = threading.Thread(target=qc_check, args=(ios_dict[SN]["soNumber"], ios_dict[SN]["remote_ip_address"], envDict))
    #     qc_threads.append(t)
    #     t.start()
    #     time.sleep(5)

    # for t in qc_threads:
    #     t.join()

    # TODO what do with IOSQCRecords
    # TODO qc_check(soNumber, ip, envDict)
    # TODO sonic_post_qc()
    # TODO revert EMAILLIST in env


    # TODO future stuff
    # TODO cmd_output purpose in ios handler? no variable needed?
    # TODO thread process function in GU?

    return
    try:
        #finished_serials is a list made in qc_check(global append)
        mainLog.debug(f"marking devices {','.join(finished_serials)} as complete")
        GU.mark_completion_in_csv(envDict['CSVFILE'], finished_serials)
    except OSError:
        add_email_errors("General Error", r"M:\Network_repository\Microsoft\GICLAB0020894_Cisco 8102 Remediation\QC Logs\8102_Sonic_Inventory.csv is busy, make sure no one is actively in it...")

    mainLog.debug(f"sending out emails now")
    setup_format_email(envDict["EMAILLIST"])

main()
