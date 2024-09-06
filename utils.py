from email.mime.text import MIMEText
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
import base64
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
import requests
import json
from langchain.tools import tool
import tempfile

import tweepy
import requests
from PIL import Image
import logging
import random
import re
from bs4 import BeautifulSoup
import shutil
import urllib
# import markdown


def twitter_tweet(tweet, consumer_key, consumer_secret, access_token, access_token_secret):

    try:
        client = tweepy.Client(consumer_key=consumer_key, consumer_secret=consumer_secret, 
                        access_token=access_token, access_token_secret=access_token_secret)
    
        tweet = tweet.strip('"')
        res = client.create_tweet(text=tweet)
        return 'Twitter tweet generated and posted to user twitter account successfully'
    except Exception as e:
        return Exception(f"Failed to tweet: {e}")

# Constants
SCOPES_DRIVE = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'
PARENT_FOLDER_ID = "1REXfwxk9dcPdpZXJOFZSur3880soVN9y"


# Authenticate and return credentials for Google Drive
def authenticate_drive():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES_DRIVE)
    return credentials

# Upload file to Google Drive
def upload_file(filepath, filename, parent_folder_id):
    creds = authenticate_drive()
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': filename,
        'parents': [parent_folder_id]
    }

    media = MediaFileUpload(filepath, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'File ID: {file.get("id")}')
    return file.get('id')

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def authenticate_gmail():
    """Authenticate and return the Gmail service."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    return service

def send_email(to_email, subject, body):
    """Tool to send email"""
    try:
        msg = MIMEMultipart('alternative')
        msg['to'] = to_email
        msg['subject'] = subject

        part2 = MIMEText(body, 'html')
        msg.attach(part2)

        raw_string = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        service = authenticate_gmail()
        sent_message = service.users().messages().send(userId='me', body={'raw': raw_string}).execute()

        print(sent_message)
        print('Email sent successfully!')
        return 'Email sent successfully!'
    except Exception as e:
        print(f'Error sending email: {str(e)}')
        return f'Error sending email: {str(e)}'

def escape_text(text):
    chars = ["\\", "|", "{", "}", "@", "[", "]", "(", ")", "<", ">", "#", "*", "_", "~"]
    for char in chars:
        text = text.replace(char, "\\"+char)
    return text

def get_urn(token):
    url = 'https://api.linkedin.com/v2/userinfo'

    headers = {
        'Authorization': f'Bearer {token}'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        print(user_info['sub'])
        return user_info['sub']
    else:
        print(f'Failed to fetch user info: {response.status_code}')
        print(response.text)

def post_image_and_text(token, title, text_content, image_path):
    """
    Posts an article on LinkedIn with an image.

    Args:
    token: LinkedIn OAuth token.
    title: LinkedIn post title.
    text_content: LinkedIn post content.
    image_path: file path of the image.
    """

    text_content = escape_text(text_content)

    owner = get_urn(token)
    if image_path.startswith('sandbox'):
        image_path = image_path.split(':')[1]
    image_path = image_path.strip()

    # Initialize the upload to get the upload URL and image URN
    init_url = "https://api.linkedin.com/rest/images?action=initializeUpload"
    headers = {
        "LinkedIn-Version": "202401",
        "X-RestLi-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    init_data = json.dumps({"initializeUploadRequest": {"owner": f'urn:li:person:{owner}'}})
    init_response = requests.post(init_url, headers=headers, data=init_data)
    print(init_response.content)
    if init_response.status_code != 200:
        raise Exception(f"Failed to initialize upload: {init_response.text}")

    init_response_data = init_response.json()["value"]
    upload_url = init_response_data["uploadUrl"]
    image_urn = init_response_data["image"]

    # Upload the file
    with open(image_path, "rb") as f:
        upload_response = requests.post(upload_url, files={"file": f})
        if upload_response.status_code not in [200, 201]:
            raise Exception(f"Failed to upload file: {upload_response.text}")

    # Create the post with the uploaded image URN as thumbnail
    post_url = "https://api.linkedin.com/rest/posts"
    post_data = json.dumps(
        {
            "author": f'urn:li:person:{owner}',
            "commentary": text_content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "media": {
                    "title": title,
                    "id": image_urn,
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
    )
    post_response = requests.post(post_url, headers=headers, data=post_data)
    print(post_response.content)
    if post_response.status_code in [200, 201]:
        return "Linkedin article has been posted successfully!"
    else:
        raise Exception(f"Failed to post article: {post_response.text}")    
    