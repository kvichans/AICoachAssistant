import io
import os
import pprint

import requests
import asyncio

from io import BytesIO
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.chat_action import ChatActionMiddleware
from aiogram.filters import CommandStart, Command
from aiogram.types import (BufferedInputFile,
                           InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery
                           )


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = os.getenv('BASE_URL')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.message.outer_middleware(ChatActionMiddleware())

def get_chat_id(telegram_chat_id):
    chat = requests.get(f'{BASE_URL}/chats/{telegram_chat_id}/')
    return chat.json()['id']

def get_user_id(telegram_chat_id):
    user = requests.get(f'{BASE_URL}/users/{telegram_chat_id}/')
    return user.json()['id']

async def send_audio(url: str, chat_id):
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()

    bio = io.BytesIO()
    for chunk in r.iter_content(8192):
        if chunk:
            bio.write(chunk)
    bio.name = "audio.mp3"
    bio.seek(0)

    buffered = BufferedInputFile(bio.getvalue(), filename="voice.mp3")
    await bot.send_voice(chat_id, buffered)

async def send_generated_messages(chat_id, text):
    payload = {
        "user_id": get_user_id(chat_id),
        "text": f"{text}"
    }
    generation = requests.post(f'{BASE_URL}/generate-text/', data=payload)
    generation_json = generation.json().get('data')
    status = generation_json.get('status')
    messages = generation_json.get('messages')
    for message in messages:
        if message.get('type') == 'text':
            await bot.send_message(chat_id, message.get('text'))
        if message.get('type') == 'audio':
            await send_audio(message.get('files').get('audio'), chat_id)
        if message.get('type') == 'pdf':
            await bot.send_document(chat_id, message.get('files').get('pdf'))

    if status == 'next':
        await bot.send_message(chat_id,
                               'Игнорируйте это сообщение, если вы не закончили',
                               reply_markup=InlineKeyboardMarkup(
                                   inline_keyboard=[
                                       [
                                           InlineKeyboardButton(
                                               text='Перейти к следующему',
                                               callback_data='/next'
                                           )
                                       ]
                                   ]
                               )
                               )

async def start_chat(message: types.Message):
    try:
        chat = requests.get(f'{BASE_URL}/users/{message.from_user.id}/chat')
        if chat.status_code == 200:
            await bot.send_message(message.from_user.id, 'Продолжим?')
        else:
            user = requests.get(f'{BASE_URL}/users/{message.from_user.id}')
            if user.status_code != 200:
                payload = {
                    "telegram_id": message.from_user.id,
                    "username": message.from_user.username or None,
                    "first_name": message.from_user.first_name or None,
                    "last_name": message.from_user.last_name or None,
                }
                user = requests.post(f'{BASE_URL}/users/', json=payload)
            audio = requests.get(f'{BASE_URL}/audio/')
            for audio in audio.json():
                if audio.get('is_first'):
                    await send_audio(audio.get('file'), message.from_user.id)
                elif audio.get('is_second'):
                    if user.json().get('sex') == 'female' and audio.get('sex') == 'female':
                        await send_audio(audio.get('file'), message.from_user.id)
                    elif user.json().get('sex') == 'male' and audio.get('sex') == 'male':
                        await send_audio(audio.get('file'), message.from_user.id)
            await bot.send_message(message.from_user.id,
                                   'Нажмите "Далее" после прослушивания голосовых сообщений',
                                   reply_markup=InlineKeyboardMarkup(
                                       inline_keyboard=[
                                           [
                                               InlineKeyboardButton(
                                                   text='Далее',
                                                   callback_data='/next'
                                               )
                                           ]
                                       ]
                                   )
                                   )

    except Exception as e:
        await bot.send_message(message.from_user.id, f'Произошла какая-то ошибка: {e}')
        raise e


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await start_chat(message)

@dp.callback_query(F.data == '/start')
async def cb_start(message: types.CallbackQuery):
    await start_chat(message)

