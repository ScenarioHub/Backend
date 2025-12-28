from django.shortcuts import render
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def get_scenario_detail_dummy(request):
    data = {
        'id': '0',
        'title': '어린이 주행 시나리오',
        'createdAt': '2025-12-28 16:01:45',
        'description': '어린이 보호구역에서 다양한 돌발 상황(도로 횡단, 차 사이에서 등장 등)을 포함한 시나리오입니다.',
        'code': '<OpenSCENARIO>...</OpenSCENARIO>',
        'tags': ['어린이', '안전', '센서'],
        'stats': { 'downloads': 0, 'views': 0, 'likes': 0 },
        'file': { 'format': 'OpenSCENARIO', 'version': '1.2', 'size': '100 KB'},
        'uploader': {
            'name': 'user',
            'email': 'email@email.com',
            'initials': 'US',
            'totalScenarios': 12
        }
    }
    return Response(data)

@api_view(['GET'])
def get_scenario_detail(request):

    try:
        cursor = connection.cursor()
        
        postColumns = ['id', 'scenario_id', 'uploader_id', 
                        'title', 'template_desc', 'description', 
                        'view_count', 'download_count', 'like_count', 
                        'created_at']
        strSql = f"select {','.join(postColumns)} from posts where id=1"
        result = cursor.execute(strSql)
        post = cursor.fetchone()
        post = {col: val for col, val in zip(postColumns, post)}

        userColumns = ['id', 'name', 'email', 'initials']
        strSql = f"select {','.join(userColumns)} from users where id={post['uploader_id']}"
        result = cursor.execute(strSql)
        user = cursor.fetchone()
        user = {col: val for col, val in zip(userColumns, user)}

        strSql = f"select count(*) from posts where uploader_id={post['uploader_id']}"
        result = cursor.execute(strSql)
        totalScenarios = cursor.fetchone()[0]

        scenarioColumns = ['id', 'owner_id', 'file_url', 'video_url',
                           'file_format', 'file_version', 'file_size', 'code_snippet',
                           'created_at']
        strSql = f"select {','.join(scenarioColumns)} from scenarios where id={post['scenario_id']}"
        result = cursor.execute(strSql)
        scenario = cursor.fetchone()
        scenario = {col: val for col, val in zip(scenarioColumns, scenario)}

        strSql = f"select tag_id from scenario_tags where scenario_id={post['scenario_id']}"
        result = cursor.execute(strSql)
        tagIds = cursor.fetchall()
        tagIds = [str(tagId[0]) for tagId in tagIds]

        strSql = f"select name from tags where id={' or id='.join(tagIds)}"
        result = cursor.execute(strSql)
        tags = cursor.fetchall()
        tags = [tag[0] for tag in tags]

        connection.commit()
        connection.close()
    except Exception as e:
        connection.rollback()
        status = 404
        data = {
            'status': 404,
            'message': {
                'message': '404 Bad Request'
            }
        }
    else:
        status = 200
        data = {
            'status': 200,
            'message': {
                'id': post['id'],
                'title': post['title'],
                'createdAt': post['created_at'],
                'description': post['description'],
                'code': scenario['code_snippet'],
                'tags': tags,
                'stats': { 'downloads': post['download_count'], 'views': post['view_count'], 'likes': post['like_count'] },
                'file': { 'format': scenario['file_format'], 'version': scenario['file_version'], 'size': scenario['file_size']},
                'uploader': {
                    'name': user['name'],
                    'email': user['email'],
                    'initials': user['initials'],
                    'totalScenarios': totalScenarios
                }
            }
        }
    finally:
        return Response(data, status=status)