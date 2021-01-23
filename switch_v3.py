"""
Title: Switch R6 Siege profiles from default (competitive) profile to main
Author: Primus27
"""

# Import packages
from pathlib import Path
from sys import exit
from datetime import datetime
from shutil import copy
import requests
import psutil
from string import ascii_uppercase
import time
from bs4 import BeautifulSoup
import re
import concurrent.futures
import argparse

program_version = "v3.8.2"
# In the event that a backup cannot be made, close program
backup_failsafe = True


def get_args():
    """
    Get arguments from user
    :return: dict containing values defined by user
    """
    # Define argument parser
    parser = argparse.ArgumentParser()
    # Remove existing action groups
    parser._action_groups.pop()

    # Create a required and optional group
    optional = parser.add_argument_group("optional arguments")

    # Define arguments
    optional.add_argument("-d", "--debug", action="store_true",
                          dest="debug_flag",
                          help="Enable debugging")
    optional.add_argument("--version", action="version",
                          version=f"%(prog)s {program_version}",
                          help="Display program version")
    args = parser.parse_args()

    user_args = {
        "debug": args.debug_flag
    }

    return user_args


def close_program():
    """
    Exits program after user confirmation
    """
    print()
    input("[?] Press ENTER to exit")
    exit()


def is_process_active(process_name):
    """
    Function to check whether process is running on PC
    :param process_name: string or list of process i.e. discord.exe
        (case insensitive)
    :return: True / False on whether it is running
    """
    if isinstance(process_name, str):
        return process_name.lower() in [p.name().lower() for p in
                                        psutil.process_iter()]
    elif isinstance(process_name, list):
        # Iterate through process names provided
        for process in process_name:
            if process.lower() in [p.name().lower() for p in
                                   psutil.process_iter()]:
                return True
        # Only reached if non of the names returned True
        return False


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


def get_all_accounts():
    """
    Get all profile paths, regardless of drives
    :return: List of profile paths, including steam (1843) / uplay (635)
             folder at end
    """
    # Get all possible drive letters as paths
    valid_drive_letters = [Path(f"{letter}:\\") for letter in ascii_uppercase]

    # Reduce to all drives found on system
    potential_drive_savegames_path = [letter / "Program Files (x86)\\Ubisoft\\"
                                               "Ubisoft Game Launcher\\"
                                               "savegames" for letter in
                                      valid_drive_letters if letter.exists()]

    # Reduce to ones where Ubisoft savegames folder exists
    drive_savegames_path = [path for path in potential_drive_savegames_path
                            if path.is_dir()]

    # Get all accounts
    accounts_paths = []
    for drive in drive_savegames_path:
        accounts_list = [folder for folder in drive.glob("*")
                         if folder.is_dir()]
        accounts_paths.extend(accounts_list)

    # Append 635 / 1843 depending on whether the folders exist
    uplay_profile_paths = [path / "635" for path in accounts_paths
                           if (path / "635").is_dir()]
    steam_profile_paths = [path / "1843" for path in accounts_paths
                           if (path / "1843").is_dir()]

    profile_paths = uplay_profile_paths.copy()
    profile_paths.extend(steam_profile_paths)

    return profile_paths


def get_request(url, ctx, text=False, user_agent=None):
    """
    Make a request and return response
    :param url: Request URL
    :param ctx: Error context
    :param text: Return only response text
    :param user_agent: Request user agent
    :return: Response data (str): text parameter = True, HTML source
            Response data (tuple): error, (-1, error message)
            Response data (dict): API response
    """

    # Request
    try:
        headers = {'User-Agent': user_agent}
        r = requests.get(url, headers=headers)
        # status_code = r.status_code
        r.raise_for_status()
    except requests.exceptions.HTTPError:  # status_code != 200
        return -1, f"{ctx} Error"
    except requests.exceptions.ConnectionError:
        return -1, f"{ctx} Connection Error"
    except requests.exceptions.Timeout:
        return -1, f"{ctx} Request Timeout"
    except requests.exceptions.TooManyRedirects:
        return -1, f"{ctx} Redirect Error - Max redirections reached"
    except requests.exceptions.RequestException:
        return -1, f"{ctx} Undefined Error"
    else:
        # Return HTML source of request
        if text:
            return r.text
        try:
            # Decode JSON
            json_info = r.json()
        except ValueError:
            # Decoding failed
            # Response is a 204 (No Content) or contains invalid JSON
            return -1, f"{ctx} request successful but can't decode contents!"
        else:
            return json_info


