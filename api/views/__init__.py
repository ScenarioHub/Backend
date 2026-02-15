from .auth_view import register, login, refresh_token, logout
from .post_myscenario_view import my_scenario

from .map_view import get_map_list, get_map_preview
from .video_view import stream_video, stream_video_board
from .xosc_download import download_file, download_file_board

from .generation_view import start_generating_scenario, get_generating_state
from .generate_to_upload_view import get_generated_data, upload_from_generation

from .stats_view import get_service_stats
from .post_list_view import post_list
from .upload_view import upload_post
from .post_detail_view import post_detail
from .post_delete import delete_post
from .likes_view import toggle_like