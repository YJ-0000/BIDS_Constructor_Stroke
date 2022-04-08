import json
import yaml
import logging
from tqdm import tqdm

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
    for i, f in tqdm(enumerate(folders), total=number):
        convert_dicom_session(f, config, bids_code)

