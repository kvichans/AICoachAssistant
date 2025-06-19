import os
import sys
import django
from pathlib import Path
from time import sleep

from aiogram.enums import ChatAction
from aiogram.types import FSInputFile

# 1) Добавляем в PYTHONPATH корень проекта (/home/Dev/AICoachAssistant),
#    чтобы Python нашёл пакет AICoachAssistant и приложение CoachAsistant.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# BASE_DIR стал /home/Dev/AICoachAssistant/django_app/CoachAsistant -> dirname -> /home/Dev/AICoachAssistant/django_app
PROJECT_ROOT = os.path.dirname(BASE_DIR)
# PROJECT_ROOT -> /home/Dev/AICoachAssistant
sys.path.append(PROJECT_ROOT)

# 2) Устанавливаем настройку DJANGO_SETTINGS_MODULE в 'config.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 3) Инициализируем Django
django.setup()

# Только после django.setup() можно импортировать модели и сервисы
from CoachAsistant.servises import (
    OpenAIAssistantService,
    OpenAIThreadService,
    TelegramUserService,
)
from CoachAsistant.models import OpenAIAssistant, TelegramUser

import asyncio
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
import openai
from aiogram import Bot, Dispatcher, types, F, flags
from aiogram.filters import CommandStart, Command
from aiogram import Router
import re
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.chat_action import ChatActionMiddleware

from pydub import AudioSegment

# Дальше идёт вся логика вашего бота
load_dotenv()
ASSISTANT_ID = os.getenv('ASSISTANT_ID')
VECTOR_STORE_ID = []
BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

client = openai.OpenAI()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

assistant = OpenAIAssistant.objects.first()
if not assistant:
    assistant = OpenAIAssistantService().create_assistant()

def register_middlewares(dp: Dispatcher) -> None:
    dp.message.outer_middleware(ChatActionMiddleware())

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    try:
        await sync_to_async(TelegramUser.objects.get)(chat_id=message.chat.id)
        await message.reply('Продолжим?')
    except:
        await message.reply('Здравствуйте! Меня зовут AI Coach, и сегодня мы вместе займёмся исследованием ваших жизненных ценностей. Это важный и интересный процесс, который поможет вам лучше понять, что для вас действительно ценно и значимо. Начнем?\n\nЧтобы было удобнее вы можете записывать голосовые сообщения, я тоже буду отвечать голосом.')


@dp.message(F.text, Command('clearall'))
async def my_handler(message: types.Message):
    try:
        thread = OpenAIThreadService()
        await sync_to_async(thread.clear_tread)(message.chat.id)
        await message.reply('Здравствуйте! Меня зовут AI Coach, и сегодня мы вместе займёмся исследованием ваших жизненных ценностей. Это важный и интересный процесс, который поможет вам лучше понять, что для вас действительно ценно и значимо. Начнем?\n\nЧтобы было удобнее вы можете записывать голосовые сообщения, я тоже буду отвечать голосом.')
    except Exception as e:
        await message.reply(f'Мы не можем начать заново, потому что не были знакомы...  Меня зовут AI Coach, займёмся исследованием ваших жизненных ценностей?\n\nЧтобы было удобнее, вы можете записывать голосовые сообщения.')



