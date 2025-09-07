from pprint import pprint
import json
import os
from io import BytesIO
from typing import Literal, Tuple

from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment

from pydantic import BaseModel

from .docs.variables import user_message_1, user_message_2, default_instructions
from .models import (User, Chat, Message, RoleChoice, Instruction,
                     ProgressStatus, TypesMessage, PDFFile, Audio)
from .utilits import get_started_files, get_ended_files

load_dotenv()
BASE_URL = os.getenv("BASE_URL")

class AnswerModel(BaseModel):
    answer: str
    status: Literal["in_progress", "next"]

def ogg_bytes_to_mp3_bytes(ogg_bytes: bytes, bitrate: str = "192k"):
    ogg_buffer = BytesIO(ogg_bytes)
    audio = AudioSegment.from_file(ogg_buffer, format="ogg")

    mp3_buffer = BytesIO()
    audio.export(mp3_buffer, format="mp3", bitrate=bitrate)

    mp3_buffer.seek(0)
    mp3_buffer.name = "audio.mp3"
    return mp3_buffer


class UserService:
    '''
    Сервис для работы с моделью User через сериализатор.
    '''
    def __init__(self, user_id):
        self.user_id = user_id

    def create_or_update_user(self, username=None, first_name=None, last_name=None):
        User.objects.update_or_create(
            chat_id=self.user_id,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        return

    def get_user(self):
        instance = User.objects.get(id=self.user_id)
        return instance


class MessageService:
    def __init__(self, chat: Chat):
        self.chat = chat

    def create(self, role: str, exercise, content=None, type_message=None, audio=None, pdf=None) -> Message:
        message = self.chat.messages.create(
            role=role,
            exercise=exercise,
            type=type_message,
            content=content,
            audio=audio,
            pdf=pdf,
        )
        return message

    def get_chat_history(self, exercise):
        return self.chat.messages.filter(exercise=exercise).exclude(role=RoleChoice.INTERNAL).order_by('created_at')

    def get_all_exercise_chat_history(self):
        return self.chat.messages.exclude(role=RoleChoice.INTERNAL).order_by('created_at')


class OpenAIAPIService:

    def __init__(self, token, message_service):
        self.client = OpenAI(api_key=token)
        self.message_service: MessageService = message_service or None

    def _persist_files_and_reply(self, exercise, audio_list, pdf_list) -> list[Message]:
        """Сохраняет файлы как внутренние сообщения и возвращает «пустой» ответ с файловым блоком."""
        audio_list = [a for a in (audio_list or []) if a]
        pdf_list = [p for p in (pdf_list or []) if p]
        messages = []

        for a in audio_list:
            message = self.message_service.create(
                role=RoleChoice.INTERNAL,
                exercise=exercise,
                type_message=TypesMessage.AUDIO,
                audio=a,
            )
            messages.append(message)
        for p in pdf_list:
            message = self.message_service.create(
                role=RoleChoice.INTERNAL,
                exercise=exercise,
                type_message=TypesMessage.PDF,
                pdf=p,
            )
            messages.append(message)
        return messages

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

    def generate(self, content: str, request=None) -> Tuple[list[Message], str]:
        """
        Возвращает ТЕКСТ ответа ассистента и сохраняет его в Message.
        Никогда не возвращает Exception как значение.
        """

        exercise = self.message_service.chat.get_current_exercise()
        if exercise is None:
            pdf_list = PDFFile.objects.filter(is_last=True)
            audio_list = Audio.objects.filter(is_last=True)
            result = self._persist_files_and_reply(exercise, audio_list,
                                                   pdf_list)
            return result, ''
        progress = self.message_service.chat.get_progress(exercise)
        progress_status = progress.status
        branch = {
            ProgressStatus.NOT_STARTED: (
            get_started_files, ProgressStatus.IN_PROGRESS),
            ProgressStatus.ENDED: (get_ended_files, ProgressStatus.DONE),
        }.get(progress_status)

        if branch:
            getter, next_status = branch
            audio_list, pdf_list = getter(request, exercise)

            result = self._persist_files_and_reply(exercise, audio_list,
                                                   pdf_list)

            progress.status = next_status
            progress.save(update_fields=["status"])

            return result, ''

        self.message_service.create(role=RoleChoice.USER, type_message=TypesMessage.TEXT, content=content, exercise=exercise)
        history = self.message_service.get_chat_history(exercise)
        messages = [{"role": m.role, "content": m.content} for m in history]

        instruction = Instruction.objects.filter(is_active=True).first()
        if not instruction:
            instruction = Instruction.objects.create(text=default_instructions, is_active=True)

        if exercise:
            messages.insert(0, {"role": "assistant", "content": f"Давай приступим к технике «{exercise.name}»?"})
            messages.insert(0, {"role": "user", "content": exercise.content})

        messages.insert(0, {
            "role": "developer",
            "content": f'"instruction": {instruction.text}, '
                       f'"name_client": {self.message_service.chat.user.first_name}'
        }
                        )

        pprint([{"role": m["role"], "content": (m["content"][:120] if isinstance(m["content"], str) else m["content"])}
                for m in messages])

        try:
            completion = self.client.beta.chat.completions.parse(
                model="gpt-5",
                messages=messages,
                response_format=AnswerModel
            )
            msg = completion.choices[0].message
            msg_json = json.loads(msg.model_dump().get('content'))

            status = msg_json.get('status')
            message = self.message_service.create(role=RoleChoice.ASSISTANT, type_message=TypesMessage.TEXT, content=msg_json.get('answer') or "[пустой ответ]", exercise=exercise)
            return [message], status

        except Exception as e:
            err_text = f"Ошибка генерации ответа: {e}"
            raise err_text
