import os

import requests
import asyncio

from io import BytesIO
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.chat_action import ChatActionMiddleware
from aiogram.filters import CommandStart, Command
from aiogram.types import BufferedInputFile, KeyboardButton, ReplyKeyboardMarkup


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = os.getenv('BASE_URL')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.message.outer_middleware(ChatActionMiddleware())

def get_default_keyboard():
    try:
        resp=requests.get(f'{BASE_URL}/exercises/')
        resp = resp.json()
        buttons = [[KeyboardButton(text=f'/{i.get("name")}')] for i in resp]
        buttons.append([KeyboardButton(text='/clearall')])
        return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    except Exception as e:
        raise e

def get_commands():
    try:
        resp = requests.get(f'{BASE_URL}/exercises/')
        resp = resp.json()
        exercises = [i.get('name') for i in resp]
        if not resp:
            exercises=['None']
        return exercises
    except Exception as e:
        raise e


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    try:
        resp = requests.get(f'{BASE_URL}/users/{message.chat.id}/')
        if resp.status_code == 200 and resp.json().get('chat') != []:
            await message.reply('Продолжим?')
        else:
            await message.reply(
                'Здравствуйте! Меня зовут AI Coach, и сегодня мы вместе займёмся исследованием ваших жизненных ценностей. Это важный и интересный процесс, который поможет вам лучше понять, что для вас действительно ценно и значимо. Начнем?\n\nЧтобы было удобнее вы можете записывать голосовые сообщения, я тоже буду отвечать голосом.',
            reply_markup=get_default_keyboard())
    except Exception as e:
        await message.reply(f'Произошла какая-то ошибка: {e}', reply_markup=get_default_keyboard())


@dp.message(F.text, Command('clearall'))
async def my_handler(message: types.Message):
    try:
        resp = requests.get(f'{BASE_URL}/users/{message.chat.id}/')
        if resp.status_code != 200:
            await message.reply(
                f'Мы не можем начать заново, потому что не были знакомы...  Меня зовут AI Coach, займёмся исследованием ваших жизненных ценностей?\n\nЧтобы было удобнее, вы можете записывать голосовые сообщения.',
            reply_markup=get_default_keyboard())
        else:
            chat = resp.json().get('chat')
            if chat:
                chat_id = chat[0].get('id')
                resp=requests.delete(f'{BASE_URL}/chats/{chat_id}/')
                await message.reply('Здравствуйте! Меня зовут AI Coach, и сегодня мы вместе займёмся исследованием ваших жизненных ценностей. Это важный и интересный процесс, который поможет вам лучше понять, что для вас действительно ценно и значимо. Начнем?\n\nЧтобы было удобнее вы можете записывать голосовые сообщения, я тоже буду отвечать голосом.',
                                    reply_markup=get_default_keyboard())
    except Exception as e:
        await message.reply(f'Произошла ошибка при удалении: {e}')

@dp.message(F.text, Command(commands=get_commands()))
async def exercises_handler(message: types.Message):
    try:
        resp = requests.get(f'{BASE_URL}/users/{message.chat.id}/')
        chat = resp.json().get('chat')

        if chat:
            chat_id = chat[0].get('id')
            requests.delete(f'{BASE_URL}/chats/{chat_id}/')

        exercise = message.text.lstrip("/")
        payload = {
            'user': message.chat.id,
            'exercise': exercise
        }
        requests.post(f'{BASE_URL}/chats/', data=payload)
        await bot.send_message(message.from_user.id, f'Давай приступим к технике {exercise}?')
    except Exception as e:
        await bot.send_message(message.from_user.id, f'ошибка при выборе техники {e}')



@dp.message(F.text)
async def handle_message(message: types.Message):
    await bot.send_chat_action(message.from_user.id, 'typing')
    try:
        payload = {
            "chat_id": message.chat.id,
            "text": f"{message.text}"
        }
        generation = requests.post(f'{BASE_URL}/generate-text/', data=payload)
        await bot.send_message(message.from_user.id, generation.json().get('data'))
    except Exception as e:
        await bot.send_message(message.from_user.id, f'Ошибка при генерации сообщения: {e}')

@dp.message(F.voice)
async def voice_handler(message: types.Message):
    try:
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        my_object = BytesIO()
        await bot.download_file(file.file_path, my_object)
        my_object.seek(0)
        payload = {
            'user_id': message.chat.id
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

# === Main ===
async def main():
    print('Бот запущен...')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
