"""
Title: Switch R6 Siege profiles from default (competitive) profile to main
Author: Primus27
Version: 3.0.0
"""

# Import packages
from pathlib import Path
from sys import exit
from datetime import datetime
from shutil import copy
import requests

program_version = "3.0.0"
# In the event that a backup cannot be made, close program
backup_failsafe = True


def close_program():
    """
    Exits program after user confirmation
    """
    print()
    input("[?] Press ENTER to exit")
    exit()


def rename_file(current_path, new_path):
    """
    Renames one file to another
    :param current_path: Current file path
    :param new_path: Desired file path
    """
    current_path.rename(new_path)


def copy_file(current_path, new_path, ctx, msg):
    """
    Create a copy of a file w/ error handling and user feedback
    :param current_path: File to copy
    :param new_path: Path to copy to
    :param ctx: Context (for error messages). {ctx} Error!
    :param msg: Success message
    """
    try:
        copy(current_path, new_path)
    # Current file path does not exist
    except FileNotFoundError:
        if ctx:
            print(f"[-] {ctx} Error! Profile: '{current_path.name}' "
                  f"not found")
        else:
            print(f"[-] Error! Profile: '{current_path.name}' not found")
        if backup_failsafe:
            close_program()
    # New file path already exists
    except FileExistsError:
        if ctx:
            print(f"[-] {ctx} Error! '{new_path.name}' already exists")
        else:
            print(f"[-] Error! '{new_path.name}' already exists")
        if backup_failsafe:
            close_program()
    else:
        print(msg)


def get_all_accounts(name=False):
    """
    Get a list of all accounts on the system
    :return: If name, list containing account IDs.
             Else, list item containing path objects of account directories
    """
    savegames_path = Path(r'C:\Program Files (x86)\Ubisoft\Ubisoft Game '
                          r'Launcher\savegames')
    if name:
        return [f.name for f in savegames_path.glob("*") if f.is_dir()]
    else:
        return [f for f in savegames_path.glob("*") if f.is_dir()]


def resolve_uplay_info(account, reverse=False):
    """
    API call to fetch account name based on player ID
    :param account: Account ID / Name
    :param reverse: Resolve Name -> ID, instead of ID -> name
    :return: If successful, tuple with account id and account name
             Otherwise, a tuple with -1 and an error message
    """
    if reverse:
        url = f"https://r6.apitab.com/search/uplay/{account}"
    else:
        url = f"https://r6.apitab.com/player/{account}"

    try:
        r = requests.get(url)
        r.raise_for_status()
    except requests.exceptions.HTTPError:  # status_code != 200
        return -1, "API Error!"
    except requests.exceptions.ConnectionError:
        return -1, "Connection Error!"
    except requests.exceptions.Timeout:
        return -1, "Request Timeout!"
    except requests.exceptions.TooManyRedirects:
        return -1, "Redirect Error! Max redirections reached."
    except requests.exceptions.RequestException:
        return -1, "Undefined Error!"
    else:
        try:
            # Decode JSON
            json_info = r.json()
        except ValueError:
            # Decoding failed
            # Response is a 204 (No Content) or contains invalid JSON
            return -1, "API call successful but unable to decode contents."
        else:
            if reverse:
                player_id = next(iter(json_info["players"]))
                return player_id, account
            else:
                player_name = json_info["player"]["p_name"]
                return account, player_name


def separator(line=False, linefeed_pre=False, linefeed_post=False):
    """
    Function to print elements to distinguish menu sections
    :param line: Bool for a dashed line
    :param linefeed_pre: Bool for a linefeed before the dashed line
    :param linefeed_post: Bool for a linefeed after the dashed line
    """
    if linefeed_pre:  # Empty print statement does a carriage return
        print()
    if line:
        print("----------------------------------------------")
    if linefeed_post:
        print()


def main_menu(backup_flag, account_list):
    """
    A function for the main menu
    :param backup_flag: Whether files should be backed up before switching
    :param account_list: List of all resolved player information
    :return: Account to be switched and whether to backup
    """
    file_output_icon = "X" if backup_flag else " "
    # Opposite of file_output_flag if user toggles
    alt_backup_flag = False if backup_flag else True

    # Current user choice
    choice = None
    # Current options available to user (before adding accounts)
    available_choices = ["00", "99"]
    # Feedback for the user
    menu_output = []

    # Iterate over the account list
    for i in range(1, len(account_list) + 1):
        # Double digits
        double_digit_i = "{0:0=2d}".format(i)
        available_choices.append(str(double_digit_i))
        # Format: N. Account Name
        menu_output.append(f"{double_digit_i}. Change "
                           f"{account_list[i-1][1]}")

    while choice not in available_choices:
        print("00. Toggle backup feature")
        print(*menu_output, sep="\n")  # Output all account names
        print("99. Exit")
        print(f"[{file_output_icon}] Backup")
        print()

        choice = input("[?] Option:")
        separator(line=True, linefeed_post=True)

        if choice in available_choices:
            # Close program
            if choice == "99":
                exit()

            # Invert backup flag - recursive
            elif choice == "00":
                menu_result = main_menu(alt_backup_flag, account_list)
                return menu_result

            # Last result must be valid, therefore return info
            else:
                return account_list[int(choice)-1], backup_flag
        else:
            print("[-] Invalid Input\n")


