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
_model = genai.GenerativeModel('gemini-2.5-flash')


SYSTEM_PROMPT = """당신은 멋쟁이사자처럼(SNULION) 동아리의 친근하고 따뜻한 선배 사자입니다.
멋사 동아리 후배들의 다음 주제에 대한 질문에만 답합니다:

- 코딩·웹 개발 (HTML/CSS/JS/TS/React/Django/Python/SQL)
- 동아리 활동·세미나·발표·프로젝트
- 진로·취업·인턴 (특히 개발자·디자이너 관점)
- 학업·시간 관리·학교 생활

위 주제와 무관한 질문(요리·연애·일상 잡담·게임·정치 등)은 정중히 거절하고
"저는 멋사 선배 사자라 동아리·개발·학교 생활 관련 질문에만 답할 수 있어요."
라고 안내한 뒤 위 주제로 자연스럽게 안내하세요.

답변은 친근하고 격려하는 톤으로, 후배에게 이야기하듯이 해주세요.
이모지를 적절히 사용해도 좋습니다 🦁
"""


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

    매 요청마다 멋사 선배 사자 페르소나의 시스템 프롬프트를 함께 보내,
    동아리 주제 외 질문은 정중히 거절하도록 한다. 한 세션에서 이전 N개
    대화를 컨텍스트로 함께 보내 multi-turn 흐름도 흉내낸다.
    """

    CONTEXT_TURNS = 4  # 같은 사용자의 최근 N개 대화를 컨텍스트로 포함

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = serializer.validated_data['prompt']

        # 같은 사용자의 최근 대화를 컨텍스트로 묶음
        recent = (
            ChatLog.objects
            .filter(user=request.user)
            .order_by('-created_at')[:self.CONTEXT_TURNS]
        )
        history_parts = []
        for log in reversed(list(recent)):
            history_parts.append(f"[후배] {log.prompt}")
            history_parts.append(f"[선배 사자] {log.response}")

        composed = SYSTEM_PROMPT + "\n\n"
        if history_parts:
            composed += "이전 대화:\n" + "\n".join(history_parts) + "\n\n"
        composed += f"[후배의 새 질문]\n{prompt}"

        # 동기 Gemini 호출 — 응답까지 worker 점유
        response = _model.generate_content(composed)
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
