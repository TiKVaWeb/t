import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, UserST, Dialog
import logging

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.receiver_id = self.scope['url_route']['kwargs']['receiver_id']

        # Получаем UserST для текущего пользователя и получателя
        self.user_st = await self.get_userst()
        self.receiver = await self.get_receiver(self.receiver_id)

        if not self.user_st or not self.receiver:
            await self.close()
            return

        # Находим диалог между пользователями
        self.dialog = await self.get_dialog(self.user_st, self.receiver)
        if not self.dialog:
            await self.close()
            return

        self.room_name = f"dialog_{self.dialog.id}"  # Используем ID диалога для группы
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    @database_sync_to_async
    def get_userst(self):
        try:
            return UserST.objects.get(user=self.user)
        except UserST.DoesNotExist:
            return None

    @database_sync_to_async
    def get_receiver(self, receiver_id):
        try:
            return UserST.objects.get(id=receiver_id)
        except UserST.DoesNotExist:
            return None

    @database_sync_to_async
    def get_dialog(self, user_st, receiver):
        return Dialog.objects.filter(participants=user_st).filter(participants=receiver).first()

    @database_sync_to_async
    def create_message(self, sender, receiver, content):
        # Находим или создаём диалог
        dialog = Dialog.objects.filter(participants=sender).filter(participants=receiver).first()
        if not dialog:
            dialog = Dialog.objects.create()
            dialog.participants.add(sender, receiver)

        # Создаём новое сообщение
        message = Message.objects.create(
            dialog=dialog,
            sender=sender,
            receiver=receiver,
            content=content,
        )
        return message

    async def receive(self, text_data):
        data = json.loads(text_data)
        receiver_id = data["receiver_id"]
        content = data["content"]

        # Проверяем, существует ли получатель
        receiver = await self.get_receiver(receiver_id)
        if not receiver:
            await self.send(text_data=json.dumps({"error": f"User with ID {receiver_id} does not exist"}))
            return

        # Создаём новое сообщение
        message = await self.create_message(self.user_st, receiver, content)

        # Формируем данные сообщения
        message_data = {
            "id": message.msg_id,
            "message": message.content,
            "sender": self.user_st.username,
            "timestamp": message.timestamp.isoformat(),
        }

        # Отправляем сообщение в группу диалога
        await self.channel_layer.group_send(
            f"dialog_{message.dialog.id}",
            {"type": "chat_message", **message_data},
        )

    async def chat_message(self, event):
        # Отправляем сообщение клиенту
        await self.send(text_data=json.dumps({
            "id": event["id"],
            "message": event["message"],
            "sender": event["sender"],
            "timestamp": event["timestamp"],
        }))