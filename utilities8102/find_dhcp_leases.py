from utilities8102 import connection_handler as CH
from netmiko import ConnectHandler
import threading

online_host = {}

def find_leases(backend_log, envDict):
    ''' Connect to server to find dhcp leases '''

    connect = ConnectHandler(host=envDict["GATEWAYIP"], username=envDict["GATEWAYUSERNAME"], password=envDict["GATEWAYPASSWORD"], device_type="linux")
    
    if connect != False:
        dhcp_leases = (
            connect.send_command(
                "cat /var/lib/dhcpd/dhcpd.leases | grep 'sonic\|localhost\|lease'"
            )
            .replace("{", "")
            .replace(";", "")
            .split("lease")
        )

        
        # filter out the output to find the values of IP and Clienthost, if IP has Clienthost append the those values in a dictionary
        for line in dhcp_leases:
            if "client" in line:
                line = line.replace("\n", "").replace("'", "").replace(" 192", "192")
                ip = line.split(" ")[0]
                hostname = line.split('"')[1]
                if ip not in online_host.keys():
                    online_host[ip] = {"client_hostname": hostname}

        # loop through IP list and try to connect, if ip connects then append true else append false.
        threads = []

        for ip_address in online_host.keys():
            x = threading.Thread(target=test_ip_connections, args=(ip_address, envDict, backend_log,))
            threads.append(x)
            x.start()

        # Waits until all of the ips are completed before starting on to the next part
        for thread in threads:
            thread.join()

    return online_host

def test_ip_connections(ip_address, envDict, backend_log):

    are_we_connected = CH.device_login(ip_address, envDict, qc_log=backend_log)
    if are_we_connected != False:
        online_host[ip_address]["are_we_connected"] = True
        device_serial = are_we_connected.send_command(
            "sudo dmidecode -s system-serial-number"
        )
        online_host[ip_address]["device_serial"] = device_serial
        backend_log.info(f"Found serial {device_serial} with an ip of {ip_address}")
    else:
        online_host[ip_address]["are_we_connected"] = False
        online_host[ip_address]["device_serial"] = "N/A"
        backend_log.warning(f"{ip_address} had an invalid connection")

def filtered_active_leases(backend_log, envDict):
    # leases that have existed before filtering out True connection state
    
    dhcp_leases = find_leases(backend_log, envDict)
    updated_dhcp_leases = {}
    
    for ip, ipData in dhcp_leases.items():
        if ipData["are_we_connected"]:
            updated_dhcp_leases[ip] = ipData

    return updated_dhcp_leases
