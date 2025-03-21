import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from social_django.models import UserSocialAuth

from web.models import *

from .steam_api import get_steam_inventory, parse_inventory_items

logger = logging.getLogger(__name__)




def homepage(request):
    return render(request, "Fullstack_market/User/chat.html")
# def homepage(request):
#     return render(request, "front/index.html")


@login_required
def profile(request):
    """
    Отображает личные данные пользователя Steam + данные с БД.
    """
    try:
        steam_user, user_st = get_steam_user_and_profile(request)
        steam_id = steam_user.uid
        player_info = steam_user.extra_data.get("player", {})

        context = {
            "steam_id": steam_id,
            "player_info": player_info,
            "user_st": user_st,
        }
        return render(request, "front/new_profille.html", context)

    except Exception as e:
        logger.error(f"Error in profile_info view: {str(e)}")
        return render(request, "successfully.html", {"error": str(e)})


@login_required
def inventory(request):
    """
    Отображает инвентарь пользователя Steam.
    """
    try:
        steam_user, user_st = get_steam_user_and_profile(request)
        steam_id = steam_user.uid

        # Получаем инвентарь
        inventory_data = get_steam_inventory(steam_id)
        if inventory_data is None:
            logger.error("Failed to get inventory data — probably private or error")
            inventory_items = []
            error_message = "Failed to load inventory (maybe private?)."
        else:
            inventory_items = parse_inventory_items(inventory_data)
            error_message = None

        context = {
            "steam_id": steam_id,
            "inventory_items": inventory_items,
            "user_st": user_st,
            "error": error_message,
        }
        return render(request, "successfully.html", context)

    except Exception as e:
        logger.error(f"Error in inventory view: {str(e)}")
        return render(request, "successfully.html", {"error": str(e)})


@login_required
def home(request):
    try:
        steam_user = UserSocialAuth.objects.get(user=request.user, provider="steam")
        steam_id = steam_user.uid
        player_info = steam_user.extra_data.get("player", {})

        # Всегда сначала создаём/получаем пользователя
        user_st, created = UserST.objects.get_or_create(
            steam_ID=steam_id,
            defaults={
                "username": player_info.get("personaname", steam_id),
            },
        )
        if created:
            logger.info(f"Created user {user_st.username}")

        # Далее пробуем получить инвентарь
        inventory_data = get_steam_inventory(steam_id)
        if inventory_data is None:
            logger.error("Failed to get inventory data — probably private or error")
            inventory_items = []
            error_message = "Failed to load inventory (maybe private?)."
        else:
            # Парсим инвентарь
            inventory_items = parse_inventory_items(inventory_data)
            error_message = None

        context = {
            "steam_id": steam_id,
            "player_info": player_info,
            "inventory_items": inventory_items,
            "user_st": user_st,
            "error": error_message,
        }
        return render(request, "front/new_profille.html", context)

    except UserSocialAuth.DoesNotExist:
        logger.error("Steam authentication not found")
        return render(
            request, "successfully.html", {"error": "Steam authentication not found"}
        )
    except Exception as e:
        logger.error(f"Error in home view: {str(e)}")
        return render(request, "successfully.html", {"error": str(e)})





# ---- Вспомогательные ручки ---- #

def get_steam_user_and_profile(request):
    """
    Получает данные пользователя Steam и создаёт/получает профиль UserST.
    Возвращает (steam_user, user_st) или вызывает исключение.
    """
    try:
        steam_user = UserSocialAuth.objects.get(user=request.user, provider="steam")
        steam_id = steam_user.uid
        player_info = steam_user.extra_data.get("player", {})

        # Создаём или получаем профиль пользователя
        user_st, created = UserST.objects.get_or_create(
            steam_ID=steam_id,
            defaults={
                "username": player_info.get("personaname", steam_id),
                "user": request.user,  # Устанавливаем поле user
            },
        )
        if created:
            logger.info(f"Created user {user_st.username}")

        return steam_user, user_st
    except UserSocialAuth.DoesNotExist:
        logger.error("Steam authentication not found")
        raise Exception("Steam authentication not found")
    except Exception as e:
        logger.error(f"Error getting Steam user: {str(e)}")
        raise Exception(f"Error getting Steam user: {e}")

# ---- Ручки для сохранения данных в ЛП ---- #

def save_tradelink(request):
    if request.method == "POST":
        tradelink = request.POST.get("tradelink")
        steam_user = UserSocialAuth.objects.get(user=request.user, provider="steam")
        steam_id = steam_user.uid

        if tradelink:
            user = UserST.objects.get(steam_ID=steam_id)
            user.trade_link = tradelink
            user.save()

        return redirect(reverse("home"))
    else:
        return HttpResponse("Недопустимый метод запроса!")


def save_email(request):
    if request.method == "POST":
        email = request.POST.get("email")
        steam_user = UserSocialAuth.objects.get(user=request.user, provider="steam")
        steam_id = steam_user.uid

        if email:
            user = UserST.objects.get(steam_ID=steam_id)
            user.email = email
            user.save()

        return redirect(reverse("home"))
    else:
        return HttpResponse("Недопустимый метод запроса!")


def save_telegram(request):
    if request.method == "POST":
        telegram = request.POST.get("telegram")
        steam_user = UserSocialAuth.objects.get(user=request.user, provider="steam")
        steam_id = steam_user.uid

        if telegram:
            user = UserST.objects.get(steam_ID=steam_id)
            user.telegram = telegram
            user.save()

        return redirect(reverse("home"))
    else:
        return HttpResponse("Недопустимый метод запроса!")


@login_required
def chat_view(request, receiver_id=None):
    try:
        user_st = request.user.userst  # Получаем UserST для текущего пользователя
    except UserST.DoesNotExist:
        return render(request, "error.html", {"error": "UserST not found"})

    receiver = None
    dialog_id = None

    if receiver_id:
        try:
            receiver = get_object_or_404(UserST, id=receiver_id)
            # Находим или создаём диалог между текущим пользователем и получателем
            dialog = Dialog.objects.filter(participants=user_st).filter(participants=receiver).first()
            if not dialog:
                dialog = Dialog.objects.create()
                dialog.participants.add(user_st, receiver)
            dialog_id = dialog.id
        except UserST.DoesNotExist:
            return render(request, "error.html", {"error": f"User with ID {receiver_id} does not exist"})

    context = {
        "user_id": user_st.id,
        "receiver_id": receiver_id,
        "dialog_id": dialog_id,  # Передаём ID диалога в шаблон
        'user_st': user_st,
    }
    return render(request, "testchat.html", context)





from rest_framework.views import APIView
from rest_framework.response import Response


class DialogListView(APIView):
    def get(self, request):
        user = request.user
        dialogs = Dialog.objects.filter(participants=user.userst).order_by('-updated_at')[:50]

        dialog_data = []
        for dialog in dialogs:
            other_participant = dialog.participants.exclude(id=user.userst.id).first()
            last_message = dialog.last_message.content if dialog.last_message else "No messages yet"
            dialog_data.append({
                "id": dialog.id,
                "participant_id": other_participant.id,
                "participant_username": other_participant.username,
                "last_message": last_message,
                "updated_at": dialog.updated_at.isoformat(),
            })

        return Response(dialog_data)


class ChatHistoryAPIView(APIView):
    def get(self, request, dialog_id):
        # Получаем все сообщения из диалога
        messages = Message.objects.filter(dialog_id=dialog_id).order_by('timestamp')[:50]
        data = [
            {
                "id": msg.msg_id,
                "message": msg.content,
                "sender": msg.sender.username,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ]
        return Response(data)