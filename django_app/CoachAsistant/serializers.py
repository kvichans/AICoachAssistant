from rest_framework import serializers

from .models import User, Chat, Message, Exercise, ChatProgress, Audio, PDFFile


class MessageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Message.
    """
    class Meta:
        model = Message
        fields = ['id', 'chat', 'role', 'content', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели User.
    Включает вложенные ассистента, тред и чаты.
    """

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'sex',
            'paid',
            'telegram_id'
        ]


class GenerateTextSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(
        help_text='ID пользователя'
    )
    text = serializers.CharField(
        help_text='Текст сообщения для генерации ответа',
        trim_whitespace=True,
        required=True
    )
    status = serializers.CharField(read_only=True)

    def validate_id(self, value):
        """
        Проверяем, что пользователь с таким chat_id существует.
        """
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError('Пользователь с таким user_id не найден.')
        return value

    def validate_text(self, value):
        """
        Запрещаем пустую строку.
        """
        if not value.strip():
            raise serializers.ValidationError('Текст не может быть пустым.')
        return value

class ResponseGenerateSerializer(serializers.Serializer):
    data = GenerateTextSerializer()

class GenerateAudioSerializer(serializers.Serializer):
    """
    Сериализатор для генерации аудио из текста.
    Принимает user_id и текст для озвучки.
    """
    user_id = serializers.IntegerField(
        help_text='ID пользователя'
    )
    file = serializers.FileField(
        help_text='Загружаемый файл'
    )

    def validate_id(self, value):
        """
        Проверяем, что пользователь с таким chat_id существует.
        """
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                'Пользователь с таким user_id не найден.')
        return value

class ExerciseSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Exercise.
    """
    class Meta:
        model = Exercise
        fields = ['id', 'name', 'order', 'start_audio', 'end_audio',
                  'additional_audio', 'start_pdf', 'end_pdf', 'additional_pdf']

class ProgressSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer()  # вложим инфо об упражнении

    class Meta:
        model = ChatProgress
        fields = ['id', 'status', 'started_at', 'finished_at', 'exercise']


class ChatSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Chat с вложенными сообщениями.
    """
    progress = ProgressSerializer(many=True, read_only=True)

    class Meta:
        model = Chat
        fields = ['id', 'user', 'progress','messages']

class AudioSerializer(serializers.ModelSerializer):

    class Meta:
        model = Audio
        fields = '__all__'

class PDFSerializer(serializers.ModelSerializer):

    class Meta:
        model = PDFFile
        fields = '__all__'