@dp.callback_query(F.data == "/next")
async def cmd_next(callback: CallbackQuery):
    resp = requests.get(f"{BASE_URL}/users/{callback.from_user.id}/chat/")
    data = resp.json()
    progress = data.get("progress", []) or []

    if not progress or all(p.get("status") == "done" for p in progress):
        await send_generated_messages(callback.from_user.id, callback.data)
        await bot.send_message(callback.from_user.id,
                         'Готовы начинать? Можно писать текстом или отправлять голосовые сообщения.'
                         )
        return

    in_progress = [p for p in progress if p.get("status") == "in_progress"]

    if in_progress:
        payload = {"status": "ended"}
        for p in in_progress:
            requests.patch(f"{BASE_URL}/progress/{p['id']}/", json=payload)
        await send_generated_messages(callback.from_user.id, callback.data)
        return


@dp.message(F.text.startswith('/'))
async def my_handler(message: types.Message):

    if message.text == '/clearall':
        try:
            chat = requests.get(f'{BASE_URL}/users/{message.chat.id}/chat')
            if chat.status_code != 200:
                await message.reply(
                    f'Мы не можем начать заново, потому что не были знакомы...  Меня зовут AI Coach, займёмся исследованием ваших жизненных ценностей?\n\nЧтобы было удобнее, вы можете записывать голосовые сообщения.',
                )
            else:
                requests.delete(f'{BASE_URL}/chats/{chat.json().get("id")}/')
                await bot.send_message(message.from_user.id,
                                       'Чат удален. Начнем?',
                                       reply_markup=InlineKeyboardMarkup(
                                           inline_keyboard=[
                                               [
                                                   InlineKeyboardButton(
                                                       text='Да, приступим!',
                                                       callback_data='/start'
                                                   )
                                               ]
                                           ]
                                       )
                                       )
        except Exception as e:
            await message.reply(
                f'Произошла ошибка при удалении: {e}'
            )


@dp.message(F.text)
async def handle_message(message: types.Message):
    await bot.send_chat_action(message.from_user.id, 'typing')
    try:
        payload = {
            "user_id": get_user_id(message.chat.id),
            "text": f"{message.text}"
        }
        generation = requests.post(f'{BASE_URL}/generate-text/', data=payload)
        generation_json = generation.json()
        if generation_json.get('status') == 'next':
            await bot.send_message(
                message.from_user.id,
                generation_json.get('data').get('messages')[0].get('text')
            )
            await bot.send_message(message.from_user.id,
                                   'Игнорируйте это сообщение, если вы не закончили',
                                   reply_markup=InlineKeyboardMarkup(
                                       inline_keyboard=[
                                           [
                                               InlineKeyboardButton(
                                                   text='Перейти к следующему',
                                                   callback_data='/next'
                                               )
                                           ]
                                       ]
                                   )
                                   )
        else:
            await bot.send_message(message.from_user.id, generation_json.get('data').get('messages')[0].get('text'))
    except Exception as e:
        await bot.send_message(message.from_user.id, f'Ошибка при генерации сообщения: {e}')
        raise e

@dp.message(F.voice)
async def voice_handler(message: types.Message):
    try:
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        my_object = BytesIO()
        await bot.download_file(file.file_path, my_object)
        my_object.seek(0)
        payload = {
            'user_id': get_user_id(message.chat.id)
        }

        files = {'file': ('voice.ogg', my_object, 'audio/ogg')}
        resp = requests.post(f'{BASE_URL}/generate-audio/',data=payload, files=files)

        result_bytes = BytesIO(resp.content)
        result_bytes.name = 'result.mp3'
        result_bytes.seek(0)

        buffered = BufferedInputFile(result_bytes.getvalue(), filename="voice.mp3")

        await message.answer_voice(buffered)
    except Exception as e:
        await bot.send_message(message.from_user.id, f'Ошибка при генерации аудио: {e}')

async def main():
    print('Бот запущен...')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