def check_latest_version(url=None):
    """
    Check whether the program version is the latest
    :param url: Custom GH release url (not required)
    """

    def version_format(version: str):
        """
        Convert version number string to tuple
        :param version: Version number (following X.Y.Z...)
        :return: tuple containing version numbers for comparison
        """
        # Remove "v" if it exists
        if version.lower().startswith("v"):
            version = version[1:]
        return tuple(map(int, (version.split("."))))

    # If no url is provided, default one is used.
    if not url:
        url = "https://api.github.com/repos/Primus27/R6-Profile-Switcher/" \
              "releases/latest"
        
    # Request. User agent required for code 200
    github_api_response = get_request(url, "GitHub API",
                                      user_agent="https://github.com/Primus27/"
                                                 "R6-Profile-Switcher")
    
    # Valid response
    if isinstance(github_api_response, dict):
        try:
            release_version = str(github_api_response["tag_name"])

        # Valid response but release doesn't exist
        except KeyError:
            print(f"[-] Unable to check for latest version.")

        else:
            # Current version same or higher than release version
            if version_format(program_version) >= version_format(
                    release_version):
                print("[*] You ARE running the latest version!")

            # Current version lower than release version
            else:
                print(f"[*] You are NOT running the latest version!\t"
                      f"Current: {program_version}, Latest: {release_version}")

                # Link if possible
                regex = r"https:\/\/api\.github\.com\/repos\/(.*)\/" \
                        r"releases\/latest"
                gh_account_repo = re.findall(regex, url)
                account_name = gh_account_repo[0] \
                    if len(gh_account_repo) > 0 else None
                if gh_account_repo:
                    print(f"[*] Link: https://github.com/{account_name}"
                          f"/releases/latest")
    
    # Error response
    elif isinstance(github_api_response, tuple):
        print(f"[-] Unable to check for latest version.\t"
              f"Reason: {github_api_response[1]}!")

    # Unexpected response
    else:
        print(f"[-] Unable to check for latest version.")

    separator(linefeed_pre=True, line=True, linefeed_post=True)


