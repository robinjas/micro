from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ipaddress import ip_address
import smtplib


class Email():

    def get_email_settings(toField):
        '''Gets all of the email settings we will need for sending the email'''
        
        fromField = "8102_Errors@wwt.com"
        subject = "Errors 8102"
        IP = 'mailhost.wwt.com'
        port = "25"
        emailSettings = {'from':fromField,'to':toField,'subject':subject,"ip":IP,"port":port}
        return emailSettings

    def Send_Email(message,settings):
        '''Actually sends the email.'''

        from_field = settings['from']  # "First Last <first.last@wwt.com>"
        to_field = ', '.join(
            settings['to']
        )  # ["First Last <first.last@wwt.com>", "First Last <first.last@wwt.com>"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = settings['subject']  # string
        msg["From"] = from_field
        msg["To"] = to_field
        text = f"{message}\n\nPlease Reach Out to the PE to troubleshoot"
        part1 = MIMEText(text, "plain")
        msg.attach(part1)
        server = smtplib.SMTP(settings['ip'], settings['port'])
        # server.sendmail(from_field, to_field, msg.as_string())
        server.send_message(msg)
        server.quit()
        print(msg)
        print("\nThe email was sent successfully!\n")

    def format_email(errorList, directory,settings):
        '''Reads in a given list of errors and puts it all together into a
        single formatted email and sends out the email to the users specified
        in the task from Terry Largent.'''
        
        # Our email function needs to send a single email as a single string, so let's build that out
        emailStr = directory + "\n\n"
        # Count the files with errors and replace 'XYZ' in emailStr with it
        count = 0
        for name,err in errorList.items():
            emailStr += f"{name}\n"
            for error in err:
                emailStr += f"\t\t{error}\n"
                count += 1
        # X3YqZ was a placeholder for the number of devices
        emailStr = emailStr.replace('X3YqZ', str(count))
        # Send the email
        Email.Send_Email(emailStr,settings)