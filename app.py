"""
Title: Main application
Author: Primus27
"""

import switch
import main_window as ui_main
import update_window as ui_update
import getting_started_window as ui_getting_started
from PyQt5 import QtCore, QtWidgets, QtGui
import sys
import argparse
import webbrowser
import logging
import datetime
import resources

# Defaults
logging.getLogger("urllib3").setLevel(logging.CRITICAL)  # Prevent all connections from being shown


class MainWindow(QtWidgets.QMainWindow, ui_main.Ui_MainWindow):
    """
    Class for main application window
    """
    def __init__(self, parent=None):
        """
        Initialiser
        """
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        # Set theme
        self.set_dark_theme()

        # Set defaults
        self.args = gl_args
        self.setWindowTitle("R6 Profile Switcher")
        self.setWindowIcon(QtGui.QIcon(resource_path("r6-logo.png")))

        # Set version number and attribution
        self.label_version_no.setText(switch.program_version)
        self.label_attribution.setText("Developed by Primus27 (github.com/primus27)")

        # Add images for runtime
        self.label_circle_s1.setPixmap(QtGui.QPixmap(resource_path("step1-orange.png")))
        self.label_circle_s2.setPixmap(QtGui.QPixmap(resource_path("step2-red.png")))
        self.label_circle_s3.setPixmap(QtGui.QPixmap(resource_path("step3-red.png")))
        self.label_circle_s4.setPixmap(QtGui.QPixmap(resource_path("step4-red.png")))

        # Log
        logging.basicConfig(format='%(message)s')
        if gl_args.get("debug", False):
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)

        # Create text box for log
        textbox_log = QPlainTextEditLogger(self.plainTextEdit_log, (550, 307))
        # Log format
        #textbox_log.setFormatter(logging.Formatter("%(asctime)s :: %(message)s", "%H:%M:%S"))
        textbox_log.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(textbox_log)

        # Create new switch object
        self.profile_switch_obj = switch.ProfileFunctions(logging.getLogger())

        # Defaults
        self.steps_state = [1, 0, 0, 0]  # 0 = No access, 1 = Access
        self.account_list = []
        self.active_profile_list = []
        self.step1_activated_time = None

        # Link 'Kofi' button
        self.pushButton_donation.clicked.connect(
            lambda: webbrowser.open("https://ko-fi.com/primus27"))

        # Step 1 - Link 'Find account'
        self.pushButton_find_account.clicked.connect(self.find_account_action)
        #self.pushButton_find_account.installEventFilter(self)

        # Step 2 - Link Combo Box
        self.comboBox_select_account.installEventFilter(self)
        self.comboBox_select_account.currentIndexChanged.connect(self.set_active_profile_label)

        # Step 3 - Link Radio Buttons
        self.buttonGroup_radio.setExclusive(True)
        self.buttonGroup_radio.buttonClicked.connect(self.select_profile_action)

        # Step 4 - Link 'Activate Profile'
        self.pushButton_activate_profile.clicked.connect(self.activate_profile_action)

        # Update window
        self.action_check_for_updates.triggered.connect(lambda: self.update_dialog.show())
        self.update_dialog = UpdateWindow(self)

        # Dark theme
        self.action_dark_theme.triggered.connect(lambda: self.set_dark_theme(
            self.action_dark_theme.isChecked()))

        # Getting started window
        self.action_getting_started.triggered.connect(lambda: self.getting_started_dialog.show())
        self.getting_started_dialog = GettingStartedWindow(self)

    def set_dark_theme(self, dark=True):
        """
        Sets the window theme.
        :param dark: Dark mode
        """
        if dark:
            theme = "Dark"
        else:
            theme = "Light"

        # Open resource file for stylesheet
        sty_f = QtCore.QFile(resource_path(f"{theme}.qss", "style"))
        sty_f.open(QtCore.QIODevice.ReadOnly)
        self.setStyleSheet(((sty_f.readAll()).data()).decode("latin1"))

        self.label_img_s1.setPixmap(QtGui.QPixmap(resource_path(f"database_{theme.lower()}.png")))
        self.label_img_s4.setPixmap(QtGui.QPixmap(resource_path(f"switch_{theme.lower()}.png")))
        self.label_img_s2.setPixmap(QtGui.QPixmap(resource_path(f"ubisoft_{theme.lower()}.png")))
        self.label_img_s3.setPixmap(QtGui.QPixmap(resource_path(f"user_{theme.lower()}.png")))

        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(resource_path(f"kofi_{theme.lower()}.png")),
            QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton_donation.setIcon(icon)

    def find_account_action(self):
        """
        Step 1 - Find accounts on system and resolve
        :return: None
        """
        if not self.time_delta_allowed():
            return

        self.steps_state = [1, 0, 0, 0]
        self.account_list = self.profile_switch_obj.s1_find_account()

        # No accounts found
        if not self.account_list:
            logging.getLogger().error("[-] No accounts found on system")
            self.profile_switch_obj.separator(use_all=True)
            return

        # Get current active profile
        self.get_all_active_profiles()

        # Update combo box based on account list
        self.update_combo_select_account()

        # Step 1 completed
        self.steps_state = [1, 1, 0, 0]
        self.change_img_colour()

    def update_combo_select_account(self):
        """
        Update combo box based on account list
        """
        # Clear combo box to prevent same account being added from previous "step 1" action
        self.comboBox_select_account.clear()

        # Filter accounts and add name to combo.
        for index, account in enumerate(self.account_list):
            if isinstance(account, tuple):
                # Combobox item index is equal to the index from account list
                self.comboBox_select_account.addItem(account[0], index)

    def eventFilter(self, src, event):
        """
        Event listener
        :param src: Element - i.e. button, combobox...
        :param event: Action to occur - i.e. click, double click...
        :return: False
        """
        if src is self.comboBox_select_account and event.type() == QtCore.QEvent.MouseButtonPress:
            """
            Step 2 - Allow user to select account from combobox
            """
            # Check is user has access
            if self.steps_state[1] == 0:
                self.incomplete_steps_feedback()
            else:
                # Step 2 completed
                self.steps_state = [1, 1, 1, 0]
                self.clear_radio_group()
                self.change_img_colour()
                self.set_active_profile_label()

        #return super(MainWindow, self).eventFilter(src, event)
        return False

    def select_profile_action(self):
        """
        Step 3 - Allow user to select profile (comp/main) from radio buttons
        :return: None
        """
        # Check is user has access
        if self.steps_state[2] == 0:
            self.incomplete_steps_feedback()
            self.clear_radio_group()
            return

        # Step 3 completed
        self.steps_state = [1, 1, 1, 1]
        self.change_img_colour()

    def clear_radio_group(self):
        """
        Clear radio buttons
        """
        self.buttonGroup_radio.setExclusive(False)
        self.radioButton_comp_profile.setChecked(False)
        self.radioButton_main_profile.setChecked(False)
        self.buttonGroup_radio.setExclusive(True)

    def activate_profile_action(self):
        """
        Step 4 - Switch profiles
        :return: None
        """
        # Check is user has access
        if self.steps_state[3] == 0:
            self.incomplete_steps_feedback()
            return

        # Get results of selected account, profile, backup flag, etc.
        account_index = self.comboBox_select_account.currentData()
        selected_account_info = self.account_list[account_index]
        profile_selection = str(self.buttonGroup_radio.checkedButton().text()).lower()
        backup_flag = self.action_profile_backup.isChecked()

        # Should never occur...
        if not len(selected_account_info) == 3:
            logging.getLogger().error("[-] Unable to perform action - internal error")
            return
        
        player_name = selected_account_info[0]
        account_path = selected_account_info[2]

        # Check that all elements contain data
        if not all([player_name, account_path, profile_selection]):
            logging.getLogger().error("[-] Unable to perform action - internal error")
            return

        # Switch profile
        self.profile_switch_obj.s4_activate_profile(account_path, player_name, profile_selection, 
                                                    backup_flag)

        self.profile_switch_obj.separator(use_all=True)

        # Clear radio buttons after completion
        self.clear_radio_group()
        self.change_img_colour(finished=True)
        self.get_all_active_profiles()
        self.set_active_profile_label()

    def incomplete_steps_feedback(self):
        """
        Log error message when previous stages not completed
        :return: None
        """
        step = "previous steps"  # Default
        # Find first step without authorisation
        for i, s in enumerate(self.steps_state):
            if s == 0:
                step = f"step {i}"
                break

        logging.getLogger().error(f"[-] Unable to perform action - "
                                  f"please complete {step} first")
        self.profile_switch_obj.separator(line=True, linefeed_post=True)

    def change_img_colour(self, finished=False):
        """
        Change colour of step images based on user completion
        :param finished: Whether the final step has been completed
        :return: None
        """
        # Check is user has access
        if not len(self.steps_state) == 4:
            return

        # Assign values of step to s1-sX
        s1, s2, s3, s4 = self.steps_state
        if s1 == 1:
            if s2 == 0:  # Step 1 not completed
                self.label_circle_s1.setPixmap(QtGui.QPixmap(resource_path("step1-orange.png")))
            else:  # Step 1 completed
                self.label_circle_s1.setPixmap(QtGui.QPixmap(resource_path("step1-green.png")))

        if s2 == 1:
            if s3 == 0:  # Step 2 not completed
                self.label_circle_s2.setPixmap(QtGui.QPixmap(resource_path("step2-orange.png")))
            else:  # Step 2 completed
                self.label_circle_s2.setPixmap(QtGui.QPixmap(resource_path("step2-green.png")))
        else:  # No access
            self.label_circle_s2.setPixmap(QtGui.QPixmap(resource_path("step2-red.png")))

        if s3 == 1:
            if s4 == 0:  # Step 3 not completed
                self.label_circle_s3.setPixmap(QtGui.QPixmap(resource_path("step3-orange.png")))
            else:  # Step 3 completed
                self.label_circle_s3.setPixmap(QtGui.QPixmap(resource_path("step3-green.png")))
        else:  # No access
            self.label_circle_s3.setPixmap(QtGui.QPixmap(resource_path("step3-red.png")))

        if s4 == 1:
            if finished:  # Step 4 completed
                self.label_circle_s4.setPixmap(QtGui.QPixmap(resource_path("step4-green.png")))
            else:  # Step 4 not completed
                self.label_circle_s4.setPixmap(QtGui.QPixmap(resource_path("step4-orange.png")))
        else:  # No access
            self.label_circle_s4.setPixmap(QtGui.QPixmap(resource_path("step4-red.png")))

    def time_delta_allowed(self, secs_wait: int = 10):
        """
        Calculate whether user has performed action within the last X seconds
        :param secs_wait: Seconds to wait before allowed to perform action
        :return: Allowed: True
                Not allowed: False
        """
        if self.step1_activated_time is None:
            self.step1_activated_time = datetime.datetime.now()
            return True
        else:
            return datetime.datetime.now() - self.step1_activated_time > \
                   datetime.timedelta(seconds=secs_wait)

    def get_all_active_profiles(self):
        """
        Get current profiles for all accounts
        """
        self.active_profile_list = []

        for account in self.account_list:
            # Should never occur...
            if not len(account) == 3:
                self.active_profile_list.append("Error")
                continue

            # Get which account is active
            active_profile = self.profile_switch_obj.get_active_profile(account[2])

            if isinstance(active_profile, str):
                self.active_profile_list.append(active_profile)
            else:
                self.active_profile_list.append("Error")

    def set_active_profile_label(self):
        """
        Set active profile label text
        """
        index = self.comboBox_select_account.currentData()
        if index is None:
            profile = "Error"
        else:
            try:
                profile = self.active_profile_list[index]
            except IndexError:
                profile = "Error"

        self.label_active_profile.setText(f"Active: {profile}")


