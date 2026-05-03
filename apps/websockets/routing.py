from django.urls import re_path

from .consumer import ExpeditionConsumer

websocket_urlpatterns = [
    re_path(r'^ws/expeditions/(?P<expedition_id>\d+)/$', ExpeditionConsumer.as_asgi()),
]
