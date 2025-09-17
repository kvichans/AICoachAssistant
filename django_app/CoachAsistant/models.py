from django.db import models
from django.db.models import Q
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
    INTERNAL = 'internal', _('Внутренняя')  #!kv

class ProgressStatus(models.TextChoices):
    NOT_STARTED = 'not_started', _('Not started')
    IN_PROGRESS = 'in_progress', _('In progress')
    ENDED = 'ended', _('Ended')
    DONE = 'done', _('Done')

class TypesMessage(models.TextChoices):
    AUDIO = 'audio', _('Audio')
    PDF = 'pdf', _('PDF')
    TEXT = 'text', _('Text')

class SexChoice(models.TextChoices):
    MALE = 'male', _('Male')
    FEMALE = 'female', _('Female')

class User(models.Model):
    username = models.CharField(max_length=255, null=True, blank=True)  #!kv
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    sex = models.CharField(choices=SexChoice, default=SexChoice.MALE, max_length=255)   #!kv
    paid = models.BooleanField(default=False)
    telegram_id = models.BigIntegerField(
        help_text='Уникальный идентификатор чата в Telegram',
        null = True,
        blank = True,
        unique=True,
    )

    def __str__(self):
        return f"{self.username or self.first_name or self.telegram_id}"    #!kv all

class Audio(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    file = models.FileField(upload_to='audio')
    sex = models.CharField(choices=SexChoice, default=SexChoice.MALE, max_length=255)
    is_first = models.BooleanField(default=False)
    is_second = models.BooleanField(default=False)
    is_last = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.title} | {self.sex}'

class PDFFile(models.Model):    #!kv commin base
    title = models.CharField(max_length=255, null=True, blank=True)
    file = models.FileField(upload_to='pdf')
    is_first = models.BooleanField(default=False)
    is_second = models.BooleanField(default=False)
    is_last = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.title}'

class Exercise(models.Model):
    """
    Упражнение (шаг). Управляется из админки.
    Поле order — порядок прохождения (уникальный, индексируемый).
    """
    name = models.CharField(max_length=255)
    content = models.TextField()
    order = models.PositiveSmallIntegerField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    start_audio = models.ForeignKey(
        Audio,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exercises_as_start_audio',  # уникально   #!kv exercises?
        related_query_name='exercise_as_start_audio',  # опционально    #!kv
    )
    end_audio = models.ForeignKey(
        Audio,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exercises_as_end_audio',
        related_query_name='exercise_as_end_audio',
    )
    additional_audio = models.ForeignKey(
        Audio,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exercises_as_additional_audio',
        related_query_name='exercise_as_additional_audio',
    )
    start_pdf = models.ForeignKey(
        PDFFile,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exercises_as_start_pdf',
        related_query_name='exercise_as_start_pdf',
    )
    end_pdf = models.ForeignKey(
        PDFFile,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exercises_as_end_pdf',
        related_query_name='exercise_as_end_pdf',
    )
    additional_pdf = models.ForeignKey(
        PDFFile,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exercises_as_additional_pdf',
        related_query_name='exercise_as_additional_pdf',
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"[{self.order}] {self.name}"

    def next(self):
        return Exercise.objects.filter(is_active=True, order__gt=self.order).order_by('order').first() #!kv no? order_by?


class Instruction(models.Model):
    """
    Глобальная инструкция. Держим В ОДНОМ активном экземпляре.
    (Можно хранить архив неактивных версий)
    """
    text = models.TextField()
    is_active = models.BooleanField(default=True)   #!kv fail

    class Meta:
        constraints = [
            # Разрешает иметь много записей, но только ОДНУ активную
            models.UniqueConstraint(
                condition=Q(is_active=True),
                fields=["is_active"],
                name='only_one_active_instruction'
            )   #!kv fail
        ]

    def __str__(self):
        return f"Instruction (active={self.is_active})"

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()


class Chat(models.Model):   #!kv char? progress!
    """
    Чат пользователя. current_exercise — "указатель" на текущее упражнение.
    История/состояния по каждому упражнению храним в ChatProgress.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='chat' #!kv
    )
    status = models.CharField(choices=ProgressStatus, default=ProgressStatus.NOT_STARTED)
    current_exercise = models.ForeignKey(
        Exercise,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='chats_current'    #!kv
    )

    def __str__(self):
        return f"Chat<{self.user}>"     #!kv

    def _is_not_done(self, exercise: Exercise) -> bool:
        return not ChatProgress.objects.filter(chat=self, exercise=exercise, status=ProgressStatus.DONE).exists()

    def get_current_exercise(self) -> Exercise:
        """
        Если указатель не задан — найдём первый активный шаг,
        который ещё не DONE у этого чата.
        """
        if self.current_exercise and self._is_not_done(self.current_exercise):
            return self.current_exercise

        next_ex = (
            Exercise.objects
            .filter(is_active=True)
            .exclude(progress__chat=self, progress__status=ProgressStatus.DONE)
            .order_by('order')   #!kv del
            .first()
        )   #!kv fail "one path"
        if not next_ex:
            next_ex = None   #!kv ?
            self.current_exercise = next_ex
            self.save(update_fields=['current_exercise'])
            return next_ex
        if next_ex != self.current_exercise:
            self.current_exercise = next_ex
            self.save(update_fields=['current_exercise'])

            ChatProgress.objects.get_or_create(user=self.user,
                chat=self, exercise=self.current_exercise,
                defaults={'status': ProgressStatus.NOT_STARTED}
            )
        return next_ex

    def get_progress(self, exercise: Exercise):
        return ChatProgress.objects.filter(
            chat=self,
            exercise=exercise
        ).exclude(
            status=ProgressStatus.DONE
        ).order_by(
            'created_at'
        ).first()


class ChatProgress(TimeStampedModel):   #!kv TimeStampedModel? ChatProgress?
    """
    Прогресс по каждому упражнению для конкретного чата.
    """
    user = models.ForeignKey('User', on_delete=models.CASCADE,  #!kv 'User'
                             related_name='progress',   #!kv sses
                             editable=False, null=True, blank=True)     #!kv `null=True, blank=True`?
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='progress')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='progress')
    status = models.CharField(
        max_length=20,  #!kv max(len)
        choices=ProgressStatus.choices,
        default=ProgressStatus.NOT_STARTED
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('chat', 'exercise')  #!kv depr
        indexes = [
            models.Index(fields=['chat', 'status']),
            models.Index(fields=['exercise', 'status']),
        ]   #!kv рано

    def __str__(self):
        return f"{self.chat} — {self.exercise} [{self.status}]"


class Message(TimeStampedModel):    #!kv
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    role = models.CharField(max_length=50, choices=RoleChoice.choices)  #!kv max(len)
    content = models.TextField(null=True, blank=True)
    type = models.CharField(choices=TypesMessage.choices, default=TypesMessage.TEXT, max_length=50)  #!kv max(len)
    audio = models.ForeignKey(Audio, null=True, blank=True, on_delete=models.SET_NULL, default=None)
    pdf = models.ForeignKey(PDFFile, null=True, blank=True, on_delete=models.SET_NULL, default=None)

    def __str__(self):
        return f"{self.role}: {(self.content or '')[:40]}"  #!kv  or
