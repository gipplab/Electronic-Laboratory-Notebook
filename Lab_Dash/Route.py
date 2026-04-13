# ✅ Moderne Channels 4.0+ Struktur
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from . import consumers

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/dashboard/<str:pk>/", consumers.DashboardConsumer.as_asgi()),
        ])
    ),
})

# Consumer-Klassen müssen async def verwenden:
class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.close()