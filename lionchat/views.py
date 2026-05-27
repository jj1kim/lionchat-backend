import google.generativeai as genai
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ChatLog
from .serializers import (
    UserSerializer,
    SignupSerializer,
    ChatLogSerializer,
    ChatRequestSerializer,
)


# Gemini 클라이언트는 모듈 import 시 한 번만 초기화한다.
genai.configure(api_key=settings.LLM_API_KEY)
_model = genai.GenerativeModel('gemini-1.5-flash')


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        'user': UserSerializer(user).data,
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_issue_tokens(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)
        if user is None:
            return Response(
                {'detail': '이메일 또는 비밀번호가 잘못되었습니다.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(_issue_tokens(user))


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChatView(APIView):
    """
    선배 사자에게 질문 → Gemini가 답변. 한 사람이 정상적으로 질문하면 정상
    작동한다. 단, 여러 명이 동시에 채팅하면 다른 요청들(가벼운 GET 포함)이
    영향을 받을 수 있다 — 그 이유는 이 함수의 처리 방식을 살펴보면 보인다.
    """

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = serializer.validated_data['prompt']

        # Gemini 호출. 응답이 돌아올 때까지 이 함수에서 대기한다.
        response = _model.generate_content(prompt)
        response_text = response.text

        log = ChatLog.objects.create(
            user=request.user,
            prompt=prompt,
            response=response_text,
        )
        return Response(ChatLogSerializer(log).data, status=status.HTTP_201_CREATED)


class ChatListView(APIView):
    """내 채팅 로그 — 가벼운 쿼리. 정상적으로는 빠르게 응답해야 한다."""

    def get(self, request):
        qs = ChatLog.objects.filter(user=request.user)[:50]
        return Response(ChatLogSerializer(qs, many=True).data)


class ChatDetailView(APIView):
    def get(self, request, pk):
        try:
            log = ChatLog.objects.get(pk=pk, user=request.user)
        except ChatLog.DoesNotExist:
            return Response(
                {'detail': '채팅을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ChatLogSerializer(log).data)
