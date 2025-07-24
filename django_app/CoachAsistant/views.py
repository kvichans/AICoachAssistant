import os
from io import BytesIO
from dotenv import load_dotenv
from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import FileResponse, Http404


from .models import User, Chat, Exercise
from .serializers import UserSerializer, GenerateTextSerializer, GenerateAudioSerializer, ChatSerializer, ExerciseSerializer
from .servises import AudioGenerationService, TextGenerationService, OpenAIAPIService
from .servises import MessageService, UserService, ogg_bytes_to_mp3_bytes

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

class UserViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    Создание, получение и удаление пользователей по chat_id.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'chat_id'

class ChatViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer

class ExerciseViewSet(viewsets.ReadOnlyModelViewSet):
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
                schema=GenerateTextSerializer
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = GenerateTextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_service = UserService(serializer.validated_data['chat_id'])
        user = user_service.get_user()

        chat, _ = Chat.objects.get_or_create(user=user)

        message_service = MessageService(chat)

        generated = TextGenerationService.generate(
            message_service,
            serializer.validated_data['text']
        )
        return Response(data={'data': generated}, status=status.HTTP_200_OK)

class GenerateAudioView(APIView):
    """
    POST /api/generate-audio/此
    Принимает multipart/form-data с полями:
      - file: аудио
      - chat_id: идентификатор чата
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
        openai_service = OpenAIAPIService(OPENAI_API_KEY)

        raw = upload.read()
        mp3_bytes = ogg_bytes_to_mp3_bytes(raw)

        transcript = openai_service.speach_to_text(mp3_bytes)

        generated = TextGenerationService.generate(
            message_service,
            transcript
        )

        speach = openai_service.text_to_speach(generated)
        speach.seek(0)
        return FileResponse(
            speach,
            as_attachment=True,
            filename='response.mp3',
            content_type='audio/mp3'
        )
