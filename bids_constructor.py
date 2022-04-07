import json
from subprocess import Popen, STDOUT, PIPE
import os
import yaml
import logging
from tqdm import tqdm
import re
from pathlib import Path

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
    # Use path or config
    try:
        config = kwargs['config']
        dicom_path, subjects = config["data"]["input_path"], f"*{config['subjects']['folders']}*"
    except:
        dicom_path, subjects = kwargs['path'], "*"
    # Search
    output = Popen(
        f"find {dicom_path if len(dicom_path)>0 else '.'} -maxdepth 1 -mindepth 1 -type {searches[search_type]} -name '{subjects}'", shell=True, stdout=PIPE
    ).stdout.read()
    folders = str(output).removeprefix('b\'').removesuffix('\'').removesuffix('\\n').split('\\n')
    return folders, len(folders)

def get_nifti_info(nifti_file):
    path = nifti_file.removesuffix(nifti_file.split('/')[-1])
    #name = (nifti_file.split('/')[-1]).split('.')[0]
    name = re.split(r"[.][a-zA-Z]", nifti_file.split('/')[-1])[0]
    print(name)
    i,p,t = name.split('--')
    t = t[:4]+'-'+t[4:6]
    info_nifti = type('', (), {})()
    info_nifti.num_id = re.split(r"^0+",re.search(r"\d+", i).group())[-1]
    info_nifti.session = re.findall(r"[A-Z0-9]+",re.split(r"\d{2,}", i)[-1].upper())[0]
    info_nifti.protocol, info_nifti.time = p, t
    if len(info_nifti.num_id) == 1:
        info_nifti.num_id = '0'+info_nifti.num_id
    return path, name, info_nifti

def organize_niftis(niftis, root_subject, root_name, mri):
    # Moving niftis
    for nifti in niftis:
        full_name = root_subject+mri+'/'+root_name+'.'+nifti.split('.')[-1]
        if os.path.exists(full_name):
            check_path(root_subject+mri+'/'+'backup/')
            full_name = root_subject+mri+'/backup/'+root_name+'_bck.'+nifti.split('.')[-1]
        Path(nifti).rename(full_name)

def update_summary(summary, main_key, current_session, c_time, ses, f, base):
    ### Update main_key: SUBJECT ID ###
    if main_key not in summary:
        # Create new entry
        summary[main_key] = {
            "originals": [f.split("/")[-1]], 
        }
        summary[main_key].update(base)
    else:
        # Update original folder name
        summary[main_key]['originals'].append(f.split("/")[-1])

    ### Update the session ###
    temp_ses = dict(summary[main_key][current_session])
    times = list(temp_ses['time'])
    for k in temp_ses:
        if k == 'time':
            times.append(c_time)
        else:
            temp_ses[k] += ses[k]
    summary[main_key][current_session] = dict(temp_ses)
    summary[main_key][current_session]['time'] = times
    return summary

if __name__ == '__main__':
    # Preliminaires
    logging.basicConfig(level=logging.INFO)
    with open("config.yaml", 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    bids_code = json.load(open("bids_code.json", 'r'))

    # Main Paths    
    check_path(config["data"]["output_path"])

    # Get folders
    logging.info(f" Getting folders from {config['data']['input_path']}")
    folders, number = get_folders(config=config)
    logging.info(f" Processing {number} folder(s) ...")

    # Write summary
    base = {
        "ses-acute": {"anat": 0, "dwi": 0, "fMRI": 0, "time": []},
        "ses-followup": {"anat": 0, "dwi": 0, "fMRI": 0, "time": []},
        "ses-followup-2": {"anat": 0, "dwi": 0, "fMRI": 0, "time": []},
        "ses-control": {"anat": 0, "dwi": 0, "fMRI": 0, "time": []},
        "ses-control-2": {"anat": 0, "dwi": 0, "fMRI": 0, "time": []}
    }
    summary = {
    }

    # Loop over folders
    for i, f in tqdm(enumerate(folders), total=number):
        dicom_folders, num_dicoms = get_folders(path=f)

        # Convert and process each DICOM session
        ses = {"anat": 0, "dwi": 0, "fMRI": 0}
        for df in dicom_folders:
            output = Popen(
                f"dcm2niix -o {config['data']['output_path']} -f %n--%p--%t -z {'y' if config['data']['gzip'] else 'n'} {df}", shell=True, stdout=PIPE
            ).stdout.read()

            # Get nifti info
            niftis, nums = get_folders(path=config['data']['output_path'], search_type='file')
            path, name, info_niftis = get_nifti_info(niftis[0])
            mri =  re.match(r"dti|MPR|MPRAGE|BOLD", info_niftis.protocol).group()
            if bids_code[mri] == 'dwi':
                acq = json.load(open(path+name+'.json', 'r'))["PhaseEncodingDirection"]
                file_name = bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_' + \
                    bids_code[info_niftis.session]["session"] + '_' + \
                    bids_code[acq] + '_' + \
                    bids_code[mri]
                mri = bids_code[mri]
                
            elif bids_code[mri] == 'T1w':
                file_name = bids_code[info_niftis.session]["ID"] + info_niftis.num_id + '_' + \
                    bids_code[info_niftis.session]["session"] + '_' + \
                    bids_code[mri]
                mri = 'anat'
            elif bids_code[mri] == 'T1w':
                # TODO: Add BOLD: fMRI (if necessary)
                pass

            # Update intra-session MRI
            ses[mri] += 1
            
            # Create subject BIDS directory
            subject_folder = config['data']['output_path'] + \
                bids_code[info_niftis.session]["ID"] + \
                info_niftis.num_id + '/' + \
                bids_code[info_niftis.session]["session"]+ '/' 
            new = check_path(subject_folder)
            if new:
                bids_tree(subject_folder, mris=config['subjects']['mris'])

            # Organize nifti files    
            organize_niftis(niftis, subject_folder, file_name, mri)
        
        # Update Data information
        main_key =  bids_code[info_niftis.session]["ID"] + info_niftis.num_id
        current_session = bids_code[info_niftis.session]["session"]
        c_time = info_niftis.time
        summary = update_summary(summary, main_key, current_session, c_time, ses, f, base)

    # Write name transcription
    with open(f"{config['data']['output_path']}ID_translation.json", 'w') as fp:
        json.dump(summary, fp, indent=3)
    #renames = pd.DataFrame(renames).to_csv(f"{config['data']['output_path']}ID_transcription.tsv", sep = "\t", index = False)

