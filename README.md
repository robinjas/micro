# VM Name: Microsoft_Arista_ZTP

- OS Centos7
- vLAN: 2226
- vLAN 2226 Server IP Address: 192.168.110.1/24
- Server Corp IP Address: 10.150.68.60/24
- DNS Name: naic2_msft_ztp.wwt.com
- Provides DHCP in range 192.168.110.50 - 192.168.110.254
- Script Code runs here
- Runs an appache HTTP server
  - files are located at /var/www/html/
- Group Credentails
  - [Arista_VM_Login](https://wwt.secretservercloud.com/app/#/secret/9797/general)

  
# Avocent
- IP: 192.168.110.3
- Gateway: 192.168.110.1 (I doubt this is needed? Remove if seeing issues
)
# CentOS 7 Commands

Check the DHCP Configuration \
cat /etc/dhcp/dhcpd.conf

Become Super User \
sudo su

Graphical IP Interface \
nmtui

Upgrade Process Sonic to Sonic 10 minutes

View DHCP Leases \
cat /var/lib/dhcpd/dhcpd.leases

Add Files to HTTP Server \
mv filename.bin /var/www/html/filename.bin

Ensure Files Are in the HTTP Server \
http://10.150.68.60/



# Project Documentation

- Project files = `(M:\Network_repository\Microsoft\GICLAB0020894_Cisco 8102 Remediation\Project Execution Documentation\SONiC)`

- MOP = `(prd1nas.wwt.com\itc_lab\Network_repository\Microsoft\GICLAB0020894_Cisco 8102 Remediation\Project Execution Documentation\SONiC\SONiC-Instructions-v3-July27.pdf)`
- 
- SRF Instructions = `M:\Network_repository\Microsoft\GICLAB0020894_Cisco 8102 Remediation\Project Execution Documentation`

- Revert Proccess = [link](https://support.edge-core.com/hc/en-us/articles/900000208626--Edgecore-SONiC-Installation-Upgrade-image)

