import os

from django.db import connection
from django.utils import timezone

from utils.scenario.generator import generator
from utils.utils import build_filename, get_base_scenario_path, parse_scenario_snippet, save_video_file

def thread_start_generation(job_uuid):
    try:
        cursor = connection.cursor()
        cursor.execute(
            "select user_id, description, map_id, status from generation_jobs where job_uuid=%s for update",
            [job_uuid]
        )
        row = cursor.fetchone()

        if not row:
            return

        user_id, description, map_id, status = row

        if status == "generating" or status == "recording":
            print(f"process_generation_job: job already running {job_uuid}")
            return

        cursor.execute("update generation_jobs set status=%s where job_uuid=%s", ['generating', job_uuid])

        cursor.execute("select map_name from maps where id=%s", [map_id])
        map_name = cursor.fetchone()[0]

        base_scenario_path = get_base_scenario_path(map_name)
        file_name = build_filename(user_id)
        xosc_path = generator(description, file_name, base_scenario_path)
        code_snippet = parse_scenario_snippet(xosc_path)
        file_size = os.path.getsize(xosc_path)

        cursor.execute("update generation_jobs set status=%s where job_uuid=%s", ['recording', job_uuid])
        video_path = save_video_file(xosc_path, file_name)

        scenario_columns = ['owner_id', 'file_url', 'video_url', 'file_format', 'file_version', 'file_size', 'code_snippet', 'created_at']
        values = [user_id, xosc_path, video_path, 'OpenSCENARIO', '1.2', file_size, code_snippet, timezone.now()]
        placeholders = ','.join(['%s'] * len(values))
        insert_sql = f"INSERT INTO scenarios({','.join(scenario_columns)}) VALUES({placeholders})"

        cursor.execute(insert_sql, values)
        scenario_id = cursor.lastrowid

        cursor.execute(
            "update generation_jobs set scenario_id=%s, status=%s where job_uuid=%s",
            [scenario_id, 'done', job_uuid]
        )
        
        cursor.close()
    except Exception:
        import traceback
        print(traceback.format_exc())

        cursor.execute(
            "update generation_jobs set status=%s where job_uuid=%s",
            ['failed',job_uuid]
        )
    return