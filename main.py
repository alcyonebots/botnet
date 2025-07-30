# main.py — MASSACRES BOTNET FINAL VERSION
import os, zipfile, random, asyncio, re, socks
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

# Init terminal colors
init(autoreset=True)

# === CONFIG ===
API_ID    = 29872536
API_HASH  = '65e1f714a47c0879734553dc460e98d6'
SESSION_ZIP = 'sessions.zip'
PROXY_TXT = 'proxy.txt'

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
    print(Fore.RED + Style.BRIGHT + "\n" + "#"*60)
    print(Fore.YELLOW + "         MASSACRES BOTNET - Multi-Account Tool")
    print(Fore.RED + Style.BRIGHT + "#"*60 + "\n")

def extract_sessions(zip_file):
    os.makedirs("sessions_tmp", exist_ok=True)
    sessions = []
    with zipfile.ZipFile(zip_file) as z:
        z.extractall("sessions_tmp")
    for f in os.listdir("sessions_tmp"):
        if f.endswith(".session"):
            sessions.append(os.path.join("sessions_tmp", f))
    return sessions

def load_proxies():
    proxies = []
    if os.path.exists(PROXY_TXT):
        with open(PROXY_TXT) as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    proxies.append((socks.SOCKS5, parts[0], int(parts[1]), True, None, None))
                elif len(parts) == 4:
                    proxies.append((socks.SOCKS5, parts[0], int(parts[1]), True, parts[2], parts[3]))
    return proxies

def parse_msg_link(link):
    match = re.search(r"t\.me/(c|s)?/([-_A-Za-z0-9]+)/(\d+)", link)
    if not match:
        match = re.search(r"t\.me/([-_A-Za-z0-9]+)/(\d+)", link)
    if match:
        if match.lastindex >= 2:
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
        print(Fore.YELLOW + f"⚠️ FloodWait: {e.seconds}s")
        return "flood"
    except PeerIdInvalidError:
        print(Fore.RED + "❌ Invalid entity or link.")
        return False
    except Exception as e:
        print(Fore.RED + f"❌ Error: {e}")
        return False

async def main_menu():
    banner()

    if not os.path.exists(SESSION_ZIP):
        print(Fore.RED + f"[!] {SESSION_ZIP} not found.")
        return

    sessions = extract_sessions(SESSION_ZIP)
    proxies = load_proxies()

    print(Fore.CYAN    + f"🔐 Loaded sessions: {len(sessions)}")
    print(Fore.MAGENTA + f"🌐 Loaded proxies:  {len(proxies)}\n")

    # Target amount
    report_per_session = input(Fore.GREEN + "💣 How many reports per session? ").strip()
    while not report_per_session.isdigit() or int(report_per_session) < 1:
        report_per_session = input("Enter a valid number: ").strip()
    report_per_session = int(report_per_session)

    # Report type
    print("\n🧭 What do you want to report?")
    print("1. Telegram User")
    print("2. Channel")
    print("3. Group")
    print("4. Specific Message")
    choice = input("🟢 Choice (1-4): ").strip()

    entity = ""
    msg_id = None

    # Get target
    if choice == "4":
        msg_link = input("🔗 Enter full message link (public/private): ").strip()
        entity, msg_id = parse_msg_link(msg_link)
        if not entity:
            print(Fore.RED + "❌ Invalid message link. Aborting.")
            return
    else:
        entity = input("🔗 Enter username, ID or invite link: ").strip()

    print("\n📚 Available reasons:")
    for i, k in enumerate(REASONS.keys(), 1):
        print(Fore.YELLOW + f"{i}. {k}")
    while True:
        r = input("➡ Select reason number: ").strip()
        if r.isdigit() and 1 <= int(r) <= len(REASONS):
            reason = list(REASONS.values())[int(r) - 1]
            reason_text = list(REASONS.keys())[int(r) - 1]
            break

    msg_text = input("📝 Enter report message: ").strip()
    print(Fore.CYAN + "\n🚀 Launching reports...\n")

    success, failed, flood = 0, 0, 0
    for idx, session_path in enumerate(sessions, 1):
        proxy = random.choice(proxies) if proxies else None
        client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy)
        try:
            await client.connect()
            name = os.path.basename(session_path)
            for rpt in range(report_per_session):
                result = await send_report(client, entity, reason, msg_text, msg_id=msg_id)
                status = f"[{idx}:{rpt+1}]"
                if result is True:
                    print(Fore.GREEN + f"{status} ✅ Report sent from {name}")
                    success += 1
                elif result == "flood":
                    print(Fore.YELLOW + f"{status} ⚠️ Flood limit hit from {name}")
                    flood += 1
                else:
                    print(Fore.RED + f"{status} ❌ Failed from {name}")
                    failed += 1
            await client.disconnect()
        except Exception as e:
            print(Fore.RED + f"[{idx}] ❌ Client error {e}")
            failed += 1

    total_attempts = len(sessions) * report_per_session
    print(Style.BRIGHT + "\n📊 Final Report Summary:")
    print(Fore.GREEN + f"✅ Successful: {success}")
    print(Fore.YELLOW + f"⚠️  FloodWaits:  {flood}")
    print(Fore.RED + f"❌ Failed:     {failed}")
    print(Fore.CYAN + f"🧮 Total Attempts: {total_attempts}")
    print(Fore.GREEN + "\n🎯 Done.\n")

if __name__ == "__main__":
    asyncio.run(main_menu())
    
