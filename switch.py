"""
Title: Switch R6 Siege profiles from default (competitive) profile to main
Author: Primus27
"""

# Import packages
from pathlib import Path
from datetime import datetime
from shutil import copy
import requests
import psutil
from string import ascii_uppercase
import time
from bs4 import BeautifulSoup
import re
import concurrent.futures

program_version = "BETA v4.1.0"


class ProfileFunctions:
    """
    Class containing all functions of profile switcher
    """
    def __init__(self, logger):
        """
        Initialiser
        :param logger: Parent logger
        """
        self.logger = logger
        self.program_version = program_version

    @staticmethod
    def is_process_active(process_name):
        """
        Function to check whether process is running on PC
        :param process_name: string or list of process i.e. discord.exe (case insensitive)
        :return: True / False on whether process is running
        """
        if isinstance(process_name, str):
            return process_name.lower() in [p.name().lower() for p in psutil.process_iter()]
        elif isinstance(process_name, list):
            # Iterate through process names provided
            for process in process_name:
                if process.lower() in [p.name().lower() for p in psutil.process_iter()]:
                    return True
            # Only reached if non of the names returned True
            return False

    @staticmethod
    def rename_file(current_path, new_path):
        """
        Renames one file to another
        :param current_path: Current file path
        :param new_path: Desired file path
        """
        current_path.rename(new_path)

    def copy_file(self, current_path, new_path, ctx, msg):
        """
        Create a copy of a file w/ error handling and user feedback
        :param current_path: File to copy
        :param new_path: Path to copy to
        :param ctx: Context (for error messages). {ctx} Error!
        :param msg: Success message
        :return: Success: None
                 Fail: -1
        """
        try:
            copy(current_path, new_path)
        # Current file path does not exist
        except FileNotFoundError:
            if ctx:
                self.logger.error(f"[-] {ctx} Error! Profile: '{current_path.name}' not found")
                return -1
            else:
                self.logger.error(f"[-] Error! Profile: '{current_path.name}' not found")
                return -1
        # New file path already exists
        except FileExistsError:
            if ctx:
                self.logger.error(f"[-] {ctx} Error! '{new_path.name}' already exists")
                return -1
            else:
                self.logger.error(f"[-] Error! '{new_path.name}' already exists")
                return -1
        else:
            self.logger.info(msg)

    @staticmethod
    def get_all_accounts():
        """
        Get all profile paths, regardless of drives
        :return: List of profile paths, including steam (1843) / uplay (635) folder at end
        """
        # Get all possible drive letters as paths
        valid_drive_letters = [Path(f"{letter}:\\") for letter in ascii_uppercase]

        # Reduce to all drives found on system
        potential_drive_savegames_path = [
            letter / "Program Files (x86)\\Ubisoft\\Ubisoft Game Launcher\\savegames" for letter in
            valid_drive_letters if letter.exists()]

        # Reduce to ones where Ubisoft savegames folder exists
        drive_savegames_path = [path for path in potential_drive_savegames_path if path.is_dir()]

        # Get all accounts
        accounts_paths = []
        for drive in drive_savegames_path:
            accounts_list = [folder for folder in drive.glob("*") if folder.is_dir()]
            accounts_paths.extend(accounts_list)

        # Append 635 / 1843 depending on whether the folders exist
        uplay_profile_paths = [path / "635" for path in accounts_paths if (path / "635").is_dir()]
        steam_profile_paths = [path / "1843" for path in accounts_paths if (path / "1843").is_dir()]

        profile_paths = uplay_profile_paths.copy()
        profile_paths.extend(steam_profile_paths)

        return profile_paths

    @staticmethod
    def get_request(url, ctx, text=False, user_agent=None, timeout=5):
        """
        Make a request and return response
        :param url: Request URL
        :param ctx: Error context
        :param text: Return only response text
        :param user_agent: Request user agent
        :param timeout: Seconds until request timeout
        :return: Response data (str): text parameter = True, HTML source
                Response data (tuple): error, (-1, error message)
                Response data (dict): API response
        """
        # Request
        try:
            headers = {'User-Agent': user_agent}
            r = requests.get(url, headers=headers, timeout=timeout)
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

    def check_latest_version(self, url=None):
        """
        Check whether the program version is the latest
        :param url: Custom GH release url (not required)
        :return: Error: -1
                Success: None
        """
        def version_format(version: str):
            """
            Convert version number string to tuple
            :param version: Version number (following X.Y.Z...)
            :return: tuple containing version numbers for comparison
            """
            # Remove "prefix" if it exists
            if regex_result := re.findall(r"[a-zA-Z ]+ ?([0-9.]+)", version):
                version = regex_result[0]
            return tuple(map(int, (version.split("."))))

        # If no url is provided, default one is used.
        if not url:
            url = "https://api.github.com/repos/Primus27/R6-Profile-Switcher/releases/latest"

        # Request. User agent required for code 200
        github_api_response = self.get_request(
            url, "GitHub API", user_agent="https://github.com/Primus27/R6-Profile-Switcher",
            timeout=10)

        # Valid response
        if isinstance(github_api_response, dict):
            try:
                release_version = str(github_api_response["tag_name"])
            # Valid response but release doesn't exist
            except KeyError:
                return -1, None
            else:
                # Current version same or higher than release version
                if version_format(self.program_version) >= version_format(release_version):
                    return 1, release_version
                # Current version lower than release version
                else:
                    return 0, release_version
        # Error response
        else:
            return -1

    def resolve_uplay_id(self, uplay_id: str, user_agent=None):
        """
        Utilise all methods to retrieve account information.
        :param uplay_id: Account ID / Name
        :param user_agent: Request user agent
        :return: If successful, tuple: (account name, account id)
                Otherwise: -1
        """
        # Define local error feedback function
        def error_feedback(account_id, reason, sleep_duration: int = 0.25):
            self.logger.debug(f"[-] Unable to retrieve data for: {account_id}.\n"
                              f"\tReason: {reason}!")
            time.sleep(sleep_duration)

        """
        Tabstats API
        """

        api_1 = "Tabstats API"
        self.logger.debug(f"[*] Accessing {api_1} for: {uplay_id}.")

        # API url
        url = f"https://r6.apitab.com/player/{uplay_id}"
        response = self.get_request(url, "API", user_agent=user_agent, timeout=2)

        # Parse return
        if isinstance(response, tuple):  # Request Error
            if response[0] == -1:  # Generic error
                error_feedback(uplay_id, response[1])

        elif isinstance(response, dict):  # Response returned
            try:
                response_status = int(response["status"])
                response_message = f"{str(response['error'])} {str(response['message'])}"
            except ValueError:
                error_feedback(uplay_id, "API Request Information Missing")
            else:
                #  Successful response but error message within response
                if response_status != 200:
                    error_feedback(uplay_id, response_message[:-1])

                # Success
                else:
                    account_name = response["player"]["p_name"]
                    return account_name, uplay_id

        """
        1. R6 Tracker
        """

        # User feedback
        site_1 = "R6Tracker"
        self.logger.debug(f"[*] Accessing {site_1} for: {uplay_id}.")

        # Request
        address = f"https://r6.tracker.network/profile/id/{uplay_id}"
        response = self.get_request(address, site_1, True, user_agent)

        # Parse response
        if isinstance(response, tuple):  # Error
            if response[0] == -1:
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
                r"R6Tracker - (.*) - [\s{2}]Rainbow Six Siege Player Stats", result)
            account_name = account_name[0] if len(account_name) > 0 else None

            if account_name:
                return account_name, uplay_id

        # Error feedback
        self.logger.debug(f"[-] Unable to access {site_1}")
        time.sleep(0.25)

        """
        2. R6tabs
        """

        site_2 = "R6Tabs"
        self.logger.debug(f"[*] Accessing {site_2} for: {uplay_id}.")

        address = f"https://r6stats.com/stats/{uplay_id}"
        response = self.get_request(address, site_2, True, user_agent)

        if isinstance(response, tuple):
            if response[0] == -1:
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
                return account_name, uplay_id

        self.logger.debug(f"[-] Unable to access {site_2}")
        time.sleep(0.25)

        """
        3. Tabstats
        """

        site_3 = "Tabstats"
        self.logger.debug(f"[*] Accessing {site_3} for: {uplay_id}.")

        address = f"https://tabstats.com/siege/player/{uplay_id}"
        response = self.get_request(address, site_3, True, user_agent)

        if isinstance(response, tuple):
            if response[0] == -1:
                error_feedback(uplay_id, response[1])

        elif isinstance(response, str):
            soup = BeautifulSoup(response, features="html.parser")
            result = str(soup.title)
            account_name = re.findall(
                r"<title>(.*) Player Stats on Rainbow Six Siege - R6Tab", result)
            account_name = account_name[0] if len(account_name) > 0 else ""

            if account_name:
                return account_name, uplay_id

        self.logger.debug(f"[-] Unable to access {site_3}")
        time.sleep(0.25)

        # Unsuccessful
        return -1

    def separator(self, line=False, linefeed_pre=False, linefeed_post=False,
                  use_all=False):
        """
        Function to output elements to distinguish menu sections
        :param line: Bool for a dashed line
        :param linefeed_pre: Bool for a linefeed before the dashed line
        :param linefeed_post: Bool for a linefeed after the dashed line
        :param use_all: Use all elements
        """
        if linefeed_pre or use_all:
            self.logger.fatal("")
        if line or use_all:
            self.logger.fatal("----------------------------------------------")
        if linefeed_post or use_all:
            self.logger.fatal("")

    def backup_profile(self, main_path):
        """
        Create a backup of the active 1.save profile
        :param main_path: Profile path
        :return: Success: None
                Fail: -1
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
        result = self.copy_file(one_dot_save_path, backup_path, ctx="Backup",
                                msg="[+] Profile backup created")
        if result == -1:
            return -1

    def threading_resolve_id(self, account_path):
        """
        Processing for uplay id resolving so that threading can be used alongside
        multiple user agents
        :param account_path: Uplay Account Path
        :return: Success: (player name, player id, account path)
                Fail: -1
        """
        # User agents to iterate through if unsuccessful
        user_agent_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36"
        ]

        account_id = Path(account_path).parts[-2]

        # Iterate through user agents
        for i, user_agent in enumerate(user_agent_list):
            self.logger.debug(f"[*] Attempt {i + 1} for: {account_id}")
            info = self.resolve_uplay_id(account_id, user_agent)

            # Error obtaining account name - API & site error
            if isinstance(info, int):
                if info == -1:
                    self.logger.error(f"[-] Unable to retrieve name for: {account_id}")
            # Success
            elif len(info) == 2:
                self.logger.info(f"[+] Player name retrieved: {account_id}")
                info_with_path = (*info, account_path)
                return info_with_path
        # All UA used and no success
        return -1

    def s1_find_account(self):
        """
        Find R6 accounts on system and resolve into usernames
        :return: List containing tuples: [(name, id, path), (name, id, path), ...]
        """
        # Get list of accounts and resolve to ID & name pairs, removing any errors
        # Contains paths
        acc_path_list = self.get_all_accounts()
        # Prerequisite(s)
        acc_resolve_list_sanitised = []

        self.logger.info("[*] Locating and resolving accounts:")
        self.separator(line=True, linefeed_post=True)

        # Threading
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Utilise threading on function using id list as param
            thread_results = executor.map(self.threading_resolve_id, acc_path_list)

            # Remove -1 results, etc.
            for thread_result in thread_results:
                # Only tuple means success, int == fail
                if isinstance(thread_result, tuple):
                    acc_resolve_list_sanitised.append(thread_result)

        if len(acc_path_list) > 0:
            self.separator(use_all=True)

        return acc_resolve_list_sanitised

    def s4_activate_profile(self, profile_path, profile_name, profile_selection, backup_flag):
        """
        Step 4 - Activate Profile
        :param profile_path: Path: Path of profile to be changed
        :param profile_name: Str: Ubisoft account name
        :param profile_selection: Str: Selected profile (competitive/main)
        :param backup_flag: Bool: Whether to backup profile beforehand
        :return: Success: None
                Fail: -1
        """

        profile_selection = str(profile_selection).lower()
        if profile_selection not in ["main", "competitive"]:
            self.logger.error("[-] Internal error. Unable to establish desired profile.")
            return -1

        # R6 Siege running
        if self.is_process_active(["rainbowsix_vulkan.exe", "rainbowsix.exe"]):
            self.logger.error("[-] R6 Siege already running. "
                              "Please close Siege to switch profiles.")
            return -1

        # Enumerate files and define profile defaults
        ubi_profile_path = profile_path / "1.save"
        main_profile_path = profile_path / "1.save.main.bak"
        comp_profile_path = profile_path / "1.save.competitive.bak"

        self.logger.info(f"Account: {profile_name}")

        # 1.save does not exist
        if not ubi_profile_path.is_file():
            self.logger.error(f"[-] Error - Unable to locate '{ubi_profile_path.name}'. "
                              f"File does not exist")
            return -1

        # Assign main and comp file existence to vars
        main_profile_status = main_profile_path.is_file()
        comp_profile_status = comp_profile_path.is_file()

        # Only the 1.save exists (first time script is run)
        if not main_profile_status and not comp_profile_status:
            copy_result = self.copy_file(ubi_profile_path, main_profile_path, ctx="Switch",
                                         msg="[+] Only one profile existed - "
                                             "the current profile is: Competitive")
            if copy_result == -1:
                return -1

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

            if backup_flag:
                # Currently ignores results from backup success/fail
                self.backup_profile(profile_path)

            # Competitive -> Main
            if active_profile == "competitive" and profile_selection == "main":
                self.rename_file(ubi_profile_path, comp_profile_path)
                self.rename_file(main_profile_path, ubi_profile_path)
            # Main -> Competitive
            elif active_profile == "main" and profile_selection == "competitive":
                self.rename_file(ubi_profile_path, main_profile_path)
                self.rename_file(comp_profile_path, ubi_profile_path)
            elif active_profile == "internal error":
                self.logger.error("[-] Unable to make any changes. Current profile could not "
                                  "be established")
                return -1
            # Competitive -> Competitive or Main -> Main
            elif active_profile == profile_selection:
                self.logger.info("[*] No changes made")

            else:
                self.logger.error("[-] Internal error. Unable to establish desired profile.")
                return -1

            self.logger.info(f"[*] Old Profile: {active_profile.title()}\n"
                             f"[*] Current Profile: {profile_selection.title()}")


if __name__ == '__main__':
    pass
