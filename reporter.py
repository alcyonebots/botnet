# reporter.py
from telethon import TelegramClient
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import (
    InputReportReasonSpam, InputReportReasonViolence,
    InputReportReasonPornography, InputReportReasonChildAbuse,
    InputReportReasonCopyright, InputReportReasonFake,
    InputReportReasonOther
)
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, PeerIdInvalidError
from config import API_ID, API_HASH
from proxy_manager import get_random_proxy

REASONS = {
    "spam": InputReportReasonSpam(),
    "violence": InputReportReasonViolence(),
    "pornography": InputReportReasonPornography(),
    "child_abuse": InputReportReasonChildAbuse(),
    "copyright": InputReportReasonCopyright(),
    "fake": InputReportReasonFake(),
    "other": InputReportReasonOther(),
}

async def report_all(session_strings, entity, reason, text, msg_id=None):
    success = 0
    for session_string in session_strings:
        try:
            client = TelegramClient(
                StringSession(session_string),
                API_ID,
                API_HASH,
                proxy=get_random_proxy()
            )
            await client.connect()
            peer = await client.get_input_entity(entity)
            if msg_id:
                res = await client(ReportRequest(peer=peer, id=[int(msg_id)], reason=REASONS[reason], message=text))
            else:
                res = await client(ReportPeerRequest(peer=peer, reason=REASONS[reason], message=text))
            if getattr(res, "value", False):
                success += 1
            await client.disconnect()
        except FloodWaitError as e:
            continue
        except Exception:
            continue
    return success
  
