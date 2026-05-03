from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.expeditions.models import Expedition, ExpeditionMember


class ExpeditionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        expedition_id = self.scope['url_route']['kwargs']['expedition_id']
        self.group_name = f'expedition_{expedition_id}'

        authorized = await self._is_authorized(user, expedition_id)
        if not authorized:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def expedition_event(self, event):
        await self.send_json({
            'type': event['event_type'],
            'payload': event['payload'],
        })

    async def _is_authorized(self, user, expedition_id: int) -> bool:
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def check():
            return (
                Expedition.objects.filter(pk=expedition_id, chief=user).exists()
                or ExpeditionMember.objects.filter(expedition_id=expedition_id, user=user).exists()
            )

        return await check()
