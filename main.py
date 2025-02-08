import json
import yaml
import logging
from tqdm import tqdm
import os

from bids_constructor import check_path, get_folders, convert_dicom_session

if __name__ == '__main__':
    ####### Preliminaires ######
    logging.basicConfig(level=logging.INFO)
    with open("config.yaml", 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    bids_code = json.load(open("bids_code.json", 'r'))
    

    ####### Main Paths ######
    check_path(config["data"]["output_path"])

    ####### Get folders ######
    logging.info(f" Getting folders from {config['data']['input_path']}")
    folders, number = get_folders(config=config)
    logging.info(f" Processing {number} folder(s) ...")
        
    ####### Loop over folders ######
    if config["data"]["log"]:
        with open("Logs.txt", 'w') as log_f:
            log_f.write("LIST OF FOLDERS WHO COULD NOT BE CONVERTED PROBABLY DUE TO NAME CODING ERROR \n")
            log_f.write("============================================================================ \n")
    for i, f in tqdm(enumerate(folders), total=number):
        try:
            ## Try Running converting without error ##
            convert_dicom_session(f, config, bids_code)
        except Exception as ee:
            print(f"Error in folder {f} \n")
            print(ee)
            errors, _ = get_folders(path=config["data"]["output_path"], exclude='txt', search_type='file')
            if config["data"]["log"]:
                ## Report Error ##
                with open("Logs.txt", 'a') as log_f:
                    log_f.write(f"Folder: {f} \n")
                    for e in errors:
                        log_f.write(f"\t \t{e} \n")
                        ## Remove Problematic Files ##
                        if os.path.exists(e):
                            os.remove(e)
            else:
                pass
    
    ## Move Logs ##
    if config["data"]["log"]:
        import shutil
        shutil.copyfile("./Logs.txt", config["data"]["output_path"]+"Logs.txt")