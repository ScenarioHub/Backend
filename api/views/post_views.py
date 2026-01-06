from django.shortcuts import render
from rest_framework import generics
from api.models import Post
from api.serializers import PostListSerializer
from rest_framework.permissions import AllowAny

# Create your views here.

class PostListView(generics.ListAPIView):
    # 최적화된 쿼리셋 (Select Related 사용)
    queryset = Post.objects.select_related('user').prefetch_related('tags').all().order_by('-created_at')
    serializer_class = PostListSerializer
    permission_classes = [AllowAny] # 로그인 없이 조회 가능