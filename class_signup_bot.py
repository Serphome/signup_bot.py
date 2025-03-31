from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

TOKEN = "7591293600:AAFTRcvRuaUAVNZAok75mkyX3tRIkDc6Uvg"
TEACHER_ID = 6158059440

# Временные слоты занятий
time_slots = {
    "tue": ["16:00-17:00", "17:00-18:00", "18:00-19:00", "19:00-20:00"],
    "wed": ["16:00-17:00", "17:00-18:00", "18:00-19:00", "19:00-20:00"],
    "thu": ["16:00-17:00", "17:00-18:00", "18:00-19:00", "19:00-20:00"],
    "fri": ["16:00-17:00", "17:00-18:00", "18:00-19:00", "19:00-20:00"],
}
day_names = {"tue": "Вторник", "wed": "Среда", "thu": "Четверг", "fri": "Пятница"}

appointments = {}
appointment_times = {}
user_names = {}


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Записаться", callback_data="signup")],
        [InlineKeyboardButton("🔍 Мои записи", callback_data="mybookings")],
        [InlineKeyboardButton("⏳ Изменить запись", callback_data="change")],
        [InlineKeyboardButton("❌ Отменить запись", callback_data="cancel")],
    ]
    if update.effective_user.id == TEACHER_ID:
        keyboard.append([InlineKeyboardButton("📜 Все записи", callback_data="view")])
        keyboard.append([InlineKeyboardButton("🔄 Сброс записей", callback_data="reset")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_chat.send_message("Выбери действие:", reply_markup=reply_markup)

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_names:
        await update.message.reply_text("Как тебя зовут? Напиши свое имя:")
    else:
        await main_menu(update, context)

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.text
    user_link = f"[{user_name}](tg://user?id={user_id})"
    user_names[user_id] = user_link
    await main_menu(update, context)

async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(day_names[day], callback_data=f"day_{day}")] for day in time_slots]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text("Выбери день:", reply_markup=reply_markup)

async def select_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    day = query.data.split("_")[1]

    free_slots = [time for time in time_slots[day] if
                  f"{day}_{time}" not in appointments.get(user_names[query.from_user.id], [])]
    if not free_slots:
        await query.answer("Нет свободных мест на этот день!", show_alert=True)
        return

    keyboard = [[InlineKeyboardButton(time, callback_data=f"time_{day}_{time}")] for time in free_slots]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="signup")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"Ты выбрал {day_names[day]}. Теперь выбери время:", reply_markup=reply_markup)

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, day, time = query.data.split("_")
    slot = f"{day}_{time}"
    user_id = query.from_user.id

    user_link = user_names[user_id]
    if user_link not in appointments:
        appointments[user_link] = []

    appointments[user_link].append(slot)
    appointment_times[slot] = get_slot_datetime(day, time)

    await query.answer()
    await query.message.reply_text(f"✅ Ты записался на {day_names[day]} {time}!")
    await main_menu(update, context)

async def my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    user_link = user_names.get(user_id, None)
    if not user_link or user_link not in appointments:
        await update.callback_query.message.reply_text("Ты пока не записан на занятия.")
        return

    if user_link not in appointments or not appointments[user_link]:
        await update.callback_query.message.reply_text("У тебя отсутствуют записи.")
        return

    text = "📌 Твои записи:\n" + "\n".join([
        f"- {day_names[slot.split('_')[0]]} {slot.split('_')[1]}"
        for slot in appointments[user_link]
    ])
    await update.callback_query.message.reply_text(text)
    await update.callback_query.message.reply_text(text)
    await main_menu(update, context)

async def view_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.from_user.id != TEACHER_ID:
        await update.callback_query.answer("❌ Нет доступа!", show_alert=True)
        return

    if not appointments:
        await update.callback_query.message.reply_text("Записей пока нет.")
        return

    text = "📜 Все записи:\n"
    for user, slots in appointments.items():
        text += f"\n{user}:\n" + "\n".join(
            [f"  - {day_names[slot.split('_')[0]]} {slot.split('_')[1]}" for slot in slots])

    await update.callback_query.message.reply_text(text)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.from_user.id != TEACHER_ID:
        await update.callback_query.answer("❌ Нет доступа!", show_alert=True)
        return

    appointments.clear()
    appointment_times.clear()
    await update.callback_query.message.reply_text("🔄 Все записи аннулированы!")

def get_slot_datetime(day, time):
    today = datetime.today()
    weekday_map = {"tue": 1, "wed": 2, "thu": 3, "fri": 4}
    slot_datetime = today.replace(hour=int(time.split(":")[0]), minute=0, second=0, microsecond=0)

    while slot_datetime.weekday() != weekday_map[day]:
        slot_datetime += timedelta(days=1)

    return slot_datetime

