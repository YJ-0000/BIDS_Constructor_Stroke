import json
import re
import nibabel as nib

def inclusion_or_exclusion_criteria(files, info_files, bids_code):
    """
    Define here any criteria you want to consider in order for the BIDS conversion to proceed or not.

    Inputs
    --------
    files (list): Contains the files outputted by the dcm2niix software
    info_files (object): Contains information on the batch of files converted - Obtained from the function get_nifti_info
    bids_code (dict): Contains information about the coding keys to transform to bids

    Outputs
    --------
    proceed (bool): Encoding whether criteria is met for continuation of the conversion
    mri (str, None): Encodes the type of mri protocol found. 
                     If None means that no protocol is of interest
    """
    
    # We search for the protocols present in the bids_code.json
    mri = re.match(f'({bids_code["PROTOCOLS"]})', info_files.protocol) 
    
    if not mri == None:
        mri = mri.group()

        ##############################################################
        # CONSIDER ADDING ANY OTHER CRITERIA PRESENT IN YOUR DATASET #
        ##############################################################
        
        if bids_code[mri] == 'dwi': # DIFFUSION ACQUISITIONS
            series = json.load(open([f for f in files if '.json' in f][0], 'r'))["SeriesDescription"]
            if ('FA' in series) or ('ADC' in series) or ('TENSOR' in series) or ('EXP' in series):
                proceed = False
            else:
                proceed = True
        
        elif bids_code[mri] == 'bold':  # FUNCTIONAL ACQUISITIONS 
            data = nib.load([f for f in files if '.nii' in f][0]).get_fdata()
            if data.shape[-1] >= 100:
                proceed = True
            else:
                proceed = False
        
        else: # ANATOMICAL ACQUISITIONS (T1w or T2w)
            proceed = True
    else:
        proceed = False
    
    return proceed, mri