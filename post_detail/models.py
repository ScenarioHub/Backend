from django.db import models

# Create your models here.
class Likes(models.Model):
    pk = models.CompositePrimaryKey('user_id', 'scenario_id')
    user = models.ForeignKey('Users', models.DO_NOTHING)
    scenario = models.ForeignKey('Scenarios', models.DO_NOTHING)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'likes'


class Posts(models.Model):
    id = models.BigAutoField(primary_key=True)
    scenario = models.ForeignKey('Scenarios', models.DO_NOTHING)
    uploader = models.ForeignKey('Users', models.DO_NOTHING)
    title = models.CharField(max_length=255)
    temp_desc = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    view_count = models.IntegerField()
    download_count = models.IntegerField()
    like_count = models.IntegerField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'posts'


class ScenarioTags(models.Model):
    pk = models.CompositePrimaryKey('scenario_id', 'tag_id')
    scenario = models.ForeignKey('Scenarios', models.DO_NOTHING)
    tag = models.ForeignKey('Tags', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'scenario_tags'


class Scenarios(models.Model):
    id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey('Users', models.DO_NOTHING)
    video_url = models.TextField()
    file_url = models.CharField(max_length=255)
    file_format = models.CharField(max_length=50)
    file_version = models.CharField(max_length=50)
    file_size = models.BigIntegerField()
    code_snippet = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'scenarios'


class Tags(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=50)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tags'


class Users(models.Model):
    id = models.BigAutoField(primary_key=True)
    pass_hash = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(unique=True, max_length=255)
    name = models.CharField(max_length=100)
    initials = models.CharField(max_length=10)
    provider_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField()
    last_login_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'