@dp.message(F.voice)
async def voice_handler(message: types.Message):
    Path("files").mkdir(parents=True, exist_ok=True)
    file_id = message.voice.file_id

    # 1. Скачать оригинальный .ogg
    file = await bot.get_file(file_id)

    ogg_path = Path(__file__).parent / f"files/{file_id}.mp3"
    await bot.download_file(file.file_path, ogg_path)

    # 2. Конвертировать .ogg → .mp3 (для распознавания)
    mp3_path = ogg_path.with_suffix(".mp3")
    AudioSegment.from_file(ogg_path, format="ogg") \
                .export(mp3_path, format="mp3", bitrate="192k")

    # 3. Распознавание речи (GPT-4o-mini-transcribe)
    with open(mp3_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file
        )
    text = transcription.text
    await bot.send_chat_action(message.from_user.id, 'record_voice')
    user_text = text
    try:
        # Синхронный вызов get_thread_by_user оборачиваем
        user_service = TelegramUserService(chat_id=message.chat.id)
        thread_obj = await sync_to_async(user_service.get_thread_by_user)()
        thread_id = thread_obj.id if thread_obj else None
        username = message.from_user.username or None
        first_name = message.from_user.first_name or None
        last_name = message.from_user.last_name or None

        if thread_id:
            thread_service = OpenAIThreadService(
                thread_id=thread_id,
                assistant_id=assistant.id
            )
            # Синхронный вызов add_message_tread оборачиваем
            await sync_to_async(thread_service.add_message_tread)(user_text)
        else:
            thread_service = OpenAIThreadService(assistant_id=assistant.id)
            await sync_to_async(thread_service.create_thread)(user_text, VECTOR_STORE_ID)
            # Синхронный вызов create_thread оборачиваем
            await sync_to_async(user_service.create_or_update_user)(assistant_id=thread_service.assistant_id,
                                                                    thread_id=thread_service.thread_id, username=username,
                                                                    first_name=first_name, last_name=last_name)

        # Синхронный вызов run_tread оборачиваем
        run = await sync_to_async(thread_service.run_tread)()
        await bot.send_chat_action(message.from_user.id, 'record_voice')
        if run.status == 'completed':
            # Синхронный вызов OpenAI API оборачиваем
            messages_resp = await sync_to_async(
                client.beta.threads.messages.list
            )(thread_id=thread_service.thread_id)

            answer = messages_resp.data[0].content[0].text.value
            clear_answer = re.sub(r'【\d+:\d+†[^】]+】', '', answer)


            # 4. Генерация TTS (GPT-4o-mini-tts) в .mp3
            await bot.send_chat_action(message.from_user.id, 'record_voice')
            tts_mp3_path = Path(__file__).parent / f"files/transcription_{file_id}.mp3"
            with client.audio.speech.with_streaming_response.create(
                    model="gpt-4o-mini-tts",
                    voice="alloy",
                    input=clear_answer,
                    instructions="""
                    Accent: neutral Russian, without pronounced regional characteristics
                    Emotional range: warm, empathetic, supportive
                    Intonation:
                      – question_end: slight rise in intonation
                      – statement: steady, calm
                    Impressions: confident coach-mentor, gentle inspirer
                    Speed of speech: very fast
                    Tone: calm, friendly, trust-building
                    Whispering: subtle, quiet inflections on emphatic phrases
                    """,
            ) as response:
                response.stream_to_file(tts_mp3_path)

            # 5. Отправка результата пользователю
            await bot.send_chat_action(message.from_user.id, 'record_voice')
            voice_file = FSInputFile(tts_mp3_path)
            await message.answer_voice(voice_file)

            # 6. Удаляем все временные файлы
            try:
                ogg_path.unlink()            # удалит files/{file_id}.ogg
            except FileNotFoundError:
                pass

            try:
                mp3_path.unlink()            # удалит files/{file_id}.mp3
            except FileNotFoundError:
                pass

            try:
                tts_mp3_path.unlink()        # удалит files/transcription_{file_id}.mp3
            except FileNotFoundError:
                pass
        else:
            await message.answer(f'Статус запроса: {run.status}')

    except Exception as e:
        error_text = f'Произошла ошибка при обработке запроса: {e}'
        await message.answer(error_text)

@dp.message()
async def handle_message(message: types.Message):
    await bot.send_chat_action(message.from_user.id, 'typing')
    user_text = message.text
    username = message.from_user.username or None
    first_name = message.from_user.first_name or None
    last_name = message.from_user.last_name or None
    try:
        # Синхронный вызов get_thread_by_user оборачиваем
        user_service = TelegramUserService(chat_id=message.chat.id)
        thread_obj = await sync_to_async(user_service.get_thread_by_user)()
        thread_id = thread_obj.id if thread_obj else None


        if thread_id:
            thread_service = OpenAIThreadService(
                thread_id=thread_id,
                assistant_id=assistant.id
            )
            # Синхронный вызов add_message_tread оборачиваем
            await sync_to_async(thread_service.add_message_tread)(user_text)
        else:
            thread_service = OpenAIThreadService(assistant_id=assistant.id)
            await sync_to_async(thread_service.create_thread)(user_text, VECTOR_STORE_ID)
            # Синхронный вызов create_thread оборачиваем
            await sync_to_async(user_service.create_or_update_user)(assistant_id=thread_service.assistant_id,
                                                                    thread_id=thread_service.thread_id, username=username,
                                                                    first_name=first_name, last_name=last_name)

        # Синхронный вызов run_tread оборачиваем
        run = await sync_to_async(thread_service.run_tread)()


        if run.status == 'completed':
            # Синхронный вызов OpenAI API оборачиваем
            messages_resp = await sync_to_async(
                client.beta.threads.messages.list
            )(thread_id=thread_service.thread_id)

            answer = messages_resp.data[0].content[0].text.value
            clear_answer = re.sub(r'【\d+:\d+†[^】]+】', '', answer)

            button_hi = [[KeyboardButton(text='/clearall')]]
            greet_kb1 = ReplyKeyboardMarkup(
                keyboard=button_hi,
                resize_keyboard=True
            )

            await bot.send_message(
                chat_id=message.chat.id,
                text=clear_answer,
                parse_mode='Markdown',
                reply_markup=greet_kb1,
            )
        else:
            await message.answer(f'Статус запроса: {run.status}')

    except Exception as e:
        error_text = f'Произошла ошибка при обработке запроса: {e}'
        await message.answer(error_text)


async def main():
    print('Бот запущен...')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
