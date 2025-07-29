# sessions.py
import zipfile
import os
from telethon.sessions import StringSession
from telethon import TelegramClient
from config import API_ID, API_HASH
from proxy_manager import get_random_proxy
from mongodb import store_session

async def extract_and_store_sessions(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as archive:
        archive.extractall("temp_sessions/")

    count = 0
    for file in os.listdir("temp_sessions/"):
        if file.endswith(".session"):
            filepath = f"temp_sessions/{file}"
            try:
                with open(filepath, "r") as f:
                    session_string = f.read()

                client = TelegramClient(
                    StringSession(session_string),
                    API_ID,
                    API_HASH,
                    proxy=get_random_proxy()
                )
                await client.connect()
                if await client.is_user_authorized():
                    store_session(session_string)
                    count += 1
                await client.disconnect()
            except Exception:
                pass
    return count
  
