import os
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.decorators import action
from dotenv import load_dotenv
from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import FileResponse, Http404


from .models import User, Chat, Exercise, Audio, PDFFile, ChatProgress
from .serializers import (UserSerializer, GenerateTextSerializer,
                          GenerateAudioSerializer, ChatSerializer,
                          ExerciseSerializer, ResponseGenerateSerializer,
                          PDFSerializer, AudioSerializer, ProgressSerializer)
from .servises import OpenAIAPIService, MessageService, UserService, ogg_bytes_to_mp3_bytes
from .utilits import safe_url

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


class ChatProgressViewSet(mixins.ListModelMixin,
                          mixins.UpdateModelMixin,
                          viewsets.GenericViewSet):
    queryset = ChatProgress.objects.all()
    serializer_class = ProgressSerializer
class AudioViewSet(mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Audio.objects.all()
    serializer_class = AudioSerializer

class PDFViewSet(mixins.ListModelMixin,
    viewsets.GenericViewSet):
    queryset = PDFFile.objects.all()
    serializer_class = PDFSerializer

class UserViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """
    Создание, получение и удаление пользователей по chat_id.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'telegram_id'
    lookup_value_regex = r'\d+'

    @action(detail=True, methods=["get"])
    def chat(self, request, telegram_id=None):
        """
        Получить чат, привязанный к юзеру.
        GET /users/{telegram_id}/chat/
        """
        user = self.get_object()
        chat = Chat.objects.filter(user=user).first()
        if not chat:
            return Response({"detail": "Чат не найден"}, status=404)
        return Response(ChatSerializer(chat).data)


class ChatViewSet(
    mixins.DestroyModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer

class ExerciseViewSet(mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    """
    ViewSet для просмотра списка упражнений и деталей.
    Только методы list и retrieve.
    """
    queryset = Exercise.objects.all().order_by('order')
    serializer_class = ExerciseSerializer
class GenerateTextView(APIView):
    """
    POST /api/generate-text/
    Принимает JSON {chat_id, text} и возвращает {chat_id, generated_text}.
    """

    @swagger_auto_schema(
        request_body=GenerateTextSerializer,
        responses={
            200: openapi.Response(
                description="Сгенерированный текст",
                schema=ResponseGenerateSerializer
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = GenerateTextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_service = UserService(serializer.validated_data['user_id'])
        user = user_service.get_user()

        chat, _ = Chat.objects.get_or_create(user=user)

        open_ai_service = OpenAIAPIService(OPENAI_API_KEY, MessageService(chat))
        messages, chat_status = open_ai_service.generate(
            serializer.validated_data['text'], request
        )
        messages_in_response = [
            {
                'type': message.type,
                'text': message.content,
                'files': {
                    'audio': safe_url(request, message.audio.file) if message.audio else None,
                    'pdf': safe_url(request, message.pdf.file) if message.pdf else None
                }
            } for message in messages
        ]

        return Response(
            data={
                'data': {
                    'chat_id': chat.id,
                    'status': chat_status,
                    'messages': messages_in_response
                }
            }, status=status.HTTP_200_OK
        )

class GenerateAudioView(APIView):
    """
    POST /api/generate-audio/此
    Принимает multipart/form-data с полями:
      - file: аудио
      - user_id: идентификатор чата
    Возвращает обработанный аудиофайл.
    """
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        serializer = GenerateAudioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        upload = serializer.validated_data['file']
        user_id = serializer.validated_data.get('user_id')

        user_service = UserService(user_id)
        user = user_service.get_user()

        chat, _ = Chat.objects.get_or_create(user=user)

        message_service = MessageService(chat)
        openai_service = OpenAIAPIService(OPENAI_API_KEY, message_service)

        raw = upload.read()
        mp3_bytes = ogg_bytes_to_mp3_bytes(raw)

        transcript = openai_service.speach_to_text(mp3_bytes)

        generated = openai_service.generate(
            transcript
        )

        speach = openai_service.text_to_speach(generated.get('text'))
        speach.seek(0)
        return FileResponse(
            speach,
            as_attachment=True,
            filename='response.mp3',
            content_type='audio/mp3'
        )
