# main.py — MASSACRES BOTNET TERMINAL REPORTER
import os
import zipfile
import random
import asyncio
import re
import socks
from colorama import Fore, Style, init
from telethon import TelegramClient
from telethon.errors import FloodWaitError, PeerIdInvalidError
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import (
    InputReportReasonSpam, InputReportReasonViolence,
    InputReportReasonPornography, InputReportReasonChildAbuse,
    InputReportReasonCopyright, InputReportReasonFake,
    InputReportReasonOther
)

# Init color
init(autoreset=True)

# ==== CONFIG ====
API_ID = 29872536
API_HASH = '65e1f714a47c0879734553dc460e98d6'
ZIP_FILE = 'sessions.zip'
PROXY_FILE = 'proxy.txt'

REASONS = {
    "spam": InputReportReasonSpam(),
    "violence": InputReportReasonViolence(),
    "pornography": InputReportReasonPornography(),
    "child_abuse": InputReportReasonChildAbuse(),
    "copyright": InputReportReasonCopyright(),
    "fake": InputReportReasonFake(),
    "other": InputReportReasonOther(),
}


def banner():
    print(Fore.RED + Style.BRIGHT + "\n" + "#" * 60)
    print(Fore.YELLOW + Style.BRIGHT + "             MASSACRES BOTNET - REPORT CONSOLE")
    print(Fore.RED + Style.BRIGHT + "#" * 60 + "\n")


def extract_sessions(zip_file):
    os.makedirs("sessions_tmp", exist_ok=True)
    sessions = []
    with zipfile.ZipFile(zip_file, 'r') as zf:
        zf.extractall("sessions_tmp")
    for file in os.listdir("sessions_tmp"):
        if file.endswith(".session"):
            path = os.path.join("sessions_tmp", file)
            sessions.append(path)
    return sessions


def load_proxies():
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    proxies.append((socks.SOCKS5, parts[0], int(parts[1]), True, None, None))
                elif len(parts) == 4:
                    proxies.append((socks.SOCKS5, parts[0], int(parts[1]), True, parts[2], parts[3]))
    return proxies


def parse_message_link(link):
    match = re.search(r"t\.me/(c|s)?/([-0-9a-zA-Z_]+)/(\d+)", link)
    if not match:
        match = re.search(r"t\.me/([-0-9a-zA-Z_]+)/(\d+)", link)
    if match:
        if match.lastindex == 3:
            return match.group(2), int(match.group(3))
    return None, None


async def send_report(client, entity, reason, msg, msg_id=None):
    try:
        target = await client.get_input_entity(entity)
        if msg_id:
            result = await client(ReportRequest(peer=target, id=[msg_id], reason=reason, message=msg))
        else:
            result = await client(ReportPeerRequest(peer=target, reason=reason, message=msg))
        return getattr(result, 'value', False)
    except FloodWaitError as e:
        print(Fore.YELLOW + f"⚠️ FloodWait: wait {e.seconds}s")
        return "flood"
    except PeerIdInvalidError:
        print(Fore.RED + "❌ Invalid entity or link!")
        return False
    except Exception as e:
        print(Fore.RED + f"❌ Error: {e}")
        return False


async def report_menu():
    banner()
    sessions = extract_sessions(ZIP_FILE)
    proxies = load_proxies()
    print(Fore.CYAN + f"🔐 Loaded sessions: {len(sessions)}")
    print(Fore.MAGENTA + f"🌐 Loaded proxies: {len(proxies)}\n")

    total = len(sessions)
    while True:
        how_many = input(Fore.GREEN + f"▶️ How many accounts to use (1 - {total}): ").strip()
        if how_many.isdigit() and 1 <= int(how_many) <= total:
            how_many = int(how_many)
            break

    print("\n🧭 What do you want to report?")
    print("1. Telegram User")
    print("2. Channel")
    print("3. Group")
    print("4. Specific Message")

    choice = input("🟢 Choice (1-4): ").strip()
    msg_id = None

    if choice == "4":
        link = input("🔗 Enter message link (public/private): ").strip()
        entity, msg_id = parse_message_link(link)
        if not entity:
            print(Fore.RED + "❌ Invalid message link format.")
            return
    else:
        entity = input("🔗 Enter username, ID, or link: ").strip()

    print("\n📚 Available reasons:")
    for i, reason in enumerate(REASONS.keys(), 1):
        print(f"{i}. {reason}")
    while True:
        r = input(Fore.GREEN + "Choose reason number: ").strip()
        if r.isdigit() and int(r) in range(1, len(REASONS) + 1):
            reason = list(REASONS.values())[int(r) - 1]
            break

    report_msg = input("📝 Enter report message: ").strip()

    count = input(f"🧮 Number of reports to send (max {how_many}): ").strip()
    count = int(count) if count.isdigit() else how_many
    count = min(count, how_many)

    selected = sessions[:count]
    success, failed, flooded = 0, 0, 0

    print(Fore.CYAN + "\n🚀 Sending reports...\n")
    for idx, session in enumerate(selected, 1):
        proxy = random.choice(proxies) if proxies else None
        client = TelegramClient(session, API_ID, API_HASH, proxy=proxy)
        try:
            await client.connect()
            result = await send_report(client, entity, reason, report_msg, msg_id=msg_id)
            if result is True:
                print(Fore.GREEN + f"[{idx}] ✅ Reported successfully")
                success += 1
            elif result == "flood":
                print(Fore.YELLOW + f"[{idx}] ⚠️ FloodWait")
                flooded += 1
            else:
                print(Fore.RED + f"[{idx}] ❌ Failed")
                failed += 1
        except Exception as e:
            print(Fore.RED + f"[{idx}] ❌ Session {session}: {e}")
            failed += 1
        finally:
            await client.disconnect()

    print(Style.BRIGHT + "\n📊 Final Report:")
    print(Fore.GREEN + f"✅ Success: {success}")
    print(Fore.YELLOW + f"⚠️ FloodWaits: {flooded}")
    print(Fore.RED + f"❌ Failed: {failed}")
    print(Fore.CYAN + "\n💀 Done.\n")


if __name__ == "__main__":
    asyncio.run(report_menu())
  
