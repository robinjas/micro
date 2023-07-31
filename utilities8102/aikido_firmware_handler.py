class aikido_handler():
    def __init__(self):
        pass

    def restart(self, ip, port):
        '''
        input pdu port number of pdu to restart port
        '''
        pass

    def get_akido_version(self, connect, logFile, akidoVer):

        fwutilList = connect.send_command_timing("sudo fwutil show status")
        activeVersion = fwutilList.split('Aikido')[1].strip()

        return activeVersion == akidoVer, f"sudo fwutil show status\n\n{fwutilList}"