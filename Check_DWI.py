#!/usr/bin/env python3
import argparse
from pathlib import Path


def check_required_files(folder):
    """
    지정한 폴더 내에 .bvec, .bval, .nii.gz 파일이 각각 하나라도 있는지 확인합니다.
    누락된 파일 유형을 리스트로 반환합니다.
    """
    missing = []
    # 확인할 파일 확장자 및 glob 패턴
    file_patterns = {
        "bvec": "*.bvec",
        "bval": "*.bval",
        "nii.gz": "*.nii.gz"
    }
    for file_type, pattern in file_patterns.items():
        if not list(folder.glob(pattern)):
            missing.append(file_type)
    return missing


def process_folder(subject_label, session_label, base_folder):
    """
    base_folder(세션 폴더 또는 subject 폴더 내)의 dwi 및 BACKUP-dwi 폴더를 확인하여
    누락된 항목(폴더 없음 또는 파일 누락)이 있으면 error 메시지를 리스트로 반환합니다.
    """
    errors = []

    # dwi 폴더 확인
    dwi_folder = base_folder / "dwi"
    if not dwi_folder.exists():
        errors.append(f"{subject_label} - {session_label}: dwi 폴더가 존재하지 않습니다.")
    else:
        missing = check_required_files(dwi_folder)
        if missing:
            errors.append(f"{subject_label} - {session_label} dwi 폴더에서 누락된 파일: {', '.join(missing)}")

    # BACKUP-dwi 폴더 확인
    # backup_folder = base_folder / "BACKUP-dwi"
    # if not backup_folder.exists():
    #     errors.append(f"{subject_label} - {session_label}: BACKUP-dwi 폴더가 존재하지 않습니다.")
    # else:
    #     missing = check_required_files(backup_folder)
    #     if missing:
    #         errors.append(f"{subject_label} - {session_label} BACKUP-dwi 폴더에서 누락된 파일: {', '.join(missing)}")

    return errors


def main(bids_dir):
    bids_dir = Path(bids_dir)
    if not bids_dir.exists():
        print(f"지정한 BIDS 디렉토리 {bids_dir}가 존재하지 않습니다.")
        return

    errors_total = []

    # subject 폴더는 "sub-*" 패턴
    subject_dirs = sorted([d for d in bids_dir.glob("sub-*") if d.is_dir()])
    if not subject_dirs:
        print("subject 폴더(sub-*)를 찾을 수 없습니다.")
        return

    for sub in subject_dirs:
        subject_label = sub.name
        # session 폴더가 있으면 각 session 폴더 내의 dwi 및 BACKUP-dwi 폴더를 확인
        session_dirs = sorted([d for d in sub.glob("ses-*") if d.is_dir()])
        if session_dirs:
            for ses in session_dirs:
                session_label = ses.name
                errors = process_folder(subject_label, session_label, ses)
                errors_total.extend(errors)
        else:
            # session 폴더가 없는 경우, subject 폴더 자체 내에서 dwi 및 BACKUP-dwi 폴더 확인
            errors = process_folder(subject_label, "N/A", sub)
            errors_total.extend(errors)

    # 통과되지 않은 항목들만 출력
    print("==== 통과되지 않은 (실패한) 항목들 ====")
    if errors_total:
        for err in errors_total:
            print(err)
    else:
        print("모든 항목이 통과되었습니다.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="각 subject/세션의 dwi 및 BACKUP-dwi 폴더 내에 bvec, bval, nii.gz 파일들이 모두 존재하는지 확인하고, "
                    "문제가 있는 항목(실패한 항목)만 출력합니다."
    )
    parser.add_argument("bids_dir", help="BIDS 데이터셋 최상위 디렉토리 경로")
    import yaml

    with open("config.yaml", 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    bids_path = config["data"]["output_path"]
    main(bids_path)
