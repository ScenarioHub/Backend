from django.shortcuts import render

from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView        # JWT 라이브러리가 제공하는 로그인 뷰 / pip install djangorestframework djangorestframework-simplejwt
from api.serializers import RegisterSerializer, LoginSerializer     # 회원가입 시리얼라이저 임포트
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model

User = get_user_model()
# 회원가입 뷰
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()               # User 모델 전체 쿼리셋
    serializer_class = RegisterSerializer       # 앞서 만든 시리얼라이저 사용
    permission_classes = [AllowAny]             # 누구나 가입할 수 있어야 하므로 권한을 열어둡니다.

# 로그인 뷰 추가
class CustomLoginView(TokenObtainPairView):
    serializer_class = LoginSerializer