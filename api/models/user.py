from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# Create your models here.

# 1. 유저 생성 도우미 (Manager)
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('이메일은 필수입니다.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # 비밀번호 암호화
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

# 2. 커스텀 유저 모델
class User(AbstractBaseUser, PermissionsMixin):
    # id(PK)는 Django가 자동으로 만들어줍니다.
    
    email = models.EmailField(unique=True, verbose_name='로그인용 이메일')
    name = models.CharField(max_length=30, verbose_name='화면 표시 이름')
    initials = models.CharField(max_length=10, null=True, blank=True, verbose_name='이니셜')
    provider_id = models.CharField(max_length=100, null=True, blank=True, verbose_name='구글 제공 ID')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='가입일')
    last_login_at = models.DateTimeField(auto_now=True, verbose_name='마지막 로그인') # 팀원 요청 스키마 반영

    # Django 필수 필드 (관리자 페이지 접근 등을 위해 필요)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'  # 이제 아이디 대신 이메일로 로그인
    REQUIRED_FIELDS = ['name'] # 슈퍼유저 만들 때 물어볼 필드

    class Meta:
        db_table = 'users'  # 테이블 이름을 'users'로 지정