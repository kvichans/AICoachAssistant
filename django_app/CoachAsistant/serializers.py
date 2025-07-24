import datetime
from django.utils import timezone
from rest_framework import serializers

from .models import OpenAIAssistant, OpenAIThread, User, Chat, Message, Exercise




class OpenAIAssistantSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели OpenAIAssistant,
    где created_at — просто IntegerField.
    """
    instructions = serializers.CharField(allow_blank=True)

    class Meta:
        model = OpenAIAssistant
        # Указываем ровно те поля, что есть в модели
        fields = [
            'id',
            'object',
            'created_at',
            'name',
            'description',
            'model',
            'instructions',
            'tools',
            'metadata',
            'top_p',
            'temperature',
            'response_format',
        ]
        read_only_fields = ['object']

class OpenAIThreadSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели OpenAIThread:
    {
      "id": "thread_abc123",
      "object": "thread",
      "created_at": 1698107661,
      "metadata": { ... }
    }
    """

    # Поле “object” по умолчанию равно "thread", можно сделать его read-only
    object = serializers.CharField(read_only=True)

    class Meta:
        model = OpenAIThread
        fields = [
            "id",
            "object",
            "created_at",
            "metadata",
        ]
        extra_kwargs = {
            "id": {"help_text": "Уникальный идентификатор потока (например, \"thread_abc123\")"},
            "created_at": {"required": False, "allow_null": True},
            "metadata": {"required": False},
        }


class MessageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Message.
    """
    class Meta:
        model = Message
        fields = ['id', 'chat', 'role', 'content', 'created_at', 'updated_at']


class ChatSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Chat с вложенными сообщениями.
    """

    class Meta:
        model = Chat
        fields = ['id', 'user', 'exercise']


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели User.
    Включает вложенные ассистента, тред и чаты.
    """
    chat = ChatSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'chat_id',
            'title',
            'username',
            'first_name',
            'last_name',
            'paid',
            'chat'
        ]


class GenerateTextSerializer(serializers.Serializer):
    chat_id = serializers.IntegerField(
        help_text='ID Telegram-чата пользователя'
    )
    text = serializers.CharField(
        help_text='Текст сообщения для генерации ответа',
        trim_whitespace=True
    )
    exercise = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Название упражнения (необязательно)'
    )

    def validate_user_id(self, value):
        """
        Проверяем, что пользователь с таким chat_id существует.
        """
        if not User.objects.filter(chat_id=value).exists():
            raise serializers.ValidationError('Пользователь с таким user_id не найден.')
        return value

    def validate_text(self, value):
        """
        Запрещаем пустую строку.
        """
        if not value.strip():
            raise serializers.ValidationError('Текст не может быть пустым.')
        return value

class GenerateAudioSerializer(serializers.Serializer):
    """
    Сериализатор для генерации аудио из текста.
    Принимает user_id и текст для озвучки.
    """
    user_id = serializers.IntegerField(
        help_text='ID Telegram-чата пользователя'
    )
    file = serializers.FileField(
        help_text='Загружаемый файл'
    )

    def validate_user_id(self, value):
        if not User.objects.filter(chat_id=value).exists():
            raise serializers.ValidationError('Пользователь с таким chat_id не найден.')
        return value

class ExerciseSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Exercise.
    """
    class Meta:
        model = Exercise
        fields = ['id', 'name', 'content', 'order']
