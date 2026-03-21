import os
import glob
import subprocess

from django.conf import settings

def update_glb_resources():
    print("Updating glb resources")

    esmini_models_dir = settings.DATA_ROOT / "models"
    glb_dir = settings.DATA_ROOT / "models_glb"

    if not os.path.exists(glb_dir):
        os.makedirs(glb_dir)

    osgb_files = glob.glob(os.path.join(esmini_models_dir, "*.osgb"))

    if not osgb_files:
        print(f"[Error] No .osgb files found in {esmini_models_dir}.")
        return

    print(f"Total {len(osgb_files)} models found. Converting...")

    for osgb_path in osgb_files:
        base_name = os.path.splitext(os.path.basename(osgb_path))[0]

        temp_obj = glb_dir / f"{base_name}.obj"
        final_glb = glb_dir / f"{base_name}.glb"

        if os.path.exists(final_glb):
            continue

        print(f"\n--- Converting [{base_name}] ---")

        # 텍스처(색상)를 제대로 뽑기 위해 -O OutputTextureFiles 옵션을 추가합니다.
        run_osgb = f"{settings.OSGCONV_EXE} -O OutputTextureFiles {osgb_path} {temp_obj}"
        ret_code = subprocess.run(run_osgb, shell=True, cwd=settings.TMP_DIR)
        if ret_code.returncode != 0:
            print("osgconv error")
            continue

        run_obj2gltf = f"npx obj2gltf -i {temp_obj} -o {final_glb}"
        ret_code = subprocess.run(run_obj2gltf, shell=True, cwd=settings.TMP_DIR)
        if ret_code.returncode != 0:
            print("obj2gltf error")
            continue

        print(f"GLB file saved at {final_glb}")

        temp_mtl = temp_obj.with_suffix(".mtl")
        for temp_file in [temp_obj, temp_mtl]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    print("\nAll vehicle conversion tasks completed!")