def resolve_uplay_id(uplay_id: str, user_agent=None):
    """
    Utilise all methods to retrieve account information.
    :param uplay_id: Account ID / Name
    :param user_agent: Request user agent
    :return: If successful, tuple: (account id, account name)
            Otherwise, a tuple: (-1, error message)
    """
    # Define local error feedback function
    def error_feedback(account_id, reason, sleep_duration: int = 0.5):
        print(f"[-] Unable to retrieve data for: {account_id}.\t"
              f"Reason: {reason}!")
        time.sleep(sleep_duration)

    """
    Tabstats API
    """

    api_1 = "Tabstats API"
    if user_arguments.get("debug", False):
        print(f"[*] Accessing {api_1} for: {uplay_id}.")

    # API url
    url = f"https://r6.apitab.com/player/{uplay_id}"
    response = get_request(url, "API", user_agent=user_agent)

    # Parse return
    if isinstance(response, tuple):  # Request Error
        if response[0] == -1 and user_arguments.get("debug", False):  # Generic error
            error_feedback(uplay_id, response[1])

    elif isinstance(response, dict):  # Response returned
        try:
            response_status = int(response["status"])
            response_message = f"{str(response['error'])} " \
                               f"{str(response['message'])}"
        except ValueError:
            if user_arguments.get("debug", False):
                error_feedback(uplay_id, "API Request Information Missing")
        else:
            #  Successful response but error message within response
            if response_status != 200:
                if user_arguments.get("debug", False):
                    error_feedback(uplay_id, response_message[:-1])

            # Success
            else:
                player_name = response["player"]["p_name"]
                return uplay_id, player_name
    elif user_arguments.get("debug", False):
        error_feedback(uplay_id, "API Error")

    """
    1. R6 Tracker
    """

    # User feedback
    site_1 = "R6Tracker"
    if user_arguments.get("debug", False):
        print(f"[*] Accessing {site_1} for: {uplay_id}.")

    # Request
    address = f"https://r6.tracker.network/profile/id/{uplay_id}"
    response = get_request(address, site_1, True, user_agent)

    # Parse response
    if isinstance(response, tuple):  # Error
        if response[0] == -1 and user_arguments.get("debug", False):
            error_feedback(uplay_id, response[1])

    elif isinstance(response, str):  # Success
        # Parse HTML
        soup = BeautifulSoup(response, features="html.parser")

        # Name extraction to be used if title cannot extract name
        """
        result = str(soup.find_all("h1", {"class": "trn-profile-header__name"}))
        account_name = re.findall(r"<span>(.*)<\/span>", result)[0]
        """

        # Extract title then name
        result = str(soup.title)
        account_name = re.findall(
            r"R6Tracker - (.*) - [\s{2}]Rainbow Six Siege Player Stats",
            result)
        account_name = account_name[0] if len(account_name) > 0 else None

        if account_name:
            return uplay_id, account_name

    # Error feedback
    if user_arguments.get("debug", False):
        print(f"[-] Unable to access {site_1}")
        time.sleep(0.5)

    """
    2. R6tabs
    """

    site_2 = "R6Tabs"
    if user_arguments.get("debug", False):
        print(f"[*] Accessing {site_2} for: {uplay_id}.")

    address = f"https://r6stats.com/stats/{uplay_id}"
    response = get_request(address, site_2, True, user_agent)

    if isinstance(response, tuple):
        if response[0] == -1 and user_arguments.get("debug", False):
            error_feedback(uplay_id, response[1])

    elif isinstance(response, str):
        soup = BeautifulSoup(response, features="html.parser")

        """
        result = str(soup.find_all("span", {"class": "player-info__player__username"}))
        account_name = re.findall(r"<span class=\"player-info__player__username\">(.*)<\/span>", result)[0]
        """

        result = str(soup.title)
        account_name = re.findall(r"<title>(.*) on PC ::", result)
        account_name = account_name[0] if len(account_name) > 0 else ""

        if account_name:
            return uplay_id, account_name

    if user_arguments.get("debug", False):
        print(f"[-] Unable to access {site_2}")
        time.sleep(0.5)

    """
    3. Tabstats
    """

    site_3 = "Tabstats"
    if user_arguments.get("debug", False):
        print(f"[*] Accessing {site_3} for: {uplay_id}.")

    address = f"https://tabstats.com/siege/player/{uplay_id}"
    response = get_request(address, site_3, True, user_agent)

    if isinstance(response, tuple):
        if response[0] == -1 and user_arguments.get("debug", False):
            error_feedback(uplay_id, response[1])

    elif isinstance(response, str):
        soup = BeautifulSoup(response, features="html.parser")
        result = str(soup.title)
        account_name = re.findall(
            r"<title>(.*) Player Stats on Rainbow Six Siege - R6Tab",
            result)
        account_name = account_name[0] if len(account_name) > 0 else ""

        if account_name:
            return uplay_id, account_name

    if user_arguments.get("debug", False):
        print(f"[-] Unable to access {site_3}")
        time.sleep(0.25)

    # Unsuccessful web scraping
    return -1


