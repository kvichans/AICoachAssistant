from django.contrib import admin
from django.template.defaultfilters import title
from django.utils.html import format_html, escape, format_html_join
from django.urls import reverse
import os

from .models import (User, Exercise, Chat, Instruction, ChatProgress,
                     Message, Audio, PDFFile)
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class ChatProgressInline(admin.TabularInline):
    model = ChatProgress
    fk_name = 'user'                 # <— ключевой момент
    extra = 0
    fields = ('id_link', 'exercise_display', 'status', 'started_at', 'finished_at')
    readonly_fields = ('id_link', 'exercise_display', 'status','started_at', 'finished_at')  # на свое усмотрение
    show_change_link = False
    can_delete = False

    def id_link(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("admin:%s_%s_change" % (  #!kv %
            obj._meta.app_label, obj._meta.model_name
        ), args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.pk)
    id_link.short_description = "ID"    #!kv

    def exercise_display(self, obj):
        return str(obj.exercise) if obj.exercise else "-"

    exercise_display.short_description = "Текущий прогресс"

class ChatInline(admin.TabularInline):
    model = Chat
    fk_name = 'user'
    extra = 0
    fields = ('current_exercise_display',)
    readonly_fields = ('current_exercise_display',)
    show_change_link = False
    can_delete = False

    def current_exercise_display(self, obj):
        return str(obj.current_exercise) if obj.current_exercise else "-"
    current_exercise_display.short_description = "Текущее упражнение"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'first_name', 'last_name', 'paid')
    inlines = [ChatInline, ChatProgressInline]

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'is_active')
    search_fields = ('id','name')
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'order',
                'content',
                'is_active',
                'start_audio',
                'end_audio',
                'start_pdf',
                'end_pdf',
                'additional_audio',
                'additional_pdf',
            ),
        }),
    )

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'current_exercise')
    fieldsets = (
        (None, {
            'fields': (
                'user',
                'current_exercise'
            ),
        }),
    )

@admin.register(Instruction)
class InstructionAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_active')
    fieldsets = (
        (None, {
            'fields': (
                'text',
                'is_active',
            ),
        }),
    )

@admin.register(ChatProgress)
class ChatProgressAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'exercise', 'status', 'messages_count')
    readonly_fields = ('messages_block',)

    fieldsets = (
        (None, {
            'fields': ('chat', 'exercise', 'status', 'started_at', 'finished_at')
        }),
        ('Переписка (сплошным текстом)', {
            'classes': ('collapse',),
            'fields': ('messages_block',),
        }),
    )

    def _messages_qs(self, obj):
        # можно оптимизировать, чтобы не тянуть лишнего
        return (Message.objects
                .filter(chat=obj.chat, exercise=obj.exercise)
                .only('role', 'content', 'created_at')
                .order_by('created_at'))

    def messages_count(self, obj):
        return self._messages_qs(obj).count()
    messages_count.short_description = "Сообщений"

    def messages_block(self, obj):
        """
        Полный сплошной текст с переносами — как в твоём примере с <pre>.
        """
        qs = self._messages_qs(obj)
        if not qs.exists():
            return "Сообщений нет."

        lines = [
            f"{m.created_at:%Y-%m-%d %H:%M:%S} [{m.get_role_display()}]\n— {m.content}\n\n"
            for m in qs
        ]

        full_text = "\n".join(lines)

        return format_html(
            '<pre style="background:#0b1020; color:#e5e7eb; padding:10px; border-radius:6px; '
            'white-space: pre-wrap; word-wrap: break-word; max-height: 480px; overflow:auto;">{}</pre>',
            escape(full_text)
        )
    messages_block.short_description = "Все сообщения (сплошной текст)"

@admin.register(Audio)
class AudioAdmin(admin.ModelAdmin):
    list_display = ('title', 'sex', 'is_first', 'is_second', 'is_last')
    fieldsets = (
        (None, {
            'fields': (
                'title',
                'file',
                'sex',
                'is_first',
                'is_second',
                'is_last',
            )
        }),
    )

@admin.register(PDFFile)
class PDFFileAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_first', 'is_second', 'is_last')
    fieldsets = (
        (None, {
            'fields': (
                'title',
                'file',
                'is_first',
                'is_second',
                'is_last',
            )
        }),
    )