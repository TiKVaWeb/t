from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.homepage, name="homepage"),
    path("home/", views.home, name="home"),
    path('profile/', views.profile, name="profile"),
    path('inventory/', views.inventory, name="inventory"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("tradelink/", views.save_tradelink, name="tradelink"),
    path("email/", views.save_email, name="email"),
    path("telegram/", views.save_telegram, name="telegram"),
    path("chat/", views.chat_view, name="chat"),  # Общий чат (без receiver_id)
    path("chat/<int:receiver_id>/", views.chat_view, name="chat_with_user"),  # Чат с конкретным пользователем
    path('api/dialogs/', views.DialogListView.as_view(), name='dialog-list'),
    path('api/chat-history/<int:dialog_id>/', views.ChatHistoryAPIView.as_view(), name='chat-history'),
]
