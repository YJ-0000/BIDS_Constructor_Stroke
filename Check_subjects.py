#!/usr/bin/env python3
import argparse
import csv
import re
import ntpath
from pathlib import Path


def check_folder_name(subject_number, expected_code, folder_name):
    """
    folder_name 내에 subject number와 expected_code가
    (숫자와 session label 사이에 '-' 또는 '_'가 있을 수도 없을 수도 있는) 패턴으로 포함되어 있는지 검사합니다.

    예) subject_number = "81", expected_code = "C"
         → folder_name에 "81C", "81_C", "81-C" 등이 있어야 함.
    """
    # (?i) : 대소문자 구분 없이 검사
    # (?:^|[^0-9]) : subject number 앞에 숫자가 아닌 문자(또는 문자열 시작)가 와야 함
    # 0* : 앞에 붙은 0들을 허용
    # [-_]? : subject number와 expected_code 사이에 '-'나 '_'가 0개 또는 1개 있을 수 있음
    pattern = re.compile(rf"(?i)(?:^|[^0-9])0*{subject_number}[-_]?{expected_code}")
    return bool(pattern.search(folder_name))


def main(bids_dir):
    bids_dir = Path(bids_dir)
    if not bids_dir.exists():
        print(f"지정한 BIDS 디렉토리 {bids_dir}가 존재하지 않습니다.")
        return

    # session_id와 기대하는 폴더 내 session label의 대응 관계
    session_code_map = {
        "ses-acute": "A",
        "ses-followup1": "C",
        "ses-followup2": "C2"
    }

    # 결과를 저장할 리스트들
    success_msgs = []
    error_msgs = []

    # 각 subject 폴더는 "sub-PAT*" 형태라고 가정합니다.
    subject_dirs = sorted([d for d in bids_dir.glob("sub-PAT*") if d.is_dir()])

    for sub_dir in subject_dirs:
        # subject 폴더 이름 예: sub-PAT24 → label: "PAT24"
        subject_label = sub_dir.name[len("sub-"):]
        # 정규표현식으로 "PAT" 뒤에 오는 숫자만 추출 (대소문자 무관)
        m = re.search(r'PAT(\d+)', subject_label, re.IGNORECASE)
        if not m:
            error_msgs.append(f"{sub_dir.name}: 폴더 이름이 'PAT<number>' 패턴에 맞지 않습니다.")
            continue
        subject_number = m.group(1)

        # subject 폴더 내에 *sessions.tsv 파일을 찾습니다.
        tsv_files = list(sub_dir.glob("*sessions.tsv"))
        if not tsv_files:
            error_msgs.append(f"{sub_dir.name}: sessions.tsv 파일을 찾을 수 없습니다.")
            continue
        # 만약 여러 개라면 첫 번째 파일을 사용 (필요에 따라 수정)
        tsv_file = tsv_files[0]

        try:
            with tsv_file.open(newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    session_id = row.get("session_id", "").strip()
                    folder_path = row.get("FOLDER", "").strip()

                    # 우리가 체크할 세션만 처리 (나머지는 건너뛰기)
                    if session_id not in session_code_map:
                        continue

                    # (a) tsv에 기록된 session이 실제 subject 폴더 내에 존재하는지 확인
                    session_folder = sub_dir / session_id
                    if not (session_folder.exists() and session_folder.is_dir()):
                        error_msgs.append(
                            f"{sub_dir.name} - {session_id}: 해당 session 폴더 ({session_folder})가 존재하지 않습니다."
                        )
                    else:
                        success_msgs.append(
                            f"{sub_dir.name} - {session_id}: session 폴더 존재 확인."
                        )

                    # (b) FOLDER 컬럼이 비어있는지 확인
                    if not folder_path:
                        error_msgs.append(f"{sub_dir.name} - {session_id}: FOLDER 컬럼이 비어 있습니다.")
                        continue

                    # FOLDER 컬럼은 원본 경로 (예: "E:\CNDA_Stroke_raw_data\FCS81C")
                    # ntpath.basename을 사용하면 Windows 스타일 경로에서도 마지막 폴더명을 추출할 수 있음
                    folder_basename = ntpath.basename(folder_path)

                    expected_code = session_code_map[session_id]
                    if check_folder_name(subject_number, expected_code, folder_basename):
                        success_msgs.append(
                            f"{sub_dir.name} - {session_id}: '{folder_basename}' → OK"
                        )
                    else:
                        error_msgs.append(
                            f"{sub_dir.name} - {session_id}: '{folder_basename}' 에서 subject number '{subject_number}'와 "
                            f"기대하는 session label '{expected_code}'가 올바르게 포함되어 있지 않습니다."
                        )
        except Exception as e:
            error_msgs.append(f"{sub_dir.name}: {tsv_file.name} 파일 처리 중 오류 발생 → {e}")

    # 결과 출력
    print("==== 검증 결과 (성공한 항목) ====")
    if success_msgs:
        for msg in success_msgs:
            print(msg)
    else:
        print("성공한 항목이 없습니다.")

    print("\n==== 검증 결과 (오류 항목) ====")
    if error_msgs:
        for msg in error_msgs:
            print(msg)
    else:
        print("오류가 없습니다.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="각 sub-* 폴더 내의 sessions.tsv 파일을 읽어, FOLDER 컬럼에 subject number와 session label(A, C, C2)이 "
                    "올바르게 포함되어 있는지 검증하는 프로그램입니다.\n"
                    "주의: 폴더 이름에서는 subject number와 session label 사이에 언더바('_')나 대시('-')가 있을 수 있고, "
                    "또 폴더 이름 뒤에 촬영 날짜 등이 붙을 수 있으며 대소문자 구분 없이 체크합니다."
    )
    parser.add_argument("bids_dir", help="BIDS 데이터셋 최상위 디렉토리 경로")
    import yaml

    with open("config.yaml", 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    bids_path = config["data"]["output_path"]
    main(bids_path)
