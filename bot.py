# bot.py
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
import os

from config import BOT_TOKEN, ADMIN_IDS
from sessions import extract_and_store_sessions
from mongodb import get_all_sessions
from reporter import report_all, REASONS
from proxy_manager import load_proxies_from_file

# /start and /help commands
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    with open("help_text.md", "r") as f:
        await update.message.reply_text(f.read())

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text("📎 Send a .zip file containing your .session files.")

async def handle_zip_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    doc = update.message.document
    if not doc.file_name.endswith(".zip"):
        return await update.message.reply_text("Please send a valid .zip file.")
    
    file = await doc.get_file()
    zip_path = await file.download_to_drive("sessions.zip")
    count = await extract_and_store_sessions(zip_path)
    await update.message.reply_text(f"✅ Imported {count} sessions.\nUse /report to start.")

async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text("Please upload your `proxy.txt` SOCKS5 proxy list.")

async def handle_proxy_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        return await update.message.reply_text("❌ Not a .txt file.")
    file = await doc.get_file()
    path = await file.download_to_drive("proxy.txt")
    load_proxies_from_file(path)
    await update.message.reply_text("✅ Proxies loaded.")

# Interactive report entry
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    buttons = [
        [InlineKeyboardButton("User", callback_data="type_user"),
         InlineKeyboardButton("Channel", callback_data="type_channel")],
        [InlineKeyboardButton("Group", callback_data="type_group"),
         InlineKeyboardButton("Message", callback_data="type_msg")]
    ]
    await update.message.reply_text("Select what to report:", reply_markup=InlineKeyboardMarkup(buttons))
    context.user_data["step"] = "awaiting_type"

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["report_type"] = query.data.replace("type_", "")
    await query.edit_message_text("Send target @username or ID:")
    context.user_data["step"] = "target"

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return

    step = context.user_data.get("step")
    
    if step == "target":
        context.user_data["target"] = update.message.text
        reason_buttons = [
            [InlineKeyboardButton(x.capitalize(), callback_data=f"reason_{x}")]
            for x in REASONS.keys()
        ]
        await update.message.reply_text("Select reason:", reply_markup=InlineKeyboardMarkup(reason_buttons))
        context.user_data["step"] = "reason"
    
    elif step == "msg":
        context.user_data["report_text"] = update.message.text
        await update.message.reply_text("📈 How many reports to send?")
        context.user_data["step"] = "count"
    
    elif step == "count":
        try:
            count = int(update.message.text)
            await update.message.reply_text("⏳ Sending reports...")

            all_sessions = get_all_sessions()
            to_use = all_sessions[:count]
            success = await report_all(
                to_use,
                context.user_data["target"],
                context.user_data["reason"],
                context.user_data["report_text"]
            )
            await update.message.reply_text(f"✅ {success}/{len(to_use)} reports sent successfully.")
            context.user_data.clear()
        except:
            await update.message.reply_text("Invalid number.")

async def reason_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reason = query.data.replace("reason_", "")
    context.user_data["reason"] = reason
    context.user_data["step"] = "msg"
    await query.edit_message_text("✍ Send report message text:")

# App startup
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("refresh", refresh_command))
    app.add_handler(CommandHandler("report", report_command))

    app.add_handler(CallbackQueryHandler(inline_handler, pattern="type_"))
    app.add_handler(CallbackQueryHandler(reason_handler, pattern="reason_"))

    app.add_handler(MessageHandler(filters.Document.FILE, handle_zip_file))
    app.add_handler(MessageHandler(filters.Document.TEXT, handle_proxy_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🤖 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
  
