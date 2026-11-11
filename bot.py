import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ORDER_CHANNEL_IDS = [x.strip() for x in os.getenv("ORDER_CHANNEL_IDS", "").split(",") if x.strip()]

MAIN_PHONE = "+998956208228"
BRANCH_PHONE = "+998990188228"

LOCATIONS = (
    "📍 Asosiy dorixona AVICENNA\nUrganch shahri, Xonqa ko‘chasi, 142/1\n"
    "Mo‘ljal: Gosstandart va Amu Lada avtosaloni\n☎️ +998956208228\n\n"
    "📍 Filial 1 AVICENNA\nUrganch shahri, Taraqqiyot ko‘chasi, 1-yo‘lak, 8-uy\n"
    "Mo‘ljal: Viloyat ko‘p tarmoqli tibbiyot birlashmasi\n☎️ +998990188228"
)

CATALOG = {
    "Og‘riq qoldiruvchi": ["Paratsetamol", "Ibuprofen"],
    "Vitaminlar": ["Vitamin D", "Vitamin C"],
    "Bolalar uchun": ["Bolalar parvarishi mahsulotlari"],
    "Tibbiy buyumlar": ["Bint", "Plastir"],
}

MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💊 Dorilar katalogi"), KeyboardButton("🔎 Dori qidirish")],
        [KeyboardButton("🛒 Buyurtma berish"), KeyboardButton("📍 Filiallarimiz")],
        [KeyboardButton("☎️ Operator bilan bog‘lanish"), KeyboardButton("ℹ️ Ma’lumot")],
    ], resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Assalomu alaykum! 🌿\nAVICENNA dorixonasi botiga xush kelibsiz.\nKerakli bo‘limni tanlang:",
        reply_markup=MENU
    )

async def claim_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    original = q.message.text or ""
    if "✅ Qabul qilindi:" in original:
        await q.answer("Bu buyurtmani xodim allaqachon qabul qilgan.", show_alert=True)
        return
    who = f"{user.full_name} (@{user.username})" if user.username else f"{user.full_name} (ID: {user.id})"
    await q.edit_message_text(original.replace("⏳ Holat: xodim kutilmoqda.", f"✅ Qabul qilindi: {who}"))

async def send_to_channels(context: ContextTypes.DEFAULT_TYPE, text: str, key: str):
    if not ORDER_CHANNEL_IDS:
        logging.warning("ORDER_CHANNEL_IDS sozlanmagan")
        return
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🙋‍♀️ Men qabul qilaman", callback_data=f"claim:{key}")]])
    for channel_id in ORDER_CHANNEL_IDS:
        try:
            await context.bot.send_message(
                chat_id=int(channel_id),
                text=text + "\n\n⏳ Holat: xodim kutilmoqda.",
                reply_markup=markup
            )
        except Exception:
            logging.exception("Kanalga yuborishda xato: %s", channel_id)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = (msg.text or "").strip()
    state = context.user_data.get("state")

    if state == "search":
        results = [f"• {item} — {category}" for category, items in CATALOG.items()
                   for item in items if text.casefold() in item.casefold()]
        context.user_data.pop("state", None)
        await msg.reply_text("\n".join(results) if results else
                             "Bu nom namuna katalogda topilmadi. Operator bilan aniqlashtiring.",
                             reply_markup=MENU)
        return

    if state == "name":
        context.user_data["name"] = text
        context.user_data["state"] = "phone"
        await msg.reply_text("Telefon raqamingizni yozing (masalan, +998901234567):")
        return
    if state == "phone":
        context.user_data["phone"] = text
        context.user_data["state"] = "item"
        await msg.reply_text("Kerakli mahsulot nomi va miqdorini yozing:")
        return
    if state == "item":
        name = context.user_data.get("name", "—")
        phone = context.user_data.get("phone", "—")
        username = f"@{update.effective_user.username}" if update.effective_user.username else "username yo‘q"
        key = f"{update.effective_chat.id}_{msg.message_id}"
        order = (f"🛒 YANGI AVICENNA BUYURTMA SO‘ROVI\n\n👤 Mijoz: {name}\n"
                 f"☎️ Telefon: {phone}\n💊 Mahsulot: {text}\nTelegram: {username}\n"
                 f"Buyurtma kodi: {key}\n\nXodimlardan biri «Men qabul qilaman» tugmasini bosing.")
        await send_to_channels(context, order, key)
        context.user_data.clear()
        await msg.reply_text("Rahmat! So‘rovingiz ikkala filial kanaliga yuborildi. Xodim siz bilan bog‘lanadi.",
                             reply_markup=MENU)
        return

    if text == "💊 Dorilar katalogi":
        lines = ["💊 KATALOG (NAMUNA)"]
        for category, items in CATALOG.items():
            lines.append(f"\n{category}")
            lines.extend(f"• {x}" for x in items)
        await msg.reply_text("\n".join(lines), reply_markup=MENU)
    elif text == "🔎 Dori qidirish":
        context.user_data["state"] = "search"
        await msg.reply_text("Qidirayotgan mahsulot nomini yozing:")
    elif text == "🛒 Buyurtma berish":
        context.user_data["state"] = "name"
        await msg.reply_text("Ismingizni yozing:")
    elif text == "📍 Filiallarimiz":
        await msg.reply_text(LOCATIONS, reply_markup=MENU)
    elif text == "☎️ Operator bilan bog‘lanish":
        await msg.reply_text(f"Asosiy dorixona: {MAIN_PHONE}\nFilial 1: {BRANCH_PHONE}", reply_markup=MENU)
    elif text == "ℹ️ Ma’lumot":
        await msg.reply_text(
            "AVICENNA — ishonchli dorixona.\nBuyurtma so‘rovi xodimlar tomonidan tasdiqlanadi. "
            "Dori tanlash va davolanish bo‘yicha shifokor yoki farmatsevt bilan maslahatlashing.",
            reply_markup=MENU
        )
    else:
        await msg.reply_text("Menyudan bo‘lim tanlang yoki /start yuboring.", reply_markup=MENU)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN muhit o‘zgaruvchisi kiritilmagan.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(claim_order, pattern=r"^claim:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__ == "__main__":
    main()
