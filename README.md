# BIDS_Constructor
## Original Note
Code to build BIDS structure from any (in theory) DICOM structured dataset

Better instruction to follow. For now, be sure to introduce the info necessary to convert and organize the files in these two files:

- bids_code.json

- criteria.py

---

## Modified Note (Windows Compatibility)

This code has been modified to enable file conversion and organization on Windows.

We have added additional checking code to ensure that the files are converted and organized correctly:
- **Check_subjects.py**: Checks whether the subjects have been correctly converted and organized.
- **Check_sessions.py**: Checks for any missing sessions.
- **Check_anat.py**: Verifies that all necessary anatomical files (T1w and T2w) are present.
- **Check_DWI.py**: (Currently not in use.)
