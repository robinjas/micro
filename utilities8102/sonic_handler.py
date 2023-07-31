from netmiko import exceptions as ne
import netmiko as netmiko
import threading
import time
import logging
import threading

def threadify(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper

send_reboot = 'sudo reboot now'
# current_ver = self.send_command_timing("sudo sonic-installer list").split()[1]
current_ver_list = "sudo sonic-installer list"


class SonicSSHConnection(LinuxSSH):
    log = logging.getLogger(__name__)

    
    def _version(self, target_image):
        with self._conn as connection:
            try:
                connection.enable()
                current_image = connection.send_command("sonic-installer list").split()[1]
                if current_image != target_image:
                    self.output = False
                else:
                    self.output = True
            except ne.ReadTimeout as time_ex:
                ...

    def _reboot(self):
        with self._conn as connection:
            try:
                connection.enable()
                self.output = connection.send_command('shutdown -r now')
                self._conn.disconnect()
                x=0

                while True:
                    if x <= 900:
                        try:
                            print(connection.is_alive())
                            if connection.is_alive():
                                print('its alive')
                                break
                            print("auto connect " + connection.auto_detect())
                            print("establish " + connection.establish_connection())
                            print('==========================================')
                            x+=1
                        except:
                            x+=1
                    else:
                        break
                        
            except Exception as ex:
                ...

    def _show_version(self):
        with self._conn as connection:
            try:
                self.output = connection.send_command('show version')
            except:
                ...


    @threadify
    def get_serial(self):
        return self._serial()
    
    @threadify
    def get_version(self, sonicVersion):
        return self._version(sonicVersion)

    @threadify
    def send_reboot(self):
        return self._reboot()

    @threadify
    def get_show_version(self):
        try:
            self.output = self._conn.send_command('show version')
        except ne.ReadTimeout as time_ex:
            ...

    def update_os(self):
        os = self.version
        if self.is_upgraded:
            self.log.info(f"{self.get_serial()} ios is already updated continuing...")
            return
        try:
            cmd_output = self._conn.send_command(
                command_string= f'sonic-installer install /tmp/{image_name}',
                expect_string=r'(yes/no)?',
                strip_prompt=False,
                strip_command=False
            )
            cmd_output += self._conn.send_command(
                command_string='yes',
                expect_string='password',
                strip_command=False,
                strip_prompt=False
            )
            self._reboot()
            self._conn.disconnect()
            time.sleep(900)
            self._conn
            self._version()
            if not self.is_upgraded:
                time.sleep(120)
                self._version()
            self.log.warning(f"{self.serial} ios upgrade status is {self.is_upgraded} ")

        except ne.ReadTimeout as e:
            self.log.warning(f"{self.serial} Error during update, returned {e}")
            return
