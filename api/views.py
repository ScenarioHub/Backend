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
def scenario_detail(request, id):
    try:
        cursor = connection.cursor()
        columns = ['id', 'title', 'description', 'createdAt', 'code',
                   'file_format', 'file_version', 'file_size',
                   'stats_downloads', 'stats_views', 'stats_likes',
                   'uploader_name', 'uploader_initials', 'uploader_email', 'uploader_total_scenarios',
                   'tags']
        strSql = f"select {','.join(columns)} from view_scenario_details where id={id}"
        cursor.execute(strSql)
        view = cursor.fetchone()
        view = {col: val for col, val in zip(columns, view)}
        view['tags'] =[tag.strip() for tag in view['tags'].split(',')]
        
        connection.commit()
        connection.close()
        
        message = {
            'id': view['id'],
            'title': view['title'],
            'createdAt': view['createdAt'],
            'description': view['description'],
            'code': view['code'],
            'tags': view['tags'],
            'stats': { 'downloads': view['stats_downloads'], 'views': view['stats_views'], 'likes': view['stats_likes'] },
            'file': { 'format': view['file_format'], 'version': view['file_version'], 'size': view['file_size']},
            'uploader': {
                'name': view['uploader_name'],
                'initials': view['uploader_initials'],
                'email': view['uploader_email'],
                'totalScenarios': view['uploader_total_scenarios']
            }
        }
    except Exception as e:
        connection.rollback()
        status = 404
        message = '404 Not Found'
    else:
        status = 200
    finally:
        return Response(
            data={
                'status': status,
                'message': message
            },
            status=status
        )
