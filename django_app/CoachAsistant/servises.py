import os
import json
from pprint import pprint
from io import BytesIO

from openai.types.chat import ChatCompletionMessage

from .docs.variables import user_message_1, user_message_2, instructions, user_message_3
from django.shortcuts import get_object_or_404

from .models import OpenAIThread, User, OpenAIAssistant, Chat, Message, Exercise, RoleChoice
from .serializers import OpenAIAssistantSerializer, OpenAIThreadSerializer, MessageSerializer

from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_PATH = os.path.join(BASE_DIR, "docs", "default_instructions.json")

def ogg_bytes_to_mp3_bytes(ogg_bytes: bytes, bitrate: str = "192k"):
    # 1) Загружаем OGG из памяти
    ogg_buffer = BytesIO(ogg_bytes)
    audio = AudioSegment.from_file(ogg_buffer, format="ogg")

    # 2) Конвертируем в MP3 в другой буфер
    mp3_buffer = BytesIO()
    audio.export(mp3_buffer, format="mp3", bitrate=bitrate)

    # 3) Сбрасываем курсор и возвращаем байты
    mp3_buffer.seek(0)
    mp3_buffer.name = "audio.mp3"
    return mp3_buffer

class OpenAIAPIService:

    def __init__(self, token):
        self.client = OpenAI(api_key=token)

    def speach_to_text(self, speech: BytesIO):
        speech.seek(0)
        transcript = self.client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=speech
        )
        return transcript.text

    def text_to_speach(self, text_for_speach):
        bio = BytesIO()
        with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=text_for_speach,
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
            for chunk in response.iter_bytes(chunk_size=32 * 1024):
                bio.write(chunk)

        bio.name = 'response.mp3'
        bio.seek(0)
        return bio


class OpenAIAssistantService:
    def create_assistant(self):

        api_response = client.beta.assistants.create(
            instructions=instructions,
            name="CoachAssistant",
            model="gpt-4o-mini",
            top_p=0.9,
            temperature=0.7
        )

        serializer = OpenAIAssistantSerializer(data=api_response.dict())
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

class OpenAIThreadService:
    def __init__(self, assistant_id=None, thread_id=None):
        self.assistant_id = assistant_id
        self.thread_id = thread_id

    def create_thread(self, message_text: str, vector_store_id: list):
        api_response = client.beta.threads.create(
            messages=[
                {"role": "assistant", "content": 'Какими характеристиками должен обладать ChatGPT?'},
                {"role": "user", "content": user_message_1},
                {"role": "assistant", "content": 'Что-нибудь еще, что ChatGPT должен знать о вас?'},
                {"role": "user", "content": user_message_2},
                {"role": "assistant", "content": 'Я отлично, отправьте мне первую интрукцию'},
                {"role": "user", "content": user_message_3},
                {"role": "assistant", "content": 'Здравствуйте! Меня зовут AI Coach, и сегодня мы вместе займёмся исследованием ваших жизненных ценностей. Это важный и интересный процесс, который поможет вам лучше понять, что для вас действительно ценно и значимо. Начнем?\n\nЧтобы было удобнее вы можете записывать голосовые сообщения, я тоже буду отвечать голосом.'},
                {"role": "user", "content": message_text}
            ]
        )
        serializer = OpenAIThreadSerializer(data=api_response.dict())
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        self.thread_id = instance.id
        return instance


    def  add_message_tread(self, user_text: str):
        return client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=user_text
            )

    def run_tread(self):
        return client.beta.threads.runs.create_and_poll(
        thread_id=self.thread_id,
        assistant_id=self.assistant_id
    )

    def clear_tread(self, chat_id):
        try:
            user = User.objects.get(chat_id=chat_id)
            client.beta.threads.delete(user.thread.id)
            user.thread.delete()
            return 'Ok'
        except Exception as e:
            raise e


class UserService:
    '''
    Сервис для работы с моделью TelegramUser через сериализатор.
    '''
    def __init__(self, chat_id):
        self.chat_id = chat_id

    def create_or_update_user(self, assistant_id=None, thread_id=None, username=None, first_name=None, last_name=None):
        user, created = User.objects.update_or_create(
            chat_id=self.chat_id,
            defaults={
                'assistant_id': assistant_id,
                'thread_id': thread_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        return

    def get_user(self):
        instance, _ = User.objects.get_or_create(chat_id=self.chat_id)
        return instance

    def get_thread_by_user(self):
        try:
            user = User.objects.get(pk=self.chat_id)
            thread = user.thread  # здесь – связанный OpenAIThread
            return thread
        except User.DoesNotExist:
            return None

class ChatService:

    def __init__(self, user_id, chat_id = None, message=None):
        self.user_id = user_id

    def create_chat(self):
        return Chat.objects.update_or_create(chat_id=self.user_id)

    def get_chat(self):
        return Chat.objects.update_or_create(chat_id=self.user_id)

    def delete_chat(self):
        Chat.objects.filter(chat_id=self.user_id).delete()

class MessageService:
    def __init__(self, chat: Chat):
        self.chat = chat

    def create(self, role: str, content: str) -> Message:
        """
        Создать новое сообщение.
        """
        message = self.chat.messages.create(
            role=role,
            content=content
        )
        message.save()
        return message

    def get_chat_history(self):
        return self.chat.messages.order_by('created_at')

class TextGenerationService:
    """
    Сервис для генерации текста через OpenAI.
    """
    @staticmethod
    def generate(message_service: MessageService, content) -> str:
        message_service.create(RoleChoice.USER, content)
        message_history = message_service.get_chat_history()
        messages = [{"role": message.role, "content": message.content} for message in message_history]

        exercise = message_service.chat.exercise
        if exercise:
            ex = Exercise.objects.filter(name=exercise).first()
            messages.insert(0, {"role": 'assistant', "content": f"Давай приступим к технике {ex.name}?"})
            messages.insert(0, {"role": 'user', "content": ex.content})

        messages.insert(0, {"role": 'user', "content": user_message_2})
        messages.insert(0, {"role": 'user', "content": user_message_1})
        messages.insert(0, {"role": 'developer', "content": instructions})

        pprint(messages)
        try:
            completion = client.chat.completions.create(
                model = "gpt-4o-mini",
                messages = messages
            )
            answer = completion.choices[0].message.content
            message_service.create(RoleChoice.ASSISTANT, answer)
            return answer
        except Exception as e:
            return e


class AudioGenerationService:
    """
    Сервис для генерации аудио из текста через OpenAI TTS.
    """
    @staticmethod
    def generate(user_id: int, text: str) -> str:
        pass
