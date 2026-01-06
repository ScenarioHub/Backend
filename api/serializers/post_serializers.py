from rest_framework import serializers
from api.models import Post

class PostListSerializer(serializers.ModelSerializer):
    # 1. 명세서(View Column) 이름으로 필드 재정의
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    createdAt = serializers.DateTimeField(source='created_at', format="%Y-%m-%d %H:%M:%S")
    
    # DB컬럼(count) -> API명세(stats) 이름 변경
    stats_downloads = serializers.IntegerField(source='download_count')
    stats_views = serializers.IntegerField(source='view_count')
    stats_likes = serializers.IntegerField(source='like_count')
    
    # 작성자 정보 (User 테이블에서 가져오기)
    uploader_name = serializers.CharField(source='user.name', read_only=True)
    uploader_initials = serializers.CharField(source='user.initials', read_only=True)
    
    # 2. 특수 필드 처리 (태그, 북마크)
    tags = serializers.SerializerMethodField()
    isBookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'description', 'createdAt',
            'stats_downloads', 'stats_views', 'stats_likes',
            'uploader_name', 'uploader_initials',
            'tags', 'isBookmarked'
        ]

    # 목록 조회 시에도 최대 5개까지만 보여주도록 안전장치 추가
    def get_tags(self, obj):
        tag_names = [tag.name for tag in obj.tags.all()[:5]] # 최대 5개로 슬라이싱
        return ",".join(tag_names)

    # 북마크 여부 (기본 False 설정, 추후 로직 구현)
    def get_isBookmarked(self, obj):
        return False
    
    # 게시글 저장/수정 시 태그 개수를 검증하는 함수
    def validate_tags(self, value):
        if len(value) > 5:
            raise serializers.ValidationError("태그는 최대 5개까지만 등록할 수 있습니다.")
        return value