async def change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    user_link = user_names.get(user_id)

    if not user_link or user_link not in appointments or not appointments[user_link]:
        await update.callback_query.message.reply_text("У тебя пока нет записей.")
        return

    keyboard = [
        [InlineKeyboardButton(f"{day_names[slot.split('_')[0]]} {slot.split('_')[1]}", callback_data=f"change_select_{slot}")]
        for slot in appointments[user_link]
    ]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text("Выбери запись, которую хочешь изменить:", reply_markup=reply_markup)

async def change_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slot = update.callback_query.data.split("_", 2)[2]
    context.user_data["old_slot"] = slot

    keyboard = [[InlineKeyboardButton(day_names[day], callback_data=f"change_day_{day}")] for day in time_slots]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text("Выбери день, на который хочешь перенести запись:", reply_markup=reply_markup)

async def change_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    day = update.callback_query.data.split("_")[2]
    context.user_data["new_day"] = day

    free_slots = [
        time for time in time_slots[day]
        if f"{day}_{time}" not in sum(appointments.values(), [])
    ]

    if not free_slots:
        await update.callback_query.message.reply_text("Нет доступного времени на этот день.")
        return

    keyboard = [[InlineKeyboardButton(time, callback_data=f"change_new_{day}_{time}")] for time in free_slots]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text("Выбери новое время:", reply_markup=reply_markup)

async def change_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_link = user_names[user_id]

    parts = query.data.split("_")
    day = parts[2]
    time = parts[3]

    new_slot = f"{day}_{time}"
    old_slot = context.user_data.get("old_slot")

    if not old_slot or old_slot not in appointments.get(user_link, []):
        await query.message.reply_text("Ошибка: старая запись не найдена.")
        return

    appointments[user_link].remove(old_slot)
    appointments[user_link].append(new_slot)
    appointment_times[new_slot] = get_slot_datetime(day, time)

    updated_text = "✅ Запись изменена!\n\n📌 Твои текущие записи:\n" + "\n".join(
        f"- {day_names[slot.split('_')[0]]} {slot.split('_')[1]}" for slot in appointments[user_link]
    )
    await query.message.reply_text(updated_text)
    await main_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    user_link = user_names.get(user_id)

    if not user_link or user_link not in appointments or not appointments[user_link]:
        await update.callback_query.message.reply_text("У тебя пока нет записей для отмены.")
        return

    keyboard = [
        [InlineKeyboardButton(f"{day_names[slot.split('_')[0]]} {slot.split('_')[1]}", callback_data=f"cancel_select_{slot}")]
        for slot in appointments[user_link]
    ]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text("Выбери запись, которую хочешь отменить:", reply_markup=reply_markup)

async def cancel_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_link = user_names[user_id]
    slot = query.data.split("_", 2)[2]

    slot_time = appointment_times.get(slot)
    now = datetime.now()

    if not slot_time or slot not in appointments.get(user_link, []):
        await query.message.reply_text("Запись не найдена.")
        return

    if slot_time - now < timedelta(hours=12):
        await query.message.reply_text("❌ До занятия осталось меньше 12 часов. Отмена невозможна.")
        return

    appointments[user_link].remove(slot)
    del appointment_times[slot]

    text = f"✅ Запись на {day_names[slot.split('_')[0]]} {slot.split('_')[1]} отменена.\n"

    if appointments[user_link]:
        text += "\n📌 Твои оставшиеся записи:\n" + "\n".join(
            f"- {day_names[s.split('_')[0]]} {s.split('_')[1]}" for s in appointments[user_link]
        )
    else:
        text += "\nУ тебя больше нет записей."

    await query.message.reply_text(text)
    await main_menu(update, context)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", ask_name))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_name))

    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(signup, pattern="^signup$"))
    app.add_handler(CallbackQueryHandler(my_bookings, pattern="^mybookings$"))
    app.add_handler(CallbackQueryHandler(view_appointments, pattern="^view$"))
    app.add_handler(CallbackQueryHandler(reset, pattern="^reset$"))

    app.add_handler(CallbackQueryHandler(select_day, pattern="^day_"))
    app.add_handler(CallbackQueryHandler(select_time, pattern="^time_"))
    app.add_handler(CallbackQueryHandler(change, pattern="^change$"))
    app.add_handler(CallbackQueryHandler(change_select, pattern="^change_select_"))
    app.add_handler(CallbackQueryHandler(change_day, pattern="^change_day_"))
    app.add_handler(CallbackQueryHandler(change_new, pattern="^change_new_"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    app.add_handler(CallbackQueryHandler(cancel_select, pattern="^cancel_select_"))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()