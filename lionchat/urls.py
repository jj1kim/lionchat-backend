from django.urls import path

from .views import (
    SignupView,
    LoginView,
    MeView,
    ChatView,
    ChatListView,
    ChatDetailView,
)

urlpatterns = [
    path('auth/signup/', SignupView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('users/me/', MeView.as_view()),
    path('chat/', ChatView.as_view()),
    path('chats/', ChatListView.as_view()),
    path('chats/<int:pk>/', ChatDetailView.as_view()),
]
