"""
Title: Switch R6 Siege profiles from default (competitive) profile to main
Author: Primus27
Version: 2.0
"""

# Import packages
from pathlib import Path
from sys import exit
from datetime import datetime
from shutil import copy
import re

""" User defaults """

# Enable backup of current profile before switching profile
backup = True
# In the event that a backup cannot be made, close program
backup_failsafe = True
# Define profile path
profile_path = Path(r'C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\savegames\{profile}\635')


def close_program():
    """
    Exits program after user confirmation
    """
    input("[*] Press any key to exit")
    exit()


def rename_file(current_path, new_path):
    """
    Renames one file to another
    :param current_path: Current file path
    :param new_path: Desired file path
    """
    current_path.rename(new_path)


re_pattern = r'[a-zA-Z]{1}:\\[a-zA-Z0-9\(\)\ ]+\\Ubisoft\\Ubisoft Game Launcher\\savegames\\[0-9a-fA-F\-]+\\[0-9]{3}'
# Check if directory doesn't exist
if not profile_path.is_dir():
    print("[-] Profile path does not exist")
    close_program()
# If it does exist, check if it matches the expected path pattern
elif not re.match(re_pattern, str(profile_path)):
    print("[-] Path does not seem to point to an R6 profile folder")
    close_program()

# Enumerate files and define profile defaults
path_files = [f for f in profile_path.glob("*") if f.is_file()]
ubi_profile_path = profile_path / "1.save"
main_profile_path = profile_path / "1.save.main.bak"
comp_profile_path = profile_path / "1.save.competitive.bak"

# Check whether the main profile (1.save) exists
if ubi_profile_path in path_files:
    if backup:
        # Create the directory backup if it does not already exist
        backup_dir = profile_path / "backup"
        if not backup_dir.is_dir():
            backup_dir.mkdir(parents=True, exist_ok=True)

        # Define default backup file name
        timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d %H.%M.%S")
        backup_path = backup_dir / f"profile {timestamp}.bak"

        # Backup file
        try:
            copy(ubi_profile_path, backup_path)
        except FileNotFoundError:
            print("[-] Error backing up profile! Profile not found")
            if backup_failsafe:
                close_program()
        except FileExistsError:
            print("[-] Error backing up profile! File already exists")
            if backup_failsafe:
                close_program()
        else:
            print("[+] Profile backup created")

    # Current profile = Competitive -> Switch to Main profile
    if main_profile_path in path_files \
            and comp_profile_path not in path_files:
        rename_file(ubi_profile_path, comp_profile_path)
        rename_file(main_profile_path, ubi_profile_path)
        print("Old Profile: Competitive\nCurrent Profile: Main")

    # Current profile = Main -> Switch to Competitive profile
    elif comp_profile_path in path_files \
            and main_profile_path not in path_files:
        rename_file(ubi_profile_path, main_profile_path)
        rename_file(comp_profile_path, ubi_profile_path)
        print("Old Profile: Main\nCurrent Profile: Competitive")

    # Only the 1.save exists (first time script is run)
    elif main_profile_path not in path_files \
            and comp_profile_path not in path_files:
        try:
            copy(ubi_profile_path, main_profile_path)
        except FileNotFoundError:
            print(f"[-] Error! Profile: '{ubi_profile_path.name}' not found")
        except FileExistsError:
            print(f"[-] Error! '{main_profile_path.name}' already exists")
        else:
            print("[+] Only one profile existed - the current profile is: "
                  "Competitive")

    # This catch all should never happen
    else:
        print(f"[-] Unexpected Error!")
else:
    print(f"[-] Error - Unable to locate '{ubi_profile_path.name}'. File does "
          f"not exist")

close_program()
