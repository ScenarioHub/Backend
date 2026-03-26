import os
import uuid
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.core.files import uploadedfile

import chardet
from lxml import etree as ET

def build_filename(user_id, return_ts=False):
    created_at = timezone.localtime(timezone.now())
    ts = created_at.strftime("%Y%m%d_%H%M%S")
    uid = str(user_id)
    file_name = f"{ts}_{uid}"

    return (file_name, created_at.isoformat()) if return_ts else file_name

def get_base_scenario_path(map_name):
    return settings.DATA_ROOT / f"xosc_examples/{map_name}.xosc"

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

def save_scenario_file(file, file_name, map_path=None):
    scenario_dir = settings.DATA_ROOT / 'scenario'
    scenario_path = scenario_dir / (file_name + ".xosc")
    output_file = open(scenario_path, "wb")

    if isinstance(file, uploadedfile.InMemoryUploadedFile):
        for chunk in file.chunks():
            output_file.write(chunk)
    if isinstance(file, bytes):
        output_file.write(file)

    output_file.close()

    if map_path:
        tree = ET.parse(scenario_path)
        root = tree.getroot()
        
        map_tag = root.find(".//RoadNetwork/LogicFile")
        map_tag.set("filepath", map_path)
        tree.write(scenario_path, pretty_print=True, encoding="utf-8", xml_declaration=True)

    print(f"Scenario file saved at {scenario_path.resolve()}")

    return str(scenario_path)

def save_video_file(scenario_file, file_name):
    old_pwd = os.getcwd()

    os.chdir(settings.DATA_ROOT.parent / "tmp")
    log_dir = settings.DATA_ROOT / 'esmini_log'
    log_path = log_dir / (file_name + ".log")
    run_esmini = f"export DISPLAY=:98 && esmini --window 0 0 800 400 --osc {scenario_file} --logfile_path {log_path} --capture_screen --fixed_timestep 0.03"
    ret_code = subprocess.run(run_esmini, shell=True, executable='/bin/bash')
    if ret_code.returncode != 0:
        raise Exception("esmini error")

    video_dir = settings.DATA_ROOT / 'video'
    video_path = video_dir / (file_name + ".mp4")
    run_ffmpeg = f"export DISPLAY=:98 && ffmpeg -f image2 -framerate 33.3 -i screen_shot_%5d.tga -c:v libx264 -vf format=yuv420p -crf 20 {video_path}"
    ret_code = subprocess.run(run_ffmpeg, shell=True, executable='/bin/bash')
    if ret_code.returncode != 0:
        raise Exception("ffmpeg error")
    
    for f in Path(".").glob("screen_shot_*.tga"):
        f.unlink()

    os.chdir(old_pwd)
    print(f"Video file saved at {video_path.resolve()}")
    
    return str(video_path)

def run_esmini_simulation(xosc_path, dat_path):
    """esmini를 headless 모드로 실행하여 .dat 파일 생성."""
    run_esmini = f"{settings.ESMINI_EXE} --headless --osc {xosc_path} --fixed_timestep 0.033 --record {dat_path}"
    ret_code = subprocess.run(run_esmini, shell=True, cwd=settings.TMP_DIR, capture_output=True)
    if ret_code.returncode != 0:
        raise Exception("esmini error")


def dat2csv(dat_path):
    """dat2csv를 실행하여 .csv 파일 생성. 반환: csv 파일 경로."""
    dat_path = Path(dat_path).resolve()
    run_dat2csv = f"{settings.DAT2CSV_EXE} {dat_path} --extended"
    ret_code = subprocess.run(run_dat2csv, shell=True, cwd=dat_path.parent, capture_output=True)
    if ret_code.returncode != 0:
        raise Exception("dat2csv error")

    csv_path = dat_path.with_suffix(".csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"dat2csv 출력 파일을 찾을 수 없습니다: {csv_path}")
    return csv_path

def csv2dict(csv_path):
    """
    esmini dat2csv로 생성된 CSV 파일을 파싱하여 dict로 반환한다.

    Returns:
        dict: {
            "0.0": {"0": {"x": ..., "y": ..., "z": ..., "h": ...}, "1": {...}},
            "0.033": {...},
            ...
        }
    """
    result = {}
    valid_count = 0

    with open(csv_path, 'rb') as raw_f:
        raw_data = raw_f.read(10000)
        detected = chardet.detect(raw_data)
        file_encoding = detected['encoding'] if detected['encoding'] else 'utf-8'

    with open(csv_path, 'r', encoding=file_encoding, errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            clean_line = line.replace(',', ' ')
            parts = clean_line.strip().split()

            if len(parts) < 7:
                continue

            try:
                time_val = float(parts[0])
                obj_id = str(int(parts[1]))
                x = float(parts[3])
                y = float(parts[4])
                z = float(parts[5])
                h = float(parts[6])

                time_key = str(time_val)

                if time_key not in result:
                    result[time_key] = {}

                result[time_key][obj_id] = {
                    "x": x,
                    "y": y,
                    "z": z,
                    "h": h
                }
                valid_count += 1

            except ValueError:
                continue

    return result

def xodr2glb(xodr_path, output_glb_path):
    if os.path.exists(output_glb_path):
        return
    
    unique_id = uuid.uuid4().hex[:8]
    
    work_dir = settings.TMP_DIR / f"work_{unique_id}"
    work_dir.mkdir(parents=True, exist_ok=True)

    default_osgb = work_dir / "generated_road.osgb"
    temp_osgb = work_dir / f"generated_road_{unique_id}.osgb"
    temp_obj = work_dir / f"temp_model_{unique_id}.obj"
    
    run_odrviewer = f"{settings.ODRVIEWER_EXE} --headless --window 60 60 800 600 --odr {xodr_path} --save_generated_model --duration 0"
    ret_code = subprocess.run(run_odrviewer, shell=True, cwd=work_dir)
    if ret_code.returncode != 0:
        raise Exception("odrviewer error")
    os.rename(default_osgb, temp_osgb)
    print(f"OSGB file saved at {temp_osgb}")

    run_osgbconv = f"{settings.OSGCONV_EXE} -O OutputTextureFiles {temp_osgb} {temp_obj}"
    ret_code = subprocess.run(run_osgbconv, shell=True, cwd=work_dir)
    if ret_code.returncode != 0:
        raise Exception("osgconv error")
    print(f"OBJ file saved at {temp_obj}")

    run_obj2gltf = f"npx obj2gltf -i {temp_obj} -o {output_glb_path}"
    ret_code = subprocess.run(run_obj2gltf, shell=True, cwd=work_dir)
    if ret_code.returncode != 0:
        raise Exception("obj2gltf error")
    print(f"GLB file saved at {output_glb_path}")

    temp_mtl = temp_obj.with_suffix(".mtl")
    for temp_file in [temp_osgb, temp_obj, temp_mtl]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    os.rmdir(work_dir)