class UpdateWindow(QtWidgets.QMainWindow, ui_update.Ui_UpdateWindow):
    """
    Class for application window that checks for updates
    """
    def __init__(self, parent=None):
        """
        Initialiser
        """
        super(UpdateWindow, self).__init__(parent)
        self.setupUi(self)

        # Defaults
        width, height = 250, 120  # Window width and height
        self.resize(width, height)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(10, 10, width - 19, height - 19))
        self.setWindowTitle("Updates?")
        self.setWindowIcon(QtGui.QIcon(resource_path("r6-logo.png")))

        # Download latest version button
        self.pushButton_link.setText("Latest version")
        self.pushButton_link.clicked.connect(lambda: webbrowser.open(
            "https://github.com/Primus27/R6-Profile-Switcher/releases"))

        # Close button
        self.pushButton_close.clicked.connect(lambda: self.hide())

        # Create profile switcher object and check for latest version
        self.profile_switch_obj = switch.ProfileFunctions(logging.getLogger())
        results = self.profile_switch_obj.check_latest_version()

        if results[0] == 0:  # Not latest version
            self.label_main_text.setText(f"You are NOT running the latest version!\n"
                                         f"Current: {self.profile_switch_obj.program_version}\n"
                                         f"Latest: {results[1]}")
        elif results[0] == 1:  # Latest version
            self.label_main_text.setText(f"You are running the latest version!")
        else:  # Error
            self.label_main_text.setText(f"Unable to check for latest version!")


