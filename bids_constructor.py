import json
from subprocess import Popen, STDOUT, PIPE
import os
import re
from pathlib import Path
import pandas as pd
import fnmatch

from criteria import inclusion_or_exclusion_criteria

def check_path(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error occurs during making directories: {e}")
            return False
    else:
        return False

def bids_tree(folder, mris=['anat', 'dwi']):
    for i in range(len(mris)):
        check_path(folder+mris[i]+'/')

def natural_sort_key(s):
    """
    문자열을 자연 정렬을 위한 키로 변환합니다.
    숫자와 문자를 분리하여 숫자는 정수로 변환하고, 문자는 소문자로 변환합니다.

    Parameters:
        s (str): 정렬할 문자열.

    Returns:
        list: 자연 정렬 키.
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('(\d+)', s)]

def get_folders(search_type='directory', **kwargs):
    """
    지정된 경로에서 폴더 또는 파일을 검색하고 필터링한 후,
    자연 정렬을 적용하여 정렬된 목록과 그 수를 반환합니다.

    Parameters:
        search_type (str): 'directory' 또는 'file' 중 하나.
        **kwargs: 추가 인자.
            - config (dict): 구성 사전. 'data.input_path' 및 'subjects.folders' 키를 포함해야 함.
            - path (str): 검색할 경로. 'config'가 제공되지 않은 경우 사용됨.
            - exclude (str): 제외할 파일의 확장자.

    Returns:
        tuple: (정렬된 검색된 경로 목록, 검색된 항목의 수)
    """
    # 검색 유형 설정
    searches = {'directory': 'directory', 'file': 'file'}
    if search_type not in searches:
        raise ValueError("Invalid search. Expected one of: %s" % list(searches.keys()))

    # 인자 처리
    try:
        config = kwargs['config']
        dicom_path = config["data"]["input_path"]
        subjects = f"*{config['subjects']['folders']}*"
    except KeyError:
        dicom_path = kwargs.get('path', '.')
        subjects = "*"

    exclude = kwargs.get('exclude', "")

    # Path 객체 생성
    p = Path(dicom_path) if dicom_path else Path('.')

    # 디렉토리 또는 파일 목록 가져오기
    if search_type == 'directory':
        entries = [e for e in p.iterdir() if e.is_dir()]
    elif search_type == 'file':
        entries = [e for e in p.iterdir() if e.is_file()]
    else:
        entries = []

    # 제외 패턴 적용
    if exclude:
        exclude_pattern = f"*.{exclude}"
        entries = [e for e in entries if not fnmatch.fnmatch(e.name, exclude_pattern)]

    # subjects 패턴 적용
    if subjects:
        entries = [e for e in entries if fnmatch.fnmatch(e.name, subjects)]

    # 경로를 문자열로 변환
    folders = [str(e) for e in entries]

    # 자연 정렬 적용
    folders_sorted = sorted(folders, key=lambda x: natural_sort_key(Path(x).name))

    return folders_sorted, len(folders_sorted)

def check_ID(json_data, ID):
    wrong_names = json_data["WrongNaming"]
    if ID in wrong_names:
        return wrong_names[ID]
    else:
        return ID
    
def get_nifti_info(nifti_file, json_data):
    path = nifti_file.removesuffix(nifti_file.split('/')[-1])
    name = re.split(r"[.][a-zA-Z]", nifti_file.split('/')[-1])[0]
    i,p,t = name.split('--')
    t = t[:4]+'-'+t[4:6]
    info_nifti = type('', (), {})()
    raw_ID = re.split(r"^0+",re.search(r"\d+", i).group())[-1]
    info_nifti.num_id = check_ID(json_data, raw_ID)
    info_nifti.session = re.findall(r"[A-Z0-9]+",re.split(r"\d{2,}", i)[-1].upper())[0]
    info_nifti.protocol, info_nifti.time = p, t
    if len(info_nifti.num_id) == 1:
        info_nifti.num_id = '0'+info_nifti.num_id
    return path, name, info_nifti

def organize_niftis(niftis, root_subject, root_name, mri):
    # Moving niftis
    for nifti in niftis:
        if nifti.split('.')[-1] == 'gz':
            extension = nifti.split('.')[-2] + '.' + nifti.split('.')[-1]
        else:
            extension = nifti.split('.')[-1]
        full_name = root_subject+mri+'/'+root_name+'.'+extension
        backup = 0
        if os.path.exists(full_name):
            check_path(root_subject+mri+'/backup/')
            full_name = root_subject+mri+'/backup/'+root_name+'_bck-'+str(backup)+'.'+extension
            while os.path.exists(full_name):
                full_name = root_subject + mri + '/backup/' + root_name + '_bck-' + str(backup) + '.' + extension
                backup += 1
        Path(nifti).rename(full_name)

    return backup

def convert_dicom_session(f, config, bids_code):
    dicom_folders, num_dicoms = get_folders(path=f, search_type='directory')
    backup_anat, backup_dwi, backup_func = 0, 0, 0
    
    ##### Convert and process each DICOM session ####
    current_session = {
        "session_id": '', "acq_time": '',"FOLDER": f.split("/")[-1],
        "anat": 0, "dwi": 0, "func": 0,
        "BACKUP-anat": 0, "BACKUP-dwi": 0, "BACKUP-func": 0
    }

    for df in dicom_folders:
        output = Popen(
            f"dcm2niix -o {config['data']['output_path']} -f %n--%p--%t -z {'y' if config['data']['gzip'] else 'n'} {df}", shell=True, stdout=PIPE
        ).stdout.read()
        
        ## Get nifti info - Prepare file naming ##
        niftis, nums = get_folders(path=config['data']['output_path'], search_type='file', exclude='t*')
        if (not niftis == ['']) and (not nums == 0):
            # Succesful DICOM --> NIFTI conversion
            try:
                path, name, info_niftis = get_nifti_info(niftis[0], bids_code)
            except:
                # check if nifitis[0] contains 'localizer' or 'scout'
                if 'localizer' in niftis[0].lower() or 'scout' in niftis[0].lower():
                    # Remove converted files
                    for nf in niftis:
                        os.remove(nf)
                    continue
                else:
                    # throw error
                    raise ValueError(f"Error in converted file {niftis[0]} \n")
            proceed, mri = inclusion_or_exclusion_criteria(niftis, info_niftis, bids_code)
            
            if proceed:
                if bids_code[mri] == 'dwi':
                    try:
                        acq = json.load(open(path+name+'.json', 'r'))["PhaseEncodingDirection"]
                    except:
                        # if no PhaseEncodingDirection in json file, remove converted files
                        for nf in niftis:
                            os.remove(nf)
                        continue
                    file_name = 'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_' + \
                        bids_code[info_niftis.session]["session"] + '_' + \
                        bids_code[acq] + '_' + \
                        bids_code[mri]
                    mri = bids_code[mri]            
                elif bids_code[mri] == 'T1w' or bids_code[mri] == 'T2w':
                    file_name = 'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_' + \
                        bids_code[info_niftis.session]["session"] + '_' + \
                        bids_code[mri]
                    mri = 'anat'
                elif bids_code[mri] == 'bold':
                    # TODO: Add BOLD: func (if necessary)
                    file_name = 'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_' + \
                        bids_code[info_niftis.session]["session"] + '_task-rest_run-' + \
                        str(current_session["func"]) + '_' +\
                        bids_code[mri]
                    mri = 'func'

                ## Create subject BIDS directory ##
                subject_folder = config['data']['output_path'] + \
                    'sub-' + bids_code[info_niftis.session]["ID"] + \
                    info_niftis.num_id + '/' + \
                    bids_code[info_niftis.session]["session"]+ '/' 
                new = check_path(subject_folder)
                if new:
                    bids_tree(subject_folder, mris=config['subjects']['mris'])

                if mri in config['subjects']['mris']:
                    ## Organize nifti files ##   
                    backup = organize_niftis(niftis, subject_folder, file_name, mri)
                    if mri == 'anat':
                        backup_anat = backup
                    elif mri == 'dwi':
                        backup_dwi = backup
                    else:
                        backup_func = backup

                    ## Update intra-session MRI ##
                    current_session[mri] += 1
                else:
                    # Remove converted files
                    for nf in niftis:
                        os.remove(nf)  

            else:
                # Remove converted files
                for nf in niftis:
                    os.remove(nf)    
    
    #### Update Subject Summary ####
    if os.path.exists(config['data']['output_path'] + 'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '/'):
        #   Current Session
        current_session['acq_time'] = info_niftis.time
        current_session['session_id'] = bids_code[info_niftis.session]["session"]
        current_session['BACKUP-anat'] = backup_anat
        current_session['BACKUP-dwi'] = backup_dwi
        current_session['BACKUP-func'] = backup_func
        tsv_name = config['data']['output_path'] + 'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '/' + \
            'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_sessions.tsv'
        try: #   Non-available Summary from previous folders
            subject_summary = pd.read_csv(tsv_name, sep='\t')
        except: # Available Summary from previous folders
            subject_summary = pd.DataFrame(
                columns=['session_id', 'acq_time', 'FOLDER', 'anat', 'dwi', 'func', 'BACKUP-anat', 'BACKUP-dwi', 'BACKUP-func']
            )
        #   Combine earlier sessions with current
        current_session = pd.DataFrame(
            [current_session], columns=['session_id', 'acq_time', 'FOLDER', 'anat', 'dwi', 'func', 'BACKUP-anat', 'BACKUP-dwi', 'BACKUP-func']
        )
        subject_summary = pd.concat([subject_summary, current_session], ignore_index=True)
        subject_summary.to_csv(tsv_name, sep='\t', index=False)

        if subject_summary['anat'][0] < 2:
            # throw error that says that the subject does not has either T1w or T2w
            raise ValueError(f"Subject {bids_code[info_niftis.session]['ID']}{info_niftis.num_id} does not have 2 anatomical images \n")
        
if __name__ == '__main__':
    pass

