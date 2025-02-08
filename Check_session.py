#!/usr/bin/env python3
import argparse
from pathlib import Path


def main(bids_dir):
    bids_dir = Path(bids_dir)
    if not bids_dir.exists():
        print(f"지정한 경로 {bids_dir}가 존재하지 않습니다.")
        return

    # 문제 상황을 저장할 리스트들
    followup2_without_followup1 = []  # ses-followup2는 있는데 ses-followup1이 없는 경우
    followups_without_acute = []  # ses-followup1이나 ses-followup2는 있는데 ses-acute이 없는 경우

    # BIDS에서는 피험자 디렉토리가 "sub-*" 형태로 구성됩니다.
    subject_dirs = sorted([d for d in bids_dir.glob("sub-*") if d.is_dir()])

    for sub in subject_dirs:
        # 각 피험자 폴더 내에 바로 세션 폴더가 존재한다고 가정
        acute_path = sub / "ses-acute"
        followup1_path = sub / "ses-followup1"
        followup2_path = sub / "ses-followup2"

        has_acute = acute_path.exists() and acute_path.is_dir()
        has_followup1 = followup1_path.exists() and followup1_path.is_dir()
        has_followup2 = followup2_path.exists() and followup2_path.is_dir()

        # 1. ses-followup2가 존재하는데 ses-followup1은 없는 경우
        if has_followup2 and not has_followup1:
            followup2_without_followup1.append(sub.name)

        # 2. ses-followup1이나 ses-followup2가 존재하는데 ses-acute이 없는 경우
        if (has_followup1 or has_followup2) and not has_acute:
            followups_without_acute.append(sub.name)

    # 결과 출력
    print("=== ses-followup2는 있으나 ses-followup1이 없는 피험자들 ===")
    if followup2_without_followup1:
        for sub in followup2_without_followup1:
            print(f"  {sub}")
    else:
        print("  해당하는 피험자가 없습니다.")

    print("\n=== ses-followup1 또는 ses-followup2가 있으나 ses-acute이 없는 피험자들 ===")
    if followups_without_acute:
        for sub in followups_without_acute:
            print(f"  {sub}")
    else:
        print("  해당하는 피험자가 없습니다.")


if __name__ == '__main__':
    import yaml

    with open("config.yaml", 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    bids_path = config["data"]["output_path"]
    main(bids_path)
