from django.db import models

from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

class UserST(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="userst",
        help_text="Связанный пользователь Django.",
    )
    username = models.CharField(max_length=25)
    registered_date = models.DateTimeField(auto_now_add=True)
    trade_link = models.URLField(default="", blank=True)
    count_buy = models.PositiveIntegerField(default=0)
    count_sell = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    inventory_json = models.JSONField(default=dict, blank=True)
    steam_ID = models.CharField(max_length=17, unique=True)
    email = models.EmailField(null=True, unique=True)
    telegram = models.CharField(max_length=20, null=True, unique=True)

    class Meta:
        indexes = [
            models.Index(fields=["steam_ID"]),
            models.Index(fields=["email"]),
            models.Index(fields=["telegram"]),
        ]
        verbose_name = "Steam User"
        verbose_name_plural = "Steam Users"

    def clean(self):
        if self.rating < 0 or self.rating > 5:
            raise ValidationError("Рейтинг должен быть в диапазоне от 0.00 до 5.00.")

    def __str__(self):
        return f"{self.username} ({self.steam_ID})"


class ItemST(models.Model):
    item_steam_ID = models.CharField(max_length=25, null=True, unique=True)
    user = models.ForeignKey(
        UserST, on_delete=models.CASCADE, related_name="items", null=True
    )
    price = models.DecimalField(decimal_places=2, max_digits=10)
    status_trade = models.BooleanField(default=True)
    date_push_item = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.item_steam_ID


class TradeST(models.Model):
    STATUS_CHOICES = (
        ("получен", "Получен"),
        ("ожидает оплаты", "Ожидает оплаты"),
        ("отменен", "Отменен"),
    )

    trade_status_st = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="ожидает оплаты"
    )
    item = models.ForeignKey(ItemST, on_delete=models.CASCADE, related_name="trades")
    buyer_ID = models.CharField(max_length=17, null=True)
    date_push_trade = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trade {self.item.user.steam_ID}: {self.item.item_steam_ID} -> {self.buyer_ID}"

class Dialog(models.Model):
    participants = models.ManyToManyField(UserST, related_name='dialogs')
    last_message = models.ForeignKey('Message', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dialog between {self.participants.first()} and {self.participants.last()}"

    class Meta:
        verbose_name = "Dialog"
        verbose_name_plural = "Dialogs"

class Message(models.Model):
    dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(UserST, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(UserST, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    msg_id = models.BigAutoField(primary_key=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Обновляем ссылку на последнее сообщение в диалоге
        self.dialog.last_message = self
        self.dialog.save()

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.content}"