def profile_selection_menu():
    """
    A function for the main menu
    :return: Profile to be switched to (main / comp)
    """
    # Current user choice
    choice = None
    # Current options available to user (before adding accounts)
    available_choices = ["01", "02", "99"]

    while choice not in available_choices:
        print("01. Select 'Main' Profile")
        print("02. Select 'Competitive' Profile")
        print("99. Exit")
        print()

        choice = input("[?] Option:")
        separator(line=True, linefeed_post=True)

        if choice in available_choices:
            # Main profile
            if choice in ("01", "1"):
                return "main"
            # Competitive profile
            elif choice in ("02", "2"):
                return "competitive"
            # '99' Selected. Close program
            else:
                exit()
        else:
            print("[-] Invalid Input\n")


def backup_profile(main_path):
    """
    Create a backup of the active 1.save profile
    """
    # Create the backup directory if it does not already exist
    backup_dir = main_path / "backup"
    if not backup_dir.is_dir():
        backup_dir.mkdir(parents=True, exist_ok=True)

    # Define default backup file name and path
    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d %H.%M.%S")
    backup_path = backup_dir / f"profile {timestamp}.bak"

    # Backup
    copy_file(ubi_profile_path, backup_path, ctx="Backup",
              msg="[+] Profile backup created")


if __name__ == '__main__':
    print(f"R6 Profile Switcher (v{program_version})\n"
          " - Developed by Primus27 (github.com/primus27)\n")

    # Get list of accounts and resolve to ID & name pairs, removing any errors
    acc_id_list = get_all_accounts(name=True)
    acc_resolve_list = [resolve_uplay_info(player_id) for player_id
                        in acc_id_list]
    acc_resolve_list_sanitised = [pair for pair in acc_resolve_list
                                  if pair[0] != -1]

    # Launch menu and capture input
    main_menu_data = main_menu(backup_flag=True,
                               account_list=acc_resolve_list_sanitised)
    active_player_id = main_menu_data[0][0]
    active_player_name = main_menu_data[0][1]
    backup_mode = main_menu_data[1]

    profile_path = Path(r"C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher"
                        r"\savegames") / active_player_id / "635"

    # Check if path exists
    if not profile_path.is_dir():
        print("[-] Unable to access profile directory - expected path does "
              "not exist.")
        close_program()

    # Enumerate files and define profile defaults
    path_files = [f for f in profile_path.glob("*") if f.is_file()]
    ubi_profile_path = profile_path / "1.save"
    main_profile_path = profile_path / "1.save.main.bak"
    comp_profile_path = profile_path / "1.save.competitive.bak"

    print(f"Account: {active_player_name}")

    # 1.save does not exist
    if not ubi_profile_path.is_file():
        print(f"[-] Error - Unable to locate '{ubi_profile_path.name}'. "
              f"File does not exist")
        close_program()

    # Assign main and comp file existence to vars
    main_profile_status = main_profile_path.is_file()
    comp_profile_status = comp_profile_path.is_file()

    # Only the 1.save exists (first time script is run)
    if not main_profile_status and not comp_profile_status:
        copy_file(ubi_profile_path, main_profile_path, ctx="",
                  msg="[+] Only one profile existed - the current profile is: "
                      "Competitive")
        close_program()
    # Script has been run before
    else:
        # Current profile = Main
        if comp_profile_status and not main_profile_status:
            active_profile = "main"
        # Current profile = Competitive
        elif main_profile_status and not comp_profile_status:
            active_profile = "competitive"
        else:
            active_profile = "error"

        # Output active profile
        print(f"Current Profile: {str(active_profile).title()}")
        print()

        # Run menu to allow user to select which profile to change to
        profile_select_data = profile_selection_menu()

        print(f"Account: {active_player_name}")
        print()

        # Backup
        if backup_mode:
            backup_profile(profile_path)

        # Competitive -> Main
        if active_profile == "competitive" and profile_select_data == "main":
            rename_file(ubi_profile_path, comp_profile_path)
            rename_file(main_profile_path, ubi_profile_path)
        # Main -> Competitive
        elif active_profile == "main" and profile_select_data == "competitive":
            rename_file(ubi_profile_path, main_profile_path)
            rename_file(comp_profile_path, ubi_profile_path)
        elif active_profile == "error":
            print("[-] Unable to make any changes. Current profile could not "
                  "be established")
        # Competitive -> Competitive or Main -> Main
        elif active_profile == profile_select_data:
            print("[*] No changes made")

        if not active_profile == "error":
            print(f"[*] Old Profile: {active_profile.title()}\n"
                  f"[*] Current Profile: {profile_select_data.title()}")

    close_program()