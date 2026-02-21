# base/urls/ai_urls.py
from django.urls import path
from base.views.ai_chat_views import ai_chat

urlpatterns = [
    path("chat/", ai_chat, name="ai-chat"),
]