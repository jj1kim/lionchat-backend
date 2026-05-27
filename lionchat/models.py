from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra):
        if not email:
            raise ValueError('email이 필요합니다.')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, name, password, **extra)


class User(AbstractUser):
    """LionChat 사용자 — 선배 사자에게 질문할 수 있는 동아리원."""
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=50)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    def __str__(self):
        return f'{self.name} ({self.email})'


class ChatLog(models.Model):
    """한 prompt → 한 응답 쌍의 채팅 기록."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='chat_logs'
    )
    prompt = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.name}: {self.prompt[:30]}...'
