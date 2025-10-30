from django.urls import path
from . import views


# This is a good practice to avoid URL name collisions with other apps
app_name = 'AI_Assistant'

urlpatterns = [
    # This will be the main page for our chat interface
    path('chat/', views.chat_page_view, name='chat_page'),
    
    # These are the API endpoints for the chat logic
    path('api/start_chat/', views.start_chat_view, name='start_chat'),
    path('api/ask/', views.ask_assistant_view, name='ask'),
]