"""
tools that deal with emails

@author:  Balint Takacs
@contact: takbal@gmail.com
"""

import pickle
import os.path
import base64
import mimetypes

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart

from typing import List
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def send_email(
    credentials: str,
    token: str,
    sender: str,
    to: str,
    subject: str,
    message_text: str,
    attachments: List[str],
):
    """
    send email with gmail SMTP
    # creds: credentials.json downloaded from Google API dev console
    # token: generated from credentials by this code before
    # attachments : list of filenames
    """

    creds = None

    if Path(token).exists():
        with open(token, "rb") as tk:
            creds = pickle.load(tk)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token, "wb") as tk:
            pickle.dump(creds, tk)

    service = build("gmail", "v1", credentials=creds)

    message = create_message_with_attachments(
        sender, to, subject, message_text, attachments
    )
    return send_message(service, "me", message)


def send_message(service, user_id, message):
    try:
        message = (
            service.users().messages().send(userId=user_id, body=message).execute()
        )

        print("Message Id: %s" % message["id"])

        return message
    except Exception as e:
        print("An error occurred: %s" % e)
        return None


def create_message_with_attachments(sender, to, subject, message_text, attachments):
    message = MIMEMultipart()
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject

    msg = MIMEText(message_text)
    message.attach(msg)

    for file in attachments:
        content_type, encoding = mimetypes.guess_type(file)

        if content_type is None or encoding is not None:
            content_type = "application/octet-stream"

        main_type, sub_type = content_type.split("/", 1)

        if main_type == "text":
            fp = open(file, "rb")
            msg = MIMEText(fp.read().decode("utf-8"), _subtype=sub_type)
            fp.close()
        elif main_type == "image":
            fp = open(file, "rb")
            msg = MIMEImage(fp.read(), _subtype=sub_type)
            fp.close()
        elif main_type == "audio":
            fp = open(file, "rb")
            msg = MIMEAudio(fp.read(), _subtype=sub_type)
            fp.close()
        else:
            fp = open(file, "rb")
            msg = MIMEBase(main_type, sub_type)
            msg.set_payload(fp.read())
            fp.close()
        filename = os.path.basename(file)
        msg.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(msg)

    raw_message = base64.urlsafe_b64encode(message.as_string().encode("utf-8"))
    return {"raw": raw_message.decode("utf-8")}
