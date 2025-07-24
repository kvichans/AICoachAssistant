from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, ChatViewSet, GenerateTextView, GenerateAudioView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'chats', ChatViewSet, basename='chat')
urlpatterns = [
    path('', include(router.urls)),
    path('generate-text/', GenerateTextView.as_view(), name='generate-text'),
    path('generate-audio/', GenerateAudioView.as_view(), name='generate-audio'),
]