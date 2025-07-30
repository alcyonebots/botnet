# bot.py
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from config import BOT_TOKEN, ADMIN_IDS
from sessions import extract_and_store_sessions
from mongodb import get_all_sessions
from reporter import report_all, REASONS
from proxy_manager import load_proxies_from_file

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
        return await update.message.reply_text("❌ Please upload a valid .zip file.")

    file = await doc.get_file()
    zip_path = await file.download_to_drive("sessions.zip")
    count = await extract_and_store_sessions(zip_path)
    await update.message.reply_text(f"✅ Imported {count} session(s).\nUse /report to start.")


async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text("📎 Upload your SOCKS5 proxy.txt file (format: `host,port[,user,pass]`).")


async def handle_proxy_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        return await update.message.reply_text("❌ Invalid file. Please upload a .txt proxy list.")
    file = await doc.get_file()
    path = await file.download_to_drive("proxy.txt")
    load_proxies_from_file(path)
    await update.message.reply_text("✅ Proxies loaded. They will be used during reporting.")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    buttons = [
        [InlineKeyboardButton("User", callback_data="type_user"),
         InlineKeyboardButton("Channel", callback_data="type_channel")],
        [InlineKeyboardButton("Group", callback_data="type_group"),
         InlineKeyboardButton("Message", callback_data="type_msg")]
    ]
    await update.message.reply_text("📝 What would you like to report?",
                                    reply_markup=InlineKeyboardMarkup(buttons))
    context.user_data["step"] = "awaiting_type"


async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["report_type"] = query.data.replace("type_", "")
    context.user_data["step"] = "target"
    await query.edit_message_text("👉 Send the @username or ID of the target.")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return

    step = context.user_data.get("step")

    if step == "target":
        context.user_data["target"] = update.message.text
        reason_buttons = [
            [InlineKeyboardButton(reason.capitalize(), callback_data=f"reason_{reason}")]
            for reason in REASONS.keys()
        ]
        await update.message.reply_text("❓ Choose report reason:",
                                        reply_markup=InlineKeyboardMarkup(reason_buttons))
        context.user_data["step"] = "reason"

    elif step == "msg":
        context.user_data["report_text"] = update.message.text
        await update.message.reply_text("📊 How many reports do you want to send (total accounts to use)?")
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
                context.user_data["report_text"],
                msg_id=context.user_data.get("msg_id")
            )

            await update.message.reply_text(f"✅ Report complete: {success}/{len(to_use)} sent successfully.")
            context.user_data.clear()

        except Exception as e:
            await update.message.reply_text(f"⚠️ Invalid input: {e}")


async def reason_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reason = query.data.replace("reason_", "")
    context.user_data["reason"] = reason
    context.user_data["step"] = "msg"
    await query.edit_message_text("📝 Send the report message to include in each report.")


async def main():

    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("refresh", refresh_command))
    app.add_handler(CommandHandler("report", report_command))

    app.add_handler(CallbackQueryHandler(inline_handler, pattern="type_"))
    app.add_handler(CallbackQueryHandler(reason_handler, pattern="reason_"))

    app.add_handler(MessageHandler(filters.Document.MimeType("application/zip"), handle_zip_file))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), handle_proxy_file))    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    print("🤖 Reporting Bot is running...")
    app.run_polling()
