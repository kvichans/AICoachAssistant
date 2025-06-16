import os
import json
from .docs.variables import user_message_1, user_message_2, instructions

from .models import OpenAIThread, TelegramUser, OpenAIAssistant
from .serializers import OpenAIAssistantSerializer, OpenAIThreadSerializer

from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_PATH = os.path.join(BASE_DIR, "docs", "default_instructions.json")


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
            user = TelegramUser.objects.get(chat_id=chat_id)
            client.beta.threads.delete(user.thread.id)
            user.thread.delete()
            return 'Ok'
        except Exception as e:
            raise e


class TelegramUserService:
    '''
    Сервис для работы с моделью TelegramUser через сериализатор.
    '''
    def __init__(self, **kwargs):
        self.chat_id = kwargs.get("chat_id")

    def create_user(self, assistant_id, thread_id, username=None, first_name=None, last_name=None):
        user = TelegramUser.objects.create(
            chat_id=self.chat_id,
            assistant_id=assistant_id,
            thread_id=thread_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        user.save()
        return

    def get_user(self):
        return TelegramUser.objects.get(chat_id=self.chat_id)

    def get_thread_by_user(self):
        try:
            user = TelegramUser.objects.get(pk=self.chat_id)
            thread = user.thread  # здесь – связанный OpenAIThread
            return thread
        except TelegramUser.DoesNotExist:
            return None