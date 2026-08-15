from django.urls import path

from apps.chat.views import chat, history

urlpatterns = [
    path('', chat, name='chat'),
    path('history/', history, name='chat-history'),
]
