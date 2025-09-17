from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (UserViewSet, ChatViewSet, GenerateTextView,
                    GenerateAudioView, ExerciseViewSet, AudioViewSet,
                    PDFViewSet, ChatProgressViewSet)

router = DefaultRouter()    #!kv ver
router.register(r'users', UserViewSet, basename='user')
router.register(r'chats', ChatViewSet, basename='chat')
router.register(r'exercises', ExerciseViewSet, basename='exercise')
router.register(r'audio', AudioViewSet, basename='audio')
router.register(r'pdf', PDFViewSet, basename='pdf')
router.register(r'progress', ChatProgressViewSet, basename='progress')
urlpatterns = [
    path('', include(router.urls)), #!kv ver
    path('generate-text/', GenerateTextView.as_view(), name='generate-text'),
    path('generate-audio/', GenerateAudioView.as_view(), name='generate-audio'),
]