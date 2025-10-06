import os
import json
import openai
from collections import defaultdict
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# === Настройки токенов ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# === Папка для долговременной памяти ===
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# === Основные переменные ===
user_roles = defaultdict(lambda: "Ты дружелюбный и умный ассистент, похожий на ChatGPT. Общайся естественно и профессионально.")
user_modes = defaultdict(lambda: "assistant")  # режим общения: assistant / story

# === Функции памяти ===
def load_memory(user_id):
    """Загрузка памяти пользователя из файла"""
    path = os.path.join(DATA_DIR, f"memory_{user_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(user_id, context):
    """Сохранение памяти пользователя"""
    path = os.path.join(DATA_DIR, f"memory_{user_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

# === Роли ===
ROLES = {
    "psychologist": "Ты опытный психолог. Говоришь мягко, с пониманием.",
    "teacher": "Ты терпеливый учитель. Объясняешь просто и с примерами.",
    "fitness_trainer": "Ты энергичный тренер, мотивируешь и вдохновляешь.",
    "marketer": "Ты эксперт в маркетинге и продвижении, говоришь по делу.",
    "developer": "Ты старший разработчик, объясняешь код логично и понятно.",
    "copywriter": "Ты креативный копирайтер, создаёшь тексты, истории и идеи.",
    "doctor": "Ты внимательный врач, объясняешь просто и спокойно.",
    "lawyer": "Ты юрист, даёшь советы грамотно и понятно.",
    "architect": "Ты архитектор, вдохновенно говоришь о дизайне и гармонии.",
    "financial_advisor": "Ты эксперт по финансам, даёшь уверенные советы.",
    "project_manager": "Ты менеджер, структурно объясняешь шаги и цели.",
    "editor": "Ты редактор, помогаешь улучшить тексты.",
    "chef": "Ты шеф-повар, рассказываешь рецепты вкусно и просто.",
    "historian": "Ты историк, объясняешь события живо и с контекстом.",
    "astrologer": "Ты астролог, объясняешь влияние планет спокойно и мягко.",
    "psychiatrist": "Ты психиатр, говоришь профессионально и с сочувствием.",
    "hr": "Ты HR, помогаешь с карьерой и собеседованиями.",
    "art_expert": "Ты искусствовед, рассказываешь о культуре с чувством.",
    "coach": "Ты коуч, вдохновляешь и помогаешь двигаться к целям.",
}

STORY_MODE_PROMPT = """
Ты креативный рассказчик. Вместе с пользователем создаёшь истории.
После каждого шага предлагай 2–3 варианта развития событий или спрашивай, как продолжить.
"""

# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🤖 Я GPT-бот с памятью и голосовым вводом.\n\n"
        "💬 Команды:\n"
        "/role [название] — выбрать профессию (например, /role doctor)\n"
        "/story — начать писать историю\n"
        "/save — сохранить текущий диалог\n"
        "/new — очистить память"
    )

async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text("Укажи роль, например: /role marketer")
        return

    role_name = " ".join(context.args).lower()
    if role_name in ROLES:
        user_roles[user_id] = ROLES[role_name]
        user_modes[user_id] = "assistant"
        await update.message.reply_text(f"Теперь я — {role_name}! 👨‍💼")
    else:
        await update.message.reply_text("Такой роли нет. Доступные:\n" + ", ".join(ROLES.keys()))

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    save_memory(user_id, [])
    await update.message.reply_text("🧹 Память очищена. Начнём заново!")

async def story_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_modes[user_id] = "story"
    await update.message.reply_text("📖 Начнём историю! Расскажи, о чём она будет?")

async def save_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    context_data = load_memory(user_id)
    if not context_data:
        await update.message.reply_text("Пока нечего сохранять 😅")
        return

    filename = f"chat_{user_id}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for msg in context_data:
            role = "Ты" if msg["role"] == "user" else "Бот"
            f.write(f"{role}: {msg['content']}\n\n")

    await update.message.reply_document(InputFile(filename), caption="💾 Вот твой диалог.")
    os.remove(filename)

# === Голосовой ввод ===
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    file = await update.message.voice.get_file()
    file_path = f"voice_{user_id}.ogg"
    await file.download_to_drive(file_path)

    with open(file_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    os.remove(file_path)

    text = transcript.text.strip()
    await update.message.reply_text(f"🎤 Распознано: {text}")
    await handle_message(update, context, text_input=text)

# === Основной обработчик сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text_input=None):
    user_id = update.message.from_user.id
    text = text_input if text_input else update.message.text

    context_data = load_memory(user_id)
    context_data.append({"role": "user", "content": text})
    mode = user_modes[user_id]
    system_prompt = STORY_MODE_PROMPT if mode == "story" else user_roles[user_id]
    messages = [{"role": "system", "content": system_prompt}] + context_data[-10:]

    try:
        await update.message.reply_chat_action("typing")
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=400,
        )
        reply = response.choices[0].message.content.strip()
        context_data.append({"role": "assistant", "content": reply})
        save_memory(user_id, context_data)
        await update.message.reply_text(reply)

    except Exception as e:
        print(e)
        await update.message.reply_text("⚠️ Ошибка при обращении к OpenAI API.")

# === Запуск ===
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("role", set_role))
    app.add_handler(CommandHandler("story", story_mode))
    app.add_handler(CommandHandler("save", save_chat))
    app.add_handler(CommandHandler("new", new_chat))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущен с памятью и голосом!")
    app.run_polling()

if __name__ == "__main__":
    main()
