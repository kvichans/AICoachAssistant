from django.contrib import admin
import os

from .models import OpenAIAssistant, OpenAIThread, User
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


@admin.register(OpenAIAssistant)
class OpenAIAssistantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'model', 'created_at')
    search_fields = ('id', 'name', 'model')
    list_filter = ('model',)
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': (
                'id',
                'object',
                'name',
                'description',
                'model',
                'instructions',
                'tools',
                'tool_resources',
                'metadata',
                'top_p',
                'temperature',
                'response_format',
            ),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    def save_model(self, request, obj, form, change):
        client.beta.assistants.update(
            assistant_id=obj.id,
            name=obj.name,
            instructions=obj.instructions or "",
            model=obj.model,
            tools=obj.tools or [],
            tool_resources=obj.tool_resources or {},
            metadata=obj.metadata or {},
            top_p=obj.top_p,
            temperature=obj.temperature,
            response_format=obj.response_format
        )
        obj.save()
    def delete_model(self, request, obj):
        try:
            client.beta.assistants.delete(obj.id)
        except:
            pass
        obj.delete()


@admin.register(OpenAIThread)
class OpenAIThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'object', 'created_at')
    search_fields = ('id',)
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('id', 'object', 'metadata'),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('chat_id', 'username', 'first_name', 'last_name', 'paid', 'assistant', 'thread')
    search_fields = ('chat_id', 'username', 'first_name', 'last_name')
    list_filter = ('paid', 'assistant')
    raw_id_fields = ('assistant', 'thread')
    fieldsets = (
        (None, {
            'fields': (
                'chat_id',
                'title',
                'username',
                'first_name',
                'last_name',
                'paid',
                'assistant',
                'thread',
            ),
        }),
    )
