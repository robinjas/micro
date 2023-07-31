from netmiko import ConnectHandler
import logging
import re
import time


def bios_upgrade(net_connect, logFile): #First Bios upgrade
    '''Bios upgrade section
    net_connect = netmiko connection of the device
    '''

    # Put this in because it show a TCP Error when first ran
    logFile.info(f"{net_connect['host']} Sleeping for 60 seconds")
    time.sleep(60)

    with ConnectHandler(**net_connect) as con:
        bash_command = [
            ["sudo -s", r"#"],
            ["fwutil show status", r"#"],
        ]

        scpCommandList = [
            [
                "sudo scp itclab@192.168.110.1:/var/www/html/spf-ns-bios-upgrade.img /opt/cisco/fpd/",
                r"yes",
            ],
            ["yes", r"password"],
        ]

        installCommandList = [
           
            ["fwutil install chassis component BIOS fw /opt/cisco/fpd/spf-ns-bios-upgrade.img",
                r"continue"],
            ["y", r""],
        ]
        imgPattern = re.escape("0-240")
        bashoutput = con.send_multiline(bash_command)
        findImg = re.findall(imgPattern, bashoutput)

        if len(findImg) <= 0:
            logFile.info(f"{net_connect['host']} Did not find the correct Bios file 0-240. Updating now...")
            con.send_multiline(scpCommandList)
            con.send_command_timing("WWTwwt1!")
            con.send_multiline(installCommandList)
            con.send_command_timing("sudo reboot")
            logFile.info(f"{net_connect['host']} Rebooting....")
            time.sleep(420) 
            
        else:
            logFile.info(f"{net_connect['host']} Found The correct Bios file 0-240, Proceed with the Golden BIOS")
    return True
          
            
def golden_bios(net_connect, logFile):
    with ConnectHandler(**net_connect) as con:

        bash_command = [
            ["sudo -s", r"#"],
            ["fwutil show status", r"#"],
        ]

        installCommandList = [
            [
                "fwutil install chassis component BIOS fw /opt/cisco/fpd/spf-ns-bios-upgrade.img",
                r"continue",
            ],
            ["y", r""],
        ]
        imgPattern = re.escape("0-240")
        bashoutput = con.send_multiline(bash_command)
        findImg = re.findall(imgPattern, bashoutput)

        if len(findImg) <= 0:
            logFile.warning('BIOS Upgrade failed')
            return False
            
        else:
            con.send_command(
                r'printf "\x07\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00" > /sys/firmware/efi/efivars/CiscoFlashSelected-59d1c24f-50f1-401a-b101-f33e0daed443'
            )
            con.send_multiline(installCommandList)
            con.send_command_timing("sudo reboot")
            logFile.info(f"{net_connect['host']} Rebooting....")
            time.sleep(420)    
    return True 
