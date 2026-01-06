#from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password', 'name', 'initials']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data['name'],
            initials=validated_data.get('initials', '')
        )
        return user
    
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class LoginSerializer(TokenObtainPairSerializer):
    # 부모 클래스의 설정을 무시하고 강제로 'email' 필드를 사용하게 합니다.
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # 필요하다면 토큰 안에 이메일이나 이름을 추가로 넣을 수 있습니다.
        token['email'] = user.email
        token['name'] = user.name
        return token