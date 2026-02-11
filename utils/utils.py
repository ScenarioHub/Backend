import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils import timezone

def build_filename(user_id, return_ts=False):
    created_at = timezone.localtime(timezone.now())
    ts = created_at.strftime("%Y%m%d_%H%M%S")
    uid = str(user_id)      #dummy
    file_name = f"{ts}_{uid}"

    return (file_name, created_at.isoformat()) if return_ts else file_name

def parse_scenario_snippet(file_path, line_limit=50): # 50줄 파싱
    code_snippet = ""
    if not (file_path and os.path.exists(file_path)):
        return "파일을 찾을 수 없습니다."

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = []
            for _ in range(line_limit):
                line = f.readline()
                if not line: break
                lines.append(line)
            code_snippet = "".join(lines)
    except Exception:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_snippet = f.read()
        except Exception as e:
            code_snippet = f"내용을 읽는 중 오류가 발생했습니다: {str(e)}"
    
    return code_snippet

def save_scenario_file(upload_file, file_name):
    scenario_dir = settings.DATA_ROOT / 'scenario'
    scenario_path = scenario_dir / (file_name + ".xosc")

    with open(scenario_path, "wb") as f:
        for chunk in upload_file.chunks():
            f.write(chunk)
    print(f"Scenario file saved at {scenario_path.resolve()}")

    return str(scenario_path)

def save_video_file(scenario_file, file_name):
    old_pwd = os.getcwd()

    os.chdir(settings.DATA_ROOT.parent / "tmp")
    print(os.getcwd())
    log_dir = settings.DATA_ROOT / 'esmini_log'
    log_path = log_dir / (file_name + ".log")
    run_esmini = f"export DISPLAY=:98 && esmini --window 0 0 800 400 --osc {scenario_file} --logfile_path {log_path} --capture_screen --fixed_timestep 1"
    ret_code = subprocess.run(run_esmini, shell=True, executable='/bin/bash')
    if ret_code.returncode != 0:
        return Exception("esmini error")

    video_dir = settings.DATA_ROOT / 'video'
    video_path = video_dir / (file_name + ".mp4")
    run_ffmpeg = f"export DISPLAY=:98 && ffmpeg -f image2 -framerate 120 -i screen_shot_%5d.tga -c:v libx264 -vf format=yuv420p -crf 20 {video_path}"
    ret_code = subprocess.run(run_ffmpeg, shell=True, executable='/bin/bash')
    if ret_code.returncode != 0:
        return Exception("ffmpeg error")
    
    for f in Path(".").glob("screen_shot_*.tga"):
        f.unlink()

    os.chdir(old_pwd)
    print(f"Video file saved at {video_path.resolve()}")
    
    return str(video_path)