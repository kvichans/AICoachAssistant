import os
import sys
import django
import asyncio
from pathlib import Path
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
import openai
import re
from pydub import AudioSegment

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.utils.chat_action import ChatActionMiddleware

# === Django setup ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.append(PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from CoachAsistant.docs.variables import exercise_1, exercise_2, exercise_3, exercise_4, exercise_5
from CoachAsistant.servises import OpenAIAssistantService, OpenAIThreadService, TelegramUserService
from CoachAsistant.models import OpenAIAssistant, TelegramUser

# === Environment ===
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.message.outer_middleware(ChatActionMiddleware())
client = openai.OpenAI()

# Ensure assistant exists
assistant = OpenAIAssistant.objects.first() or OpenAIAssistantService().create_assistant()
VECTOR_STORE_ID = []

# === Helpers ===
def get_default_keyboard():
    buttons = [
        [KeyboardButton(text='/clearall')],
        [KeyboardButton(text='/ограничивающие_убеждения')],
        [KeyboardButton(text='/исследование_жизненных_ценностей')],
        [KeyboardButton(text='/воплощение_ценностей')],
        [KeyboardButton(text='/cкрытые_стратегии')],
        [KeyboardButton(text='/исследование_гениальности')],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def get_or_create_user_service(message):
    return TelegramUserService(chat_id=message.chat.id)

async def get_thread_service(message, exercise=None, exercise_name=None):
    ts = OpenAIThreadService(assistant_id=assistant.id)
    try:
        await sync_to_async(ts.clear_tread)(message.chat.id)
    except:
        pass
    if exercise:
        await sync_to_async(ts.create_thread)(exercise=exercise, exercise_name=exercise_name)
    return ts

async def send_intro_message(message, text):
    await message.reply(text, reply_markup=get_default_keyboard())

async def exercise_handler(message, exercise, description):
    ts = await get_thread_service(message, exercise, description)
    us = await get_or_create_user_service(message)
    await sync_to_async(us.create_or_update_user)(
        assistant_id=ts.assistant_id,
        thread_id=ts.thread_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    await send_intro_message(message,
        f'Здравствуйте! Меня зовут AI Coach, и сегодня мы займёмся {description}. Начнем?\n\nВы можете записывать голосовые сообщения, я тоже отвечу голосом.'
    )

# class MessageProcessor:
#     def __init__(self, assistant):
#         self.assistant = assistant
#
#     async def _get_or_create_thread(self, message):
#         user_svc = TelegramUserService(chat_id=message.chat.id)
#         thread_obj = await sync_to_async(user_svc.get_thread_by_user)()
#         if thread_obj:
#             ts = OpenAIThreadService(thread_id=thread_obj.id, assistant_id=self.assistant.id)
#         else:
#             ts = OpenAIThreadService(assistant_id=self.assistant.id)
#             await sync_to_async(ts.create_thread)(VECTOR_STORE_ID)
#             await sync_to_async(user_svc.create_or_update_user)(
#                 assistant_id=ts.assistant_id,
#                 thread_id=ts.thread_id,
#                 username=message.from_user.username,
#                 first_name=message.from_user.first_name,
#                 last_name=message.from_user.last_name
#             )
#         return ts
#
#     async def process(self, message, user_text: str) -> str:
#         """Общая логика обработки текста."""
#         ts = await self._get_or_create_thread(message)
#         await sync_to_async(ts.add_message_tread)(user_text)
#         run = await sync_to_async(ts.run_tread)()
#         if run.status != 'completed':
#             return f'Статус запроса: {run.status}'
#         msgs = await sync_to_async(client.beta.threads.messages.list)(thread_id=ts.thread_id)
#         return re.sub(r'【\d+:\d+†[^】]+】', '', msgs.data[0].content[0].text.value)

# === Command handlers ===
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    exists = await sync_to_async(TelegramUser.objects.filter(chat_id=message.chat.id).exists)()
    if exists:
        await message.reply('Продолжим?', reply_markup=get_default_keyboard())
    else:
        await send_intro_message(message, 'Здравствуйте! Меня зовут AI Coach, займёмся исследованием ваших жизненных ценностей?')

@dp.message(Command('clearall'))
async def clear_all_handler(message: types.Message):
    # reset thread without new exercise
    await get_thread_service(message)
    await send_intro_message(message, 'Начнем заново исследование ваших ценностей?')

@dp.message(Command('исследование_жизненных_ценностей'))
async def values_handler(message: types.Message):
    await exercise_handler(message, exercise_1, 'исследованием ваших жизненных ценностей')

@dp.message(Command('ограничивающие_убеждения'))
async def beliefs_handler(message: types.Message):
    await exercise_handler(message, exercise_2, 'вашими ограничивающими убеждениями')

@dp.message(Command('воплощение_ценностей'))
async def beliefs_handler(message: types.Message):
    await exercise_handler(message, exercise_3, 'воплощениями ваших ценностей')

@dp.message(Command('cкрытые_стратегии'))
async def beliefs_handler(message: types.Message):
    await exercise_handler(message, exercise_4, 'вашими скрытыми стратегиями')

@dp.message(Command('исследование_гениальности'))
async def beliefs_handler(message: types.Message):
    await exercise_handler(message, exercise_5, 'исследованием вашей уникальной гениальности')

# === Voice handler ===
@dp.message(F.voice)
async def voice_handler(message: types.Message):
    # prepare files directory
    Path('files').mkdir(exist_ok=True)
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    ogg_path = Path('files') / f'{file_id}.ogg'
    await bot.download_file(file.file_path, ogg_path)

    # ogg -> mp3 for transcription
    mp3_path = ogg_path.with_suffix('.mp3')
    AudioSegment.from_file(ogg_path, format='ogg').export(mp3_path, format='mp3', bitrate='192k')

    # transcribe
    with open(mp3_path, 'rb') as f:
        transcription = client.audio.transcriptions.create(
            model='gpt-4o-mini-transcribe', file=f
        )
    user_text = transcription.text
    await bot.send_chat_action(message.from_user.id, 'record_voice')

    # process thread
    us = await get_or_create_user_service(message)
    thread_obj = await sync_to_async(us.get_thread_by_user)()
    if thread_obj:
        ts = OpenAIThreadService(thread_id=thread_obj.id, assistant_id=assistant.id)
    else:
        ts = OpenAIThreadService(assistant_id=assistant.id)
        await sync_to_async(ts.create_thread)(VECTOR_STORE_ID)
        await sync_to_async(us.create_or_update_user)(
            assistant_id=ts.assistant_id,
            thread_id=ts.thread_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    await sync_to_async(ts.add_message_tread)(user_text)

    run = await sync_to_async(ts.run_tread)()
    if run.status == 'completed':
        msgs = await sync_to_async(client.beta.threads.messages.list)(thread_id=ts.thread_id)
        answer = re.sub(r'【\d+:\d+†[^】]+】', '', msgs.data[0].content[0].text.value)
        # generate tts
        tts_path = Path('files') / f'tts_{file_id}.mp3'
        with client.audio.speech.with_streaming_response.create(
            model='gpt-4o-mini-tts', voice='alloy', input=answer,
            instructions='Accent: neutral Russian...'  # truncated
        ) as resp:
            resp.stream_to_file(tts_path)
        # send
        await bot.send_chat_action(message.from_user.id, 'record_voice')
        await message.answer_voice(FSInputFile(tts_path))
        # cleanup
        for p in (ogg_path, mp3_path, tts_path):
            try: p.unlink()
            except: pass
    else:
        await message.answer(f'Статус запроса: {run.status}')

# === Text handler ===
@dp.message()
async def handle_message(message: types.Message):
    await bot.send_chat_action(message.from_user.id, 'typing')
    user_text = message.text
    us = await get_or_create_user_service(message)
    thread_obj = await sync_to_async(us.get_thread_by_user)()
    if thread_obj:
        ts = OpenAIThreadService(thread_id=thread_obj.id, assistant_id=assistant.id)
    else:
        ts = OpenAIThreadService(assistant_id=assistant.id)
        await sync_to_async(ts.create_thread)(VECTOR_STORE_ID)
        await sync_to_async(us.create_or_update_user)(
            assistant_id=ts.assistant_id,
            thread_id=ts.thread_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    await sync_to_async(ts.add_message_tread)(user_text)
    run = await sync_to_async(ts.run_tread)()
    if run.status == 'completed':
        msgs = await sync_to_async(client.beta.threads.messages.list)(thread_id=ts.thread_id)
        answer = re.sub(r'【\d+:\d+†[^】]+】', '', msgs.data[0].content[0].text.value)
        await bot.send_message(
            chat_id=message.chat.id,
            text=answer,
            parse_mode='Markdown',
            reply_markup=get_default_keyboard()
        )
    else:
        await message.answer(f'Статус запроса: {run.status}')

# === Main ===
async def main():
    print('Бот запущен...')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
