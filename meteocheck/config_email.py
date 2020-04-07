# -*- coding: utf-8 -*-
"""
Created on Fri Jan 13 17:51:20 2017

@author: Ruben
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import configparser
import os
from pathlib import Path

# Configuration files
config = configparser.ConfigParser(interpolation=None, inline_comment_prefixes='#')

working_path = os.getcwd() # tries to read config file from the Current Working Directory where meteocheck is invoked
config.read(str(Path(working_path, 'meteocheck_email.ini')))

IS_SENDING_EMAIL = config.getboolean('email_configuration', 'IS_SENDING_EMAIL')
RECIPIENTS_EMAIL = config.get('email_configuration', 'RECIPIENTS_EMAIL').split(',') # It can be a list of several
SENDER_EMAIL = config.get('email_configuration', 'SENDER_EMAIL')
SMTP_SERVER = config.get('email_configuration', 'SMTP_SERVER')
SMTP_PORT = config.getint('email_configuration', 'SMTP_PORT')
LOGIN_EMAIL = config.get('email_configuration', 'LOGIN_EMAIL')
PASSWORD_EMAIL = config.get('email_configuration', 'PASSWORD_EMAIL')


def send_email(
                body,
                subject,
                list_figures,
                receivers=RECIPIENTS_EMAIL,
                sender=SENDER_EMAIL,
                smtp_server=SMTP_SERVER,
                smtp_port=SMTP_PORT,
                login=LOGIN_EMAIL,
                password=PASSWORD_EMAIL):
    """
    Sends an email with the log content.

    Parameters
    ----------
    body : String
        Email body text
    subject : String
        Email subject text
    receivers : list
        list of email addresses (Strings)
    sender : String
        Path of the analyzed file
    figure : plt.figure()
        MPL's figure describing the error

    Returns
    -------
    None
    """
    msg = MIMEMultipart()
    msg['To'] = ', '.join(receivers)
    msg['From'] = sender
    msg['Subject'] = subject

    msgText = MIMEText(body, 'html')
    msg.attach(msgText)

    for index, buffer in list_figures:
        if buffer is not None:
            msgText = MIMEText(
                '<br><img src="cid:{}"><br>'.format(index), 'html')
            msg.attach(msgText)   # Added, and edited the previous line

            img = MIMEImage(buffer.read())

            img.add_header('Content-ID', '<{}>'.format(index))
            msg.attach(img)

#    msg.as_string()
    # Send the message via local SMTP server.
    smtp = smtplib.SMTP(smtp_server, smtp_port)
    smtp.ehlo()
    smtp.starttls()

    smtp.login(login, password)
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    smtp.sendmail(sender, receivers, msg.as_string())
    smtp.quit()