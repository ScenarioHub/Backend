from django.db import models
from django.conf import settings 

# 태그 테이블
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'tags'

    def __str__(self):
        return self.name

# 게시글 테이블
class Post(models.Model):
    # 작성자 (Users 테이블과 연결)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # 통계 정보
    view_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 태그 연결
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)

    class Meta:
        db_table = 'posts'