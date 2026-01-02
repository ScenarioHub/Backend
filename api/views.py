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
