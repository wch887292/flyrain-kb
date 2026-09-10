from django.urls import path

from apps.chat.views import chat, history, session_list, session_delete, feedback, stats, export_session, export_pdf

urlpatterns = [
    path('', chat, name='chat'),
    path('history/', history, name='chat-history'),
    path('sessions/', session_list, name='chat-session-list'),
    path('sessions/delete/', session_delete, name='chat-session-delete'),
    path('feedback/', feedback, name='chat-feedback'),
    path('stats/', stats, name='chat-stats'),
    path('export/', export_session, name='chat-export'),
    path('export/pdf/', export_pdf, name='chat-export-pdf'),
]
