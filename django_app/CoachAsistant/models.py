from django.db import models
from django.utils.translation import gettext_lazy as _

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['created_at']

class RoleChoice(models.TextChoices):
    DEVELOPER = 'developer', _('Developer')
    USER = 'user', _('User')
    ASSISTANT = 'assistant', _('Assistant')

class OpenAIAssistant(models.Model):
    '''
    Модель для хранения ассистената
    '''
    id = models.CharField(
        primary_key=True,
        max_length=100,
        help_text='Уникальный идентификатор ассистента (например, "asst_abc123")'
    )
    object = models.CharField(
        max_length=50,
        default='assistant',
        help_text='Тип объекта (по умолчанию "assistant")'
    )
    # Поле "created_at" в JSON хранится в виде UNIX-времени (секунды с 1970-01-01)
    # В Django удобнее хранить это как DateTimeField. При сохранении нужно будет конвертировать
    # UNIX-метку в datetime. Если нужен «сырый» int, можно заменить на IntegerField.
    created_at = models.IntegerField(
        null=True,
        blank=True
    )
    name = models.CharField(
        max_length=200,
        help_text='Название ассистента (например, "Math Tutor")'
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text='Описание ассистента (может быть пустым)'
    )
    model = models.CharField(
        max_length=100,
        help_text='Имя используемой языковой модели (например, "gpt-4o")'
    )
    instructions = models.TextField(
        help_text='Системные инструкции для ассистента'
    )
    tools = models.JSONField(
        default=list,
        blank=True,
        help_text='Список инструментов (например, [{ "type": "code_interpreter" }])'
    )
    tool_resources = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Ресурсы для инструментов в формате: '
            '{"file_search": {"vector_store_ids": ["vs_123"]}}'
        )
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Дополнительная структурированная информация (до 16 пар ключ-значение)'
    )
    top_p = models.FloatField(
        default=1.0,
        help_text='Параметр top_p'
    )
    temperature = models.FloatField(
        default=1.0,
        help_text='Параметр temperature'
    )
    response_format = models.CharField(
        max_length=50,
        default='auto',
        help_text='Формат ответа от ассистента'
    )

    def __str__(self):
        return f'{self.name} ({self.id})'

class OpenAIThread(models.Model):
    """
    Модель для хранения Thread-объекта OpenAI.
    Ожидаемая JSON-структура:
    """

    id = models.CharField(
        primary_key=True,
        max_length=100,
        help_text='Уникальный идентификатор потока (например, "thread_abc123")'
    )
    object = models.CharField(
        max_length=50,
        default="thread",
        help_text='Тип объекта (по умолчанию "thread")'
    )
    created_at = models.IntegerField(
        null=True,
        blank=True
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Дополнительная структурированная информация (до 16 пар ключ-значение)'
    )


class User(models.Model):
    """
    Модель для хранения пользователя
    """
    chat_id = models.BigIntegerField(
        primary_key=True,
        help_text='Уникальный идентификатор чата в Telegram'
    )
    title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Заголовок чата (может быть пустым для личного диалога)'
    )
    username = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Username пользователя (если есть)'
    )
    first_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Имя пользователя'
    )
    last_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Фамилия пользователя'
    )
    paid = models.BooleanField(
        default=False,
        help_text='Статус оплаты (True, если оплачено)'
    )
    assistant = models.ForeignKey(
        OpenAIAssistant,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="users",
        help_text='Ассистент, связанный с этим Telegram-пользователем'
    )
    thread = models.ForeignKey(
        OpenAIThread,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users'
    )


class Chat(models.Model):
    user = models.ForeignKey(
        User,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name='chat'
    )
    exercise =models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )


class Message(TimeStampedModel):
    chat = models.ForeignKey(
        Chat,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(
        max_length=50,
        null=False,
        blank=False,
        choices=RoleChoice.choices
    )
    content = models.TextField(
        null=False,
        blank=False
    )


class Exercise(models.Model):
    name = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )
    content = models.TextField(
        null=False,
        blank=False
    )
    order = models.IntegerField(
        null=False,
        blank=False
    )