def separator(line=False, linefeed_pre=False, linefeed_post=False):
    """
    Function to print elements to distinguish menu sections
    :param line: Bool for a dashed line
    :param linefeed_pre: Bool for a linefeed before the dashed line
    :param linefeed_post: Bool for a linefeed after the dashed line
    """
    if linefeed_pre:
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
    available_choices = ["00", "98", "99"]
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
        if len(menu_output) > 0:
            print(*menu_output, sep="\n")  # Output all account names
        print("98. Check for updates")
        print("99. Exit")
        print(f"[{file_output_icon}] Backup")
        print()

        choice = input("[?] Option:").strip()
        if len(choice) == 1:
            choice = "0" + choice
        separator(linefeed_pre=True, line=True, linefeed_post=True)

        if choice in available_choices:
            # Close program
            if choice == "99":
                exit()

            # Check for latest version, then show menu (recursive)
            elif choice == "98":
                check_latest_version()
                menu_result = main_menu(backup_flag, account_list)
                return menu_result

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

        choice = input("[?] Option:").strip()
        if len(choice) == 1:
            choice = "0" + choice
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
    :param main_path: Profile path
    """
    # Create the backup directory if it does not already exist
    backup_dir = main_path / "backup"
    one_dot_save_path = main_path / "1.save"

    if not backup_dir.is_dir():
        backup_dir.mkdir(parents=True, exist_ok=True)

    # Define default backup file name and path
    timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d %H.%M.%S")
    backup_path = backup_dir / f"profile {timestamp}.bak"

    # Backup
    copy_file(one_dot_save_path, backup_path, ctx="Backup",
              msg="[+] Profile backup created")


def threading_resolve_id(player_id):
    """
    Processing for uplay id resolving so that threading can be used
        alongside multiple user agents
    :param player_id: Uplay ID
    :return: Success = tuple: (player id, player name)
            Fail = int: -1
    """
    # User agents to iterate through if unsuccessful
    user_agent_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36",
        "Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36"
    ]

    # Iterate through user agents
    for i, user_agent in enumerate(user_agent_list):
        if user_arguments.get("debug", False):
            print(f"[*] Attempt {i + 1} for: {player_id}")
        info = resolve_uplay_id(player_id, user_agent)

        # Error obtaining account name - API & site error
        if isinstance(info, int):
            if info == -1 and user_arguments.get("debug", False):
                print(f"[-] Unable to retrieve name for: {player_id}")
        # Success
        else:
            if user_arguments.get("debug", False):
                print(f"[+] Player name retrieved: {player_id}")
            return info
    # All UA used and no success
    return -1


def main():
    """
    Main method
    """
    print(f"R6 Profile Switcher ({program_version})\n"
          " - Developed by Primus27 (github.com/primus27)\n")

    # R6 Siege running
    if is_process_active(["rainbowsix_vulkan.exe", "rainbowsix.exe"]):
        print("[-] R6 Siege already running. Please close Siege to switch "
              "profiles.")
        close_program()

    # Get list of accounts and resolve to ID & name pairs, removing any errors
    # Contains paths
    acc_path_list = get_all_accounts()
    # Contains ID
    acc_id_list = [Path(path).parts[-2] for path in acc_path_list]
    # Prerequisite(s)
    acc_resolve_list_sanitised = []

    if user_arguments.get("debug", False):
        separator(line=True, linefeed_post=True)

    # Threading
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Utilise threading on function using id list as param
        thread_results = executor.map(threading_resolve_id, acc_id_list)

        # Remove -1 results, etc.
        for thread_result in thread_results:
            # Only tuple means success
            if isinstance(thread_result, tuple):
                acc_resolve_list_sanitised.append(thread_result)

    if len(acc_id_list) > 0 and user_arguments.get("debug", False):
        separator(linefeed_pre=True, line=True, linefeed_post=True)

    # Launch menu and capture input
    main_menu_data = main_menu(backup_flag=True,
                               account_list=acc_resolve_list_sanitised)
    active_player_id = main_menu_data[0][0]
    active_player_name = main_menu_data[0][1]
    backup_mode = main_menu_data[1]

    profile_path_list = [path for path in acc_path_list
                         if active_player_id in str(path)]

    try:
        profile_path = profile_path_list[0]
    except IndexError:
        print("[-] Unable to access profile directory - could not establish "
              "profile path.")
        close_program()
    else:
        # Check if path exists
        if not profile_path.is_dir():
            print("[-] Unable to access profile directory - expected path "
                  "does not exist.")
            close_program()

    # Enumerate files and define profile defaults
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
            active_profile = "internal error"

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
        elif active_profile == "internal error":
            print("[-] Unable to make any changes. Current profile could not "
                  "be established")
        # Competitive -> Competitive or Main -> Main
        elif active_profile == profile_select_data:
            print("[*] No changes made")

        if not active_profile == "internal error":
            print(f"[*] Old Profile: {active_profile.title()}\n"
                  f"[*] Current Profile: {profile_select_data.title()}")

    close_program()


if __name__ == '__main__':
    user_arguments = get_args()
    main()
