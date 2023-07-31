
from builtins import ValueError, print
from os import stat
from re import search
from utilities8102 import connection_handler as CH
from utilities8102 import general_utility as GU, send_error_email
import time, re, netmiko, threading


class IOS_Handler():


    def __init__(self, envDict, utilityLog, ipList):

        '''The basic things that are used throught the whole class that we use
        to start things off

        ipList: the list of ip addresses
        deviceUsername: the username of the device
        devicePassword: the password of the device
        utilityLog: the logging object we are using
        '''

        # For ios update reporting
        self.portConnectDict = {}

        self.ipList = ipList
        self.envDict = envDict
        self.deviceUsername = self.envDict['SONICUSERNAME']
        self.devicePassword = self.envDict['SONICPASSWORD']
        self.defaultUsername = self.envDict['SONICDEFAULTUSERNAME']
        self.defaultPassword = self.envDict['SONICDEFAULTPASSWORD']
        self.utility_log = utilityLog


    def _send_credentials(self, device):

        '''This is for the login to the server connected to the avocent

        device: the netmiko connection object

        returns: bool if it came back true
        '''

        try:
            #see if there is any movement in there
            time.sleep(4)
            _ = device.send_command_timing(self.deviceUsername)
            _ = device.send_command_timing(self.devicePassword)

            return True

        except netmiko.exceptions.ReadTimeout:
            return False


    def verify_sonic_verison(self, connect, targetVersion):
        """Verifies the sonic ios on the system

        connect: netmiko connection that we send connection to
        targetVersion: sonic version we're checking for

        returns object the response of the command, a reboot bool and a current bool
        """

        installer_list = connect.send_command_timing("sudo sonic-installer list").split()
        
        print(f"installer list : {installer_list}")
        currentVersion = installer_list[1]
        nextVersion = installer_list[3]

        if nextVersion == targetVersion:
            if currentVersion == targetVersion:
                reboot = True
                current = True
            else:
                reboot = True
                current = False
        else:
            reboot = False
            current = False

        showVerOutput = connect.send_command("sudo show version")
        versionOutput = f"show version {showVerOutput}"

        return {"output": versionOutput, "reboot": reboot, "current": current}


    def _ios_update_pxe(self, ip):

        '''updates the ios of the device by navigating the bios menu
        it goes as follows grub menu > exit grub cmd line > go to 
        Boot manager once Bios menu shows up > click on iPXE > let iPXE
        take care of the rest.

        ip: the ip of the device
        '''
        
        self.portConnectDict[ip] = {"ios_upgrade" : False, "reboot": False}

        device = CH.device_login(ip, self.envDict, self.utility_log)
        
        if device == False:
            self.utility_log.warning(f"{self.portConnectDict[ip]} could not find an ip so it cannot upgrade ios exiting")
            return

        versionInfo = self.verify_sonic_verison(device, self.envDict['SONICVERSION'])

        # Check if the device needs ios version update
        if versionInfo["current"] is False:

            try:
                cmd_output = device.send_command(
                    command_string= 'sudo bash',
                    expect_string= '#',
                    strip_prompt=False,
                    strip_command=False
                )
                
                test2 = device.send_command_timing(
                    command_string= f'sonic-installer install /tmp/{self.envDict["SONICIOS"]}'
                )
                
                test = device.send_command(
                    command_string= 'y',
                    expect_string= re.escape("root@localhost:/home/cisco#"),
                    read_timeout=900
                )

                print(ip)
                print(cmd_output)
                print(test2)
                print(test)

                # verify if the ios took place and is set to reboot into image
                versionInfo = self.verify_sonic_verison(device, self.envDict['SONICVERSION'])
                print(versionInfo['reboot'])
                print("STARTING REBOOT")
                if versionInfo["reboot"] is True:
                    send_reboot = device.send_command('shutdown -r now')
                    print("SENT REBOOT")
                    device.disconnect()
                    self.portConnectDict[ip]["reboot"] = True
                    time.sleep(300)
                    print("SLEEPOVER!")

                    device = CH.device_login(ip, self.envDict, self.utility_log)
                    # see if there is any movement in there
                    versionInfo = self.verify_sonic_verison(device, self.envDict['SONICVERSION'])

                    if versionInfo["current"] is False:
                        time.sleep(120)
                        versionInfo = self.verify_sonic_verison(device, self.envDict['SONICVERSION'])
                        if versionInfo["current"] is False:
                            self.utility_log.warning(f"{self.portConnectDict[ip]['serial']} ios upgrade status is {versionInfo['current']} ")
                        self.portConnectDict[ip]["ios_upgrade"] = versionInfo['current']
                    self.portConnectDict[ip]["ios_upgrade"] = versionInfo['current']

                else:
                    # should be false if update command did not work
                    self.utility_log.warning(f"{ip} Error applying update for sonic installer, reboot aborted")

            except netmiko.exceptions.ReadTimeout as e:
                # should be false if connection fails on ios upgrade
                print(e)
                self.utility_log.warning(f"{ip} Error during update, returned {e}")
                return 

            # one last check to make sure current version of OS is correct
            self.portConnectDict[ip]["ios_upgrade"] = versionInfo['current']
            
        else:
            self.utility_log.info(f"{ip} ios is already updated continuing...")
            self.portConnectDict[ip]["ios_upgrade"] = versionInfo['current']
            return


    def thread_ios_upgrade_devices(self):
        '''Threads the active devices and updates the ios via pxe

        returns: updated dictionary with it updates the os or not
        '''
        
        if len(self.ipList) <= 0:
            return
        
        upgrade_threads = []
        
        for ip in self.ipList:
            x = threading.Thread(target=self._ios_update_pxe, args=(ip,))
            upgrade_threads.append(x)
            x.start()
            time.sleep(5)

        for thread in upgrade_threads:
            thread.join()

        return self.portConnectDict
