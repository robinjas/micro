import logging, time, subprocess, os, csv, re
import pandas as pd


def linux_cli(command, qc_log, popen=False):
    """ Takes in a CLI command and runs it through subprocess then returns the output,
    and either a Bool or exit code

    command: the linux command we want to run
    popen: wheter or not we use the subprocess Popen method or not

    returns = the output of the command and a bool if it passed through
              or not
    """

    newCommand = []

    # Command is a string, let's turn it into a list for the subprocess module
    command = command.split(" ")

    # For compatibility with Rubicon product part number
    for com in command:
        newCommand.append(com.replace("*", " "))

    if not popen:
        try:
            output = subprocess.check_output(newCommand)
            return output, True

        except subprocess.CalledProcessError as e:
            return e.output, False

        except:
            pass

    elif popen:
        # get everything and have a timeout happen after 10 minutes
        script_timeout = 600
        proc = subprocess.Popen(
            newCommand,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        try:
            stdout, stderr = proc.communicate(timeout=script_timeout)

        except subprocess.TimeoutExpired:
            # print("Command: " +  str(command) + " timedout check device or command")
            qc_log.info(f"Timed out on Command: {command}")

            return

        proc.kill()
        qc_log.info(f"Command Output:{stdout} Error:{stderr}")
        return stdout, stderr

    else:
        exitcode = proc.returncode
        if exitcode != 0:
            if stderr:
                # print("error running command: " + str(command))
                pass

        else:
            output = stdout
        proc.kill()


def verify_path_structure(path, pathType, qc_log):
    """Vertifies That the correct folder is present in the directory

    path = str of what directory is present or not

    pathType = str that detirmines if it is a file or a directory

    returns = bool if the path is present or not
    """

    qc_log.debug(f"Checking {pathType} {path} to make sure it is there")

    pathTypeOptions = {"dir": "Directory", "file": "File"}

    if pathType == pathTypeOptions['dir']:
        if os.path.isdir(path) == True:
            status = True
        else:
            status = False

    elif pathType == pathTypeOptions["file"]:
        if os.path.isfile(path) == True:
            status = True
        else:
            status = False

    else:
        qc_log.warning(f'Could not find the correct file type please check to see if it is a {pathTypeOptions["dir"]} or a {pathTypeOptions["file"]}')
        raise TypeError("Invalid Slection used to vertify a file option please check your spelling")
    
    if status:
        qc_log.info(f"Found {pathType} {path} Continuing")
        return True
    else:
        qc_log.warning(f"Did not find directory {pathType} {path}")
        return False


def copy_directory_over(directory, targetDir, qc_log):
    """ This moves the Directory from one place to another

    directory: the begining path that we will move

    targetDir: the path that we are going to move the file to

    returns = bool if the file copied over or not
    """

    if not verify_path_structure(targetDir, "Directory", qc_log):
        create_directory_folder(targetDir, qc_log)
        qc_log.info(f'Directory {targetDir} has not been created, Creating now...')

    output, status = linux_cli(f'sudo cp -r {directory} {targetDir}', qc_log) 

    if status == True:
         qc_log.info(f'Succesfully copied over {directory} to {targetDir}')
    else:
        qc_log.warning(f"File contents of {directory} did not copy over to {targetDir}")

    return status


def get_csv_contents(csvFile):
    """Grabs The contents of the file and returns a dictionary value of the contents it was suppose to looks for

    csvFile : Path of the csvFile we are parsing

    returns = results of the dictionary based on the the list
              passed through
    """

    csvDict = []

    with open(csvFile, "r", encoding="utf-8") as csvFileContents:
        csvReader = csv.DictReader(csvFileContents)
        for csvRow in csvReader:
            if csvRow['SO Number'] != '' and csvRow['Serial Number'] != '' and csvRow['Complete'] != '':
                if csvRow['Complete'] != 'y':
                    csvDict.append(csvRow)

    return csvDict


def create_directory_folder(path, qc_log):
    """Create a folder using sudo mkdir
    path: path using to create a directory
    """

    output, status = linux_cli(f'mkdir {path}', qc_log) 

    if status == True:
        qc_log.info(f"Directory was created at {path}")
    else:
        qc_log.warning(
            f"Directory was not created at {path} please make sure it is a valid spot"
        )


def wait_for_ping(ip, qc_log, status, sleepTimer=8):
    """A way to loop through pinging the device so we can try to reach it more then once

    ip = ip address of the device we are pinging
    status = first status passed in to see what we need to exectue

    returns if the ping was succesful or not
    """

    if status == True:
        qc_log.info("Got a successfull ping on first try")
        return status
    else:
        for count in range(0, 10):
            # print(f"cSleeping for {sleepTimer} seconds...")
            time.sleep(sleepTimer)

            if count != 9:
                status = local_check_ping(ip, qc_log)

                if status == True:
                    return status

            else:
                qc_log.warning(f"Device {ip} timed out on max tries of ping")
                return status


def local_check_ping(hostname, qc_log, persistent=False):
    """Pings a device and returns status

    hostname = ip address of the device
    persistent = switch that lets persistent ping the device

    returns = if the ping was successfull or not
    """

    output, status = linux_cli(f"ping -c 1 {hostname}", qc_log)
    qc_log.info(f"ping output {output}")

    if persistent:
        status = wait_for_ping(hostname, qc_log, status)

    if status:
        qc_log.info(f"Device {hostname} is reachable continuing")
    else:
        qc_log.warning(f"Device {hostname} is unreachable please check connection")

    return status


def remote_ping_gateway(device, prompt):

    """This is when we are ssh into the device and we want to ping something 
    from the remote device

    device : netmiko connection we are pinging on
    prompt : the expected prompt that we are looking for
    
    returns : Bool if it was successfull or not
    """


    pingGateway = device.send_command("ping -c 5 192.168.110.1", expect_string=prompt)
    findPacket = re.findall(r".{2,3}packet\sloss", pingGateway)
    if len(findPacket) > 0:
        packet = findPacket[0].split('%')[0]
        if int(packet) <= 25:
            return True
    return False


def setup_log(name):

    '''Create a log file name based on the name passed through

    name = the name of the log file we want to name it
    '''
    logger = logging.getLogger(name)   
    logger.setLevel(logging.DEBUG) 
    log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    filename = f"/home/itclab/microsoft_8102_xr_to_sonic/logs/{name}.log"
    
    log_handler = logging.FileHandler(filename)
    log_handler.setLevel(logging.DEBUG)

    log_handler.setFormatter(log_format)
    logger.addHandler(log_handler)

    return logger


def mark_completion_in_csv(csvFile, devices):
    ''' This takes a list of completed device serial numbers and marks 
    them as complete in the csv file by changing the 'n' in the 
    Completed column to a 'y'.
    
    csvFile : Path of the csvFile we are parsing
    devices : list of serial #s we are marking as complete in the file

    df stands for dataframe, commonly used with pandas
    mark_completion_in_csv("/home/nunoe/8102_Sonic_QC/8102_Sonic_Inventory.csv", ['FLM26160E7D'])
    '''

    df = pd.read_csv(csvFile)

    for serial in devices:
        df.loc[df['Serial Number'] == serial, 'Complete'] = 'y'

    df.to_csv(csvFile, index=False)

    return True


def check_for_moved_log_files(csvContents, qcLocation):
    ''' Check for QC logs for each SN to make sure it completed. 
    
    csvContents: contents of the csv file
    qcLocation: A string path the location of where the QC files go
    '''

    finishedSerials = []
    fileNames = []

    for root, dirs, filename in os.walk(qcLocation):
        for f in filename:
            fileNames.append(f)

    for row in csvContents:
        for filen in fileNames:
            if row["Serial Number"] in filen:
                finishedSerials.append(row['Serial Number'])

    return finishedSerials