class GettingStartedWindow(QtWidgets.QMainWindow, ui_getting_started.Ui_GettingStartedWindow):
    """
    Class for GettingStarted window - Instructions to help new users
    """
    def __init__(self, parent=None):
        """
        Initialiser
        """
        super(GettingStartedWindow, self).__init__(parent)
        self.setupUi(self)

        # Defaults
        width, height = 900, 550  # Window width and height
        self.resize(width, height)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(10, 10, width - 19, height - 19))
        self.setWindowTitle("Getting Started")
        self.setWindowIcon(QtGui.QIcon(resource_path("r6-logo.png")))

        # Close button
        self.pushButton_close.clicked.connect(lambda: self.hide())


class QPlainTextEditLogger(logging.Handler):
    """
    TextEdit class for logger output
    """
    def __init__(self, parent, size_xy: tuple):
        """
        Initialiser
        :param parent: Parent class
        :param size_xy: Size of TextEdit box
        """
        super().__init__()
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        x, y = size_xy
        self.widget.resize(x, y)
        self.widget.setFont(QtGui.QFont("Courier New", 10))

    def emit(self, record):
        """
        Output to log
        :param record: Log message
        """
        msg = self.format(record)
        self.widget.appendPlainText(msg)


def resource_path(filename, resource_type="icon"):
    """
    Return path of files
    :param filename: Name of resource
    :param resource_type: Type of resource (i.e. icon)
    :return:
    """
    """
    # Use with spec file
    if hasattr(sys, '_MEIPASS'):
        return str(Path(sys._MEIPASS) / rel_path)
    return str(Path.cwd() / rel_path)
    """
    return f":/src/{resource_type}/{filename}"


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
    optional.add_argument("-d", "--debug", action="store_true", dest="debug_flag",
                          help="Enable debugging")
    optional.add_argument("--version", action="version",
                          version=f"%(prog)s {switch.program_version}",
                          help="Display program version")
    args = parser.parse_args()

    user_args = {
        "debug": args.debug_flag
    }

    return user_args


if __name__ == "__main__":
    gl_args = get_args()
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
