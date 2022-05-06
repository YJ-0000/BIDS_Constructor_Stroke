import json
from subprocess import Popen, STDOUT, PIPE
import os
import re
from pathlib import Path

import pandas as pd

def check_path(path):
    if not os.path.isdir(path):
        os.system("mkdir -p {}".format(path))
        return True
    else: 
        return False

def bids_tree(folder, mris=['anat', 'dwi']):
    for i in range(len(mris)):
        check_path(folder+mris[i]+'/')

def get_folders(search_type='directory',**kwargs):
    # Folders or files (not both)
    searches = {'directory': 'd', 'file': 'f'}
    if search_type not in searches.keys():
        raise ValueError("Invalid search. Expected one of: %s" % searches.keys())

    # Use provided arguments
    try:
        config = kwargs['config']
        dicom_path, subjects = config["data"]["input_path"], f"*{config['subjects']['folders']}*"
    except:
        dicom_path, subjects = kwargs['path'], "*"
    try:
        exclude = kwargs['exclude']
    except:
        exclude = ""

    # Search
    output = Popen(
        f"find {dicom_path if len(dicom_path)>0 else '.'} -maxdepth 1 -mindepth 1 -type {searches[search_type]} ! -name '*.{exclude}' -name '{subjects}'", 
        shell=True, stdout=PIPE
    ).stdout.read()
    folders = str(output).removeprefix('b\'').removesuffix('\'').removesuffix('\\n').split('\\n')
    return folders, len(folders)

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
            full_name = root_subject+mri+'/backup/'+root_name+'_bck.'+extension
            backup = 1
        Path(nifti).rename(full_name)
    return backup

def convert_dicom_session(f, config, bids_code):
    dicom_folders, num_dicoms = get_folders(path=f, search_type='directory')

    ##### Convert and process each DICOM session ####
    current_session = {"session_id": '', "acq_time": '',"FOLDER": f.split("/")[-1],  "anat": 0, "dwi": 0, "fMRI": 0, "BACKUP": 0}
    for df in dicom_folders:
        output = Popen(
            f"dcm2niix -o {config['data']['output_path']} -f %n--%p--%t -z {'y' if config['data']['gzip'] else 'n'} {df}", shell=True, stdout=PIPE
        ).stdout.read()

        ## Get nifti info - Prepare file naming ##
        niftis, nums = get_folders(path=config['data']['output_path'], search_type='file', exclude='tsv')
        path, name, info_niftis = get_nifti_info(niftis[0], bids_code)
        mri =  re.match(r"dti|MPR|MPRAGE|BOLD|t1_mprage", info_niftis.protocol).group()
        if bids_code[mri] == 'dwi':
            acq = json.load(open(path+name+'.json', 'r'))["PhaseEncodingDirection"]
            file_name = 'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_' + \
                bids_code[info_niftis.session]["session"] + '_' + \
                bids_code[acq] + '_' + \
                bids_code[mri]
            mri = bids_code[mri]            
        elif bids_code[mri] == 'T1w':
            file_name = 'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_' + \
                bids_code[info_niftis.session]["session"] + '_' + \
                bids_code[mri]
            mri = 'anat'
        elif bids_code[mri] == 'bold':
            # TODO: Add BOLD: fMRI (if necessary)
            file_name = 'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_' + \
                bids_code[info_niftis.session]["session"] + '_task-rest_run-' + \
                str(current_session["fMRI"]) + '_' +\
                bids_code[mri]
            mri = 'fMRI'

        ## Create subject BIDS directory ##
        subject_folder = config['data']['output_path'] + \
            'sub-' + bids_code[info_niftis.session]["ID"] + \
            info_niftis.num_id + '/' + \
            bids_code[info_niftis.session]["session"]+ '/' 
        new = check_path(subject_folder)
        if new:
            bids_tree(subject_folder, mris=config['subjects']['mris'])

        ## Organize nifti files ##   
        backup = organize_niftis(niftis, subject_folder, file_name, mri)

        ## Update intra-session MRI ##
        current_session[mri] += 1
    
    #### Update Subject Summary ####
    #   Current Session
    current_session['acq_time'] = info_niftis.time
    current_session['session_id'] = bids_code[info_niftis.session]["session"]
    current_session['BACKUP'] = backup
    tsv_name = config['data']['output_path'] + 'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '/' + \
        'sub-' + bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_sessions.tsv'
    try: #   Non-available Summary from previous folders
        subject_summary = pd.read_csv(tsv_name, sep='\t')
    except: # Available Summary from previous folders
        subject_summary = pd.DataFrame(columns=['session_id', 'acq_time', 'FOLDER', 'anat', 'dwi', 'fMRI', 'BACKUP'])
    #   Combine earlier sessions with current
    current_session = pd.DataFrame([current_session], columns=['session_id', 'acq_time', 'FOLDER', 'anat', 'dwi', 'fMRI', 'BACKUP'])
    subject_summary = pd.concat([subject_summary, current_session], ignore_index=True)
    subject_summary.to_csv(tsv_name, sep='\t', index=False)
        
if __name__ == '__main__':
    pass

