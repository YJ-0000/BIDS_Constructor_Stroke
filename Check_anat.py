#!/usr/bin/env python3
import argparse
from pathlib import Path
import json


def main(bids_dir):
    bids_dir = Path(bids_dir)
    if not bids_dir.exists():
        print(f"지정한 경로({bids_dir})가 존재하지 않습니다.")
        return

    # 결과를 저장할 리스트들
    complete = []  # T1w와 T2w 모두 존재하는 경우
    incomplete = []  # 둘 중 하나만 존재하는 경우 (어느 것이 누락되었는지 표시)
    missing_anat = []  # anat 폴더 자체가 없거나 T1w/T2w 파일이 하나도 없는 경우

    # subjects: "sub-*" 패턴의 폴더를 찾습니다.
    subject_dirs = sorted([d for d in bids_dir.glob("sub-*") if d.is_dir()])

    for sub in subject_dirs:
        # 세션 폴더가 있는지 확인 (BIDS에서는 optional)
        session_dirs = sorted([d for d in sub.glob("ses-*") if d.is_dir()])
        if session_dirs:  # 세션 폴더가 있는 경우
            for ses in session_dirs:
                anat_dir = ses / "anat"
                if anat_dir.exists() and anat_dir.is_dir():
                    # anat 폴더 내의 T1w, T2w 파일 검색 (파일명이 T1w 혹은 T2w를 포함)
                    t1_files = list(anat_dir.glob("*T1w*"))
                    t2_files = list(anat_dir.glob("*T2w*"))
                    if t1_files and t2_files:
                        complete.append((sub.name, ses.name))
                    elif t1_files or t2_files:
                        # 어느 것이 누락되었는지 판별
                        missing = "T2w" if t1_files and not t2_files else "T1w"
                        incomplete.append((sub.name, ses.name, missing))
                    else:
                        missing_anat.append((sub.name, ses.name))
                else:
                    missing_anat.append((sub.name, ses.name))
        else:  # 세션 폴더가 없는 경우 → anat 폴더는 subject 폴더 하위에 존재
            anat_dir = sub / "anat"
            if anat_dir.exists() and anat_dir.is_dir():
                t1_files = list(anat_dir.glob("*T1w*"))
                t2_files = list(anat_dir.glob("*T2w*"))
                if t1_files and t2_files:
                    complete.append((sub.name, "N/A"))
                elif t1_files or t2_files:
                    missing = "T2w" if t1_files and not t2_files else "T1w"
                    incomplete.append((sub.name, "N/A", missing))
                else:
                    missing_anat.append((sub.name, "N/A"))
            else:
                missing_anat.append((sub.name, "N/A"))

    # 결과 report 출력
    print("=== T1w와 T2w가 모두 존재하는 피험자/세션 ===")
    for sub, ses in complete:
        print(f"Subject: {sub}, Session: {ses}")

    print("\n=== 일부만 존재하는 피험자/세션 (누락된 시퀀스 표시) ===")
    for sub, ses, missing in incomplete:
        print(f"Subject: {sub}, Session: {ses}, Missing: {missing}")

    print("\n=== anat 폴더가 없거나 T1w/T2w 파일이 없는 피험자/세션 ===")
    for sub, ses in missing_anat:
        print(f"Subject: {sub}, Session: {ses}")


if __name__ == '__main__':
    # parser = argparse.ArgumentParser(
    #     description="BIDS 데이터셋 내 anat 폴더에서 T1w 및 T2w 이미지를 검색하고 report하는 프로그램"
    # )
    # parser.add_argument("bids_dir", help="BIDS 데이터셋 디렉토리 경로")
    # args = parser.parse_args()
    # main(args.bids_dir)
    # read from config.yaml file
    import yaml

    with open("config.yaml", 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    bids_path = config["data"]["output_path"]

    main(bids_path)
