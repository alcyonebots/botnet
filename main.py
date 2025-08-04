import asyncio
import logging
import os
import glob
from telethon import TelegramClient
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonChildAbuse,
    InputReportReasonCopyright,
    InputReportReasonFake,
    InputReportReasonOther,
)
import socks

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

API_ID = "29872536"
API_HASH = "65e1f714a47c0879734553dc460e98d6"

# Directory containing session files
SESSIONS_DIR = "sessions"

# Reasons for reporting
REPORT_REASONS = {
    "spam": InputReportReasonSpam(),
    "violence": InputReportReasonViolence(),
    "pornography": InputReportReasonPornography(),
    "child abuse": InputReportReasonChildAbuse(),
    "copyright infringement": InputReportReasonCopyright(),
    "scam": InputReportReasonFake(),
    "other": InputReportReasonOther(),
}


def load_socks5_proxies(file_path="proxy.txt"):
    """Load SOCKS5 proxies from a file."""
    try:
        with open(file_path, "r") as f:
            proxies = []
            for line in f.readlines():
                if line.strip():
                    parts = line.strip().split(":")
                    if len(parts) >= 2:
                        # Format: host:port or host:port:username:password
                        host = parts[0]
                        port = int(parts[1])
                        username = parts[2] if len(parts) > 2 else None
                        password = parts[3] if len(parts) > 3 else None
                        proxies.append((host, port, username, password))
        return proxies
    except FileNotFoundError:
        logger.error(f"Proxy file '{file_path}' not found.")
        return []


def get_session_files():
    """Get all .session files from the sessions directory."""
    if not os.path.exists(SESSIONS_DIR):
        logger.error(f"Sessions directory '{SESSIONS_DIR}' not found.")
        return []
    
    session_files = glob.glob(os.path.join(SESSIONS_DIR, "*.session"))
    logger.info(f"Found {len(session_files)} session files in '{SESSIONS_DIR}' directory")
    return session_files


async def connect_sessions(proxies, required_count):
    """Connect to existing session files with SOCKS5 proxy support."""
    session_files = get_session_files()
    if not session_files:
        logger.error("No session files found!")
        return []
    
    connected_clients = []
    
    for i, session_file in enumerate(session_files[:required_count]):
        session_name = os.path.splitext(os.path.basename(session_file))[0]
        
        for retry in range(5):
            proxy = None
            if proxies:
                proxy_info = proxies[(i + retry) % len(proxies)]
                proxy = (socks.SOCKS5, proxy_info[0], proxy_info[1])
                if proxy_info[2] and proxy_info[3]:  # username and password provided
                    proxy = proxy + (True, proxy_info[2], proxy_info[3])
            
            try:
                client = TelegramClient(
                    session_file,
                    API_ID,
                    API_HASH,
                    proxy=proxy
                )
                
                await client.connect()
                
                if await client.is_user_authorized():
                    logger.info(f"Connected to session: {session_name} using SOCKS5 Proxy: {proxy}")
                    connected_clients.append(client)
                    break
                else:
                    logger.warning(f"Session {session_name} not authorized. Skipping.")
                    await client.disconnect()
                    break
                    
            except Exception as e:
                logger.warning(f"Proxy issue for session {session_name}: {proxy}. Retrying... ({retry + 1}/5)")
                if retry == 4:
                    logger.error(f"Failed to connect session {session_name} after 5 retries")
    
    return connected_clients


async def report_entity(client, entity, reason, times_to_report, message, msg_id=None):
    """Report a peer or specific message."""
    try:
        if reason not in REPORT_REASONS:
            logger.error(f"Invalid report reason: {reason}")
            return 0

        entity_peer = await client.get_input_entity(entity)
        successful_reports = 0

        for _ in range(times_to_report):
            try:
                if msg_id:
                # First fetch the message to get the sender as participant
                msg = await client.get_messages(target, ids=msg_id)
                sender = await client.get_input_entity(msg.sender_id)

                # Report that specific message in the context of the channel
                await client(functions.channels.ReportSpamRequest(
                    channel=target,
                    participant=sender,
                    id=[msg_id]
                    ))
    
                else:
                    result = await client(ReportPeerRequest(
                        peer=entity_peer,
                        reason=REPORT_REASONS[reason],
                        message=message
                    ))

                if result:
                    successful_reports += 1
                    logger.info(f"[✓] Reported {entity} {'message' if msg_id else 'peer'} for {reason}.")
                else:
                    logger.warning(f"[✗] Failed to report {entity}.")
            except Exception as e:
                logger.error(f"Error during report attempt for {entity}: {str(e)}")

        return successful_reports

    except Exception as e:
        logger.error(f"Failed to report {entity}: {str(e)}")
        return 0


async def main():
    print("\n=== Telegram Multi-Account Reporter (SOCKS5 + Session Files) ===\n")
    
    # Load available session files
    session_files = get_session_files()
    if not session_files:
        print("[✗] No session files found in 'sessions' directory!")
        return
    
    print(f"[✓] Found {len(session_files)} session files")
    
    account_count = int(input(f"Enter the number of accounts to use (max {len(session_files)}): "))
    account_count = min(account_count, len(session_files))
    
    # Load SOCKS5 proxies
    proxies = load_socks5_proxies()
    if proxies:
        print(f"[✓] Loaded {len(proxies)} SOCKS5 proxies")
    else:
        print("[!] No proxies loaded, connecting without proxy")
    
    # Connect to sessions
    clients = await connect_sessions(proxies, account_count)
    
    if not clients:
        print("[✗] No clients could be connected!")
        return
    
    print(f"[✓] Successfully connected {len(clients)} clients")

    print("\nSelect what you want to report:")
    print("1 - Group")
    print("2 - Channel")
    print("3 - User")
    print("4 - Specific message in a chat")
    choice = int(input("Enter your choice (1/2/3/4): "))

    if choice == 4:
        entity = input("Enter the chat username or ID: ").strip()
        msg_id = int(input("Enter the message ID to report: "))
    else:
        entity = input("Enter the group/channel username or user ID to report: ").strip()
        msg_id = None

    print("\nAvailable reasons for reporting:")
    for idx, reason in enumerate(REPORT_REASONS.keys(), 1):
        print(f"{idx} - {reason.capitalize()}")
    reason_choice = int(input("Enter your choice: "))
    reason = list(REPORT_REASONS.keys())[reason_choice - 1]

    times_to_report = int(input("Enter how many times each account should report: "))
    message = input("Enter custom report message: ").strip()

    # Execute reporting
    tasks = [
        report_entity(client, entity, reason, times_to_report, message, msg_id=msg_id)
        for client in clients
    ]
    results = await asyncio.gather(*tasks)
    total_successful_reports = sum(results)

    print(f"\n[✓] Total successful reports submitted: {total_successful_reports}")

    # Disconnect all clients
    for client in clients:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

