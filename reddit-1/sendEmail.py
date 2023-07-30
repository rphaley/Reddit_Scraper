##### SMTP Example #####

import base64, logging, os, smtplib
from email.mime.text import MIMEText

def sendEmail(config, debug, title,url,CN, postBody, author, postResponse):
    try:
        fromaddr = config.get('EmailSettings', 'FromAddress')
        toaddrs = config.get('EmailSettings', 'ToAddress')
        smtp_server = "smtp.gmail.com:587"
        username = config.get('EmailSettings', 'Username')   
        pass_env_var = config.get('EmailSettings', 'PasswordEnvVar')
        password = os.environ[pass_env_var]  
  #      password=password.decode("utf-8")  
    except Exception as e:
        print(f'[-] Error reading email settings from config file: {e}')
        return
    
    #Compose Message
    title = "[{}] {}".format(CN,title)
    try:
        message = MIMEText(f'POST: {postBody}<br><br>AUTHOR: <a href="https://reddit.com/u/{author}">{author}</a><br><br>LINK: {url}<br><br>RESPONSE: {postResponse}', 'html')
    except Exception as e:
        print(f'[-] Error formatting email message: {e}')
        return
    message['From'] = f'Reddit Bot <{fromaddr}>'
    message['To'] = f'{toaddrs} <{toaddrs}>'
    message['Subject'] = title
    body = message.as_string()
          

    
    try:
        server = smtplib.SMTP(smtp_server)
        server.ehlo()
        server.starttls()
        server.ehlo()
        if debug == 1: print("[+] Email server accepted connection")
    except Exception as e:
        print (f"[-] Error connecting to email server: {e}")
        return 
    try:
        if debug == 1: print(f"Attempting to login with: {username} {type(username)} and password type {type(password)}")
        server.login(username,password)
        if debug == 1: print("[+] Email server accepted login credentials")
    except Exception as e:
        print (f"[-] Error loggin into email server: {e}")
        return
    try:
        server.sendmail(fromaddr, toaddrs,body)
        if debug == 1: print("[+] Email server accepted email to be sent")
        server.quit()
    except Exception as e:
        print (f"[-] Error sending email: {e}")
        return
        

