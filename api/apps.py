import os
import sys
from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        if not os.environ.get('RUN_MAIN'):
            if 'runserver' in sys.argv:
                from utils.update import update_glb_resources
                update_glb_resources()
