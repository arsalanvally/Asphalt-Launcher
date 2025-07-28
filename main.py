"""
Asphalt Launcher - A Launcher for Minecraft
An open-source and minimal Minecraft launcher built using Python

GitHub: https://github.com/arsalanvally/Asphalt-Launcher
README: https://github.com/arsalanvally/Asphalt-Launcher/blob/main/README.md
LICENSE: https://github.com/arsalanvally/Asphalt-Launcher/blob/main/LICENSE
BUILD: https://github.com/arsalanvally/Asphalt-Launcher/blob/main/BUILD.md

If you find this useful, please consider giving credit by linking to my GitHub page—it's not required, but it would be greatly appreciated.
You're free to modify and redistribute this without any restrictions.
"""

import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime

import psutil
import minecraft_launcher_lib

from PySide6.QtCore import QObject, Qt, QThread, QSize, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QProgressBar, QPushButton, QSlider, QSpinBox, QTextEdit,
    QVBoxLayout, QWidget
)
from PySide6.QtGui import QIcon, QPainter, QPixmap


class BackgroundWidget(QWidget):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), self.pixmap)


def get_appdata_path():
    return os.path.join(os.getenv("APPDATA"), "AsphaltLauncher")


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


def get_minecraft_dir():
    return os.path.expandvars(r"%APPDATA%\.minecraft")


CONFIG_FILE = os.path.join(get_appdata_path(), "launcher.json")


def load_config():
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"username": "", "jvm_args": ["-Xms2G", "-Xmx4G"], "java_path": None}


def save_config(username, jvm_args, java_path):
    os.makedirs(get_appdata_path(), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"username": username, "jvm_args": jvm_args, "java_path": java_path}, f, indent=2)


LAST_PLAYED_FILE = os.path.join(get_appdata_path(), "last_played.json")


def load_last_played():
    if os.path.isfile(LAST_PLAYED_FILE):
        try:
            with open(LAST_PLAYED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_last_played(version_id):
    lp = load_last_played()
    lp[version_id] = datetime.now().timestamp()
    with open(LAST_PLAYED_FILE, "w", encoding="utf-8") as f:
        json.dump(lp, f, indent=2)


def _scan_local_versions():
    local = {}
    versions_dir = os.path.join(get_minecraft_dir(), "versions")
    if os.path.isdir(versions_dir):
        for name in os.listdir(versions_dir):
            folder = os.path.join(versions_dir, name)
            if os.path.isdir(folder):
                local[name] = os.path.getmtime(folder)
    return local


def get_available_versions():
    local = _scan_local_versions()
    local_items = [(f"🔧 {v}", v) for v in local]
    remote = minecraft_launcher_lib.utils.get_version_list()
    type_labels = {"release": "Release", "snapshot": "Snapshot", "old_beta": "Beta", "old_alpha": "Alpha"}
    seen = set(local)
    remote_items = []
    
    for v in remote:
        vid = v["id"]
        if vid in seen:
            continue
        seen.add(vid)
        label = f"{type_labels.get(v['type'], v['type'])} - {vid}"
        remote_items.append((label, vid))
    
    items = local_items + remote_items
    last_played = load_last_played()
    
    if last_played:
        last_vid = max(last_played, key=last_played.get)
        idx = next((i for i, (_, vid) in enumerate(items) if vid == last_vid), None)
        if idx is not None:
            items.insert(0, items.pop(idx))
    
    return items


def launch_minecraft(username, version, java_executable=None, jvm_args=None):
    offline_uuid = str(uuid.uuid3(uuid.NAMESPACE_OID, username))
    options = {"username": username, "uuid": offline_uuid, "token": "0" * 32}
    
    if java_executable:
        options["executablePath"] = java_executable
    if jvm_args:
        options["jvmArguments"] = jvm_args
    
    mc_dir = get_minecraft_dir()
    minecraft_launcher_lib.install.install_minecraft_version(version, mc_dir, callback=None)
    command = minecraft_launcher_lib.command.get_minecraft_command(version, mc_dir, options)
    
    proc = subprocess.Popen(
        command,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        cwd=os.path.expandvars(r"%APPDATA%\.minecraft")
    )
    
    save_last_played(version)
    proc.wait()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] != os.getpid():
                if "asphalt-launcher" in ' '.join(proc.info['cmdline']).lower():
                    proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


class JvmArgsDialog(QDialog):
    def __init__(self, parent=None, current=None):
        super().__init__(parent)
        self.setWindowTitle("Custom JVM Arguments")
        self.setFixedSize(500, 300)
        
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setPlainText("\n".join(current or []))
        layout.addWidget(self.text)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def args(self):
        txt = self.text.toPlainText().strip()
        return txt.splitlines() if txt else []


class JavaPickerDialog(QDialog):
    def __init__(self, parent=None, current=""):
        super().__init__(parent)
        self.setWindowTitle("Select Java Executable")
        self.setFixedSize(400, 100)
        
        layout = QVBoxLayout(self)
        
        self.path = QLineEdit(current or "")
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        
        row = QHBoxLayout()
        row.addWidget(self.path)
        row.addWidget(browse)
        layout.addLayout(row)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _browse(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Java executable", "", "Executables (*.exe)" if os.name == 'nt' else "")
        if file:
            self.path.setText(file)

    def java_path(self):
        path = self.path.text().strip()
        if path and ("java" in path.lower() or "javaw" in path.lower()):
            return path
        return None


class InstallWorker(QObject):
    progress_max = Signal(int)
    progress = Signal(int)
    finished = Signal()
    failed = Signal(str)

    def __init__(self, version_id, mc_dir):
        super().__init__()
        self.version_id = version_id
        self.mc_dir = mc_dir

    def run(self):
        try:
            def cb_max(v): self.progress_max.emit(v)
            def cb_prog(v): self.progress.emit(v)
            
            minecraft_launcher_lib.install.install_minecraft_version(
                self.version_id, self.mc_dir,
                callback={"setMax": cb_max, "setProgress": cb_prog, "setStatus": lambda _: None}
            )
            self.finished.emit()
        except Exception as e:
            self.failed.emit(str(e))


class AsphaltLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.appdata_dir = get_appdata_path()
        self.icon_path = resource_path("assets/icon.ico")
        self.cfg = load_config()
        self.java_executable = self.cfg.get("java_path")
        self.jvm_arguments = self.cfg.get("jvm_args", ["-Xms2G", "-Xmx4G"])
        
        self.setWindowTitle("Asphalt Launcher")
        self.setFixedSize(880, 520)
        self.setWindowIcon(QIcon(self.icon_path))
        
        bg_path = resource_path("assets/background.svg")
        if os.path.isfile(bg_path):
            bg_pixmap = QPixmap(bg_path)
            bg = BackgroundWidget(bg_pixmap, self)
            bg.setGeometry(self.rect())
            bg.lower()
        else:
            self.setStyleSheet("background-color: #2c2c2c; color: white; font-family: 'Segoe UI';")
        
        root_v = QVBoxLayout(self)
        root_v.setContentsMargins(0, 0, 0, 0)
        
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(16, 12, 16, 8)
        
        saved = load_config()
        self.login_lbl = QLabel()
        self.login_lbl.setFixedWidth(300)
        self.login_lbl.setStyleSheet("color:#ffffff; font-size:12px; font-weight:bold;")
        self.login_lbl.setAttribute(Qt.WA_StyledBackground, True)
        
        if saved.get("username"):
            self.login_lbl.setText(f"Logged in as {saved['username']}")
            self.login_lbl.show()
        else:
            self.login_lbl.hide()
        
        top_bar.addWidget(self.login_lbl)
        top_bar.addStretch()
        
        self.btn_account = QPushButton()
        self.btn_account.setIcon(QIcon(resource_path("assets/account.svg")))
        self.btn_account.setIconSize(QSize(20, 20))
        self.btn_account.setFixedSize(28, 28)
        self.btn_account.setStyleSheet(
            "QPushButton { border:none; padding:4px; }"
            "QPushButton:hover { background:rgba(255,255,255,40); border-radius:6px; }"
        )
        self.btn_account.clicked.connect(self.open_account_popup)
        top_bar.addWidget(self.btn_account)
        
        self.btn_settings = QPushButton()
        self.btn_settings.setIcon(QIcon(resource_path("assets/settings.svg")))
        self.btn_settings.setIconSize(QSize(20, 20))
        self.btn_settings.setFixedSize(28, 28)
        self.btn_settings.setStyleSheet(
            "QPushButton { border:none; padding:4px; }"
            "QPushButton:hover { background:rgba(255,255,255,40); border-radius:6px; }"
        )
        self.btn_settings.clicked.connect(self.open_settings)
        top_bar.addWidget(self.btn_settings)
        
        root_v.addLayout(top_bar)
        root_v.addStretch()
        
        # Center content
        center_h = QHBoxLayout()
        center_h.addStretch()
        
        center_v = QVBoxLayout()
        center_v.setAlignment(Qt.AlignCenter)
        
        self.version_dropdown = QComboBox()
        self.version_map = {}
        self._online = True
        
        self.version_dropdown.setFixedWidth(220)
        self.version_dropdown.setFixedHeight(42)
        self.version_dropdown.setStyleSheet(
            "QComboBox { background: rgba(0, 0, 0, 80); color: #fff; font-weight: bold; border: none; border-radius: 4px; padding-left: 6px; }"
            "QComboBox::drop-down { background: transparent; }"
            "QComboBox QAbstractItemView { background: rgba(0, 0, 0, 80); color: #ffffff; font-weight: bold; border: none; }"
        )
        
        self.retry_btn = QPushButton()
        self.retry_btn.setIcon(QIcon(resource_path("assets/retry.svg")))
        self.retry_btn.setIconSize(QSize(20, 20))
        self.retry_btn.setFixedSize(28, 42)
        self.retry_btn.setToolTip("Refresh version list")
        self.retry_btn.setStyleSheet("""
            QPushButton { border:none; }
            QPushButton:hover { background:rgba(255,255,255,40); border-radius:6px; }
            QPushButton:pressed { background:rgba(255,255,255,60); }
        """)
        self.retry_btn.clicked.connect(self._populate_dropdown)
        self.retry_btn.hide()
        
        try:
            versions = get_available_versions()
            self.retry_btn.hide()
        except Exception:
            versions = [(f"🔧 {v}", v) for v in _scan_local_versions()]
            self.retry_btn.show()
        
        most_recent_index = 0
        for idx, (label, version_id) in enumerate(versions):
            self.version_dropdown.addItem(label)
            self.version_map[label] = version_id
            if label.startswith("🔧") and most_recent_index == 0:
                most_recent_index = idx
        
        self.version_dropdown.setCurrentIndex(most_recent_index)
        
        last = load_last_played()
        if last:
            last_vid = max(last, key=last.get)
            idx = next((i for i, (_, vid) in enumerate(versions) if vid == last_vid), 0)
            self.version_dropdown.setCurrentIndex(idx)
        
        self.start_btn = QPushButton("START")
        self.start_btn.setFixedSize(80, 42)
        self.start_btn.setStyleSheet(
            "QPushButton { background: rgba(0, 0, 0, 80); color: #ffffff; "
            "border: none; border-radius: 4px; font-size:17px; font-weight:bold; }"
            "QPushButton:hover { background: rgba(0, 0, 0, 100); }"
            "QPushButton:pressed { background: rgba(0, 0, 0, 120); }"
        )
        self.start_btn.clicked.connect(self.launch_game)
        
        row = QHBoxLayout()
        row.addWidget(self.version_dropdown)
        row.addWidget(self.retry_btn)
        row.addSpacing(1)
        row.addWidget(self.start_btn)
        center_v.addLayout(row)
        center_h.addLayout(center_v)
        center_h.addStretch()
        
        root_v.addLayout(center_h)
        root_v.addStretch()
        
        self._populate_dropdown()
        
        from PySide6.QtCore import QTimer
        self._network_timer = QTimer(self)
        self._network_timer.setInterval(3000)
        self._network_timer.timeout.connect(self._check_network)
        self._network_timer.start()
        
        footer = QLabel("Asphalt Launcher - A Launcher for Minecraft")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color:#fff; font-size:14px; font-weight:bold; margin-bottom: 12px;")
        root_v.addWidget(footer)

    def open_settings(self):
        SettingsDialog(self, self.java_executable, self.jvm_arguments).exec()

    def open_account_popup(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Account")
        dlg.setFixedSize(300, 160)
        dlg.setModal(True)
        dlg.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px;")

        # Main layout
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Username:"))
        username_edit = QLineEdit(load_config().get("username", ""))
        username_edit.setFixedHeight(28)
        username_edit.setStyleSheet(
            "background:#ffffff; border:1px solid #aaa; border-radius:4px; padding:4px 8px;"
        )
        username_edit.setReadOnly(bool(load_config().get("username")))
        username_edit.mousePressEvent = lambda _, e=username_edit: e.setReadOnly(False)
        layout.addWidget(username_edit)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.setAlignment(Qt.AlignCenter)

        save_btn = QPushButton("Save & Exit")
        save_btn.setFixedSize(90, 28)
        save_btn.setStyleSheet("background:#888888; color:#000; border:none; border-radius:4px;")
        save_btn.clicked.connect(dlg.accept)

        logout_btn = QPushButton("Logout")
        logout_btn.setFixedSize(90, 28)
        logout_btn.setStyleSheet("background:#888888; color:#000; border:none; border-radius:4px;")

        for btn in [save_btn, logout_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 0, 0, 120);
                    color: #ffffff;
                    font-weight: bold;
                    border: none;
                    border-radius: 4px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background: rgba(0, 0, 0, 160);
                }
                QPushButton:pressed {
                    background: rgba(0, 0, 0, 200);
                }
            """)

        def do_logout():
            save_config("", self.jvm_arguments, self.java_executable)
            self.current_username = ""
            self.login_lbl.hide()
            dlg.reject()

        logout_btn.clicked.connect(do_logout)
        btn_box.addWidget(save_btn)
        btn_box.addWidget(logout_btn)
        layout.addLayout(btn_box)

        dlg.exec()
        if dlg.result() == QDialog.Accepted:
            username = username_edit.text().strip()
            save_config(username, self.jvm_arguments, self.java_executable)
            self.current_username = username
            self.login_lbl.setText(f"Logged in as {username}")
            self.login_lbl.show()

    def edit_jvm_args(self):
        dlg = JvmArgsDialog(self, self.jvm_arguments)
        if dlg.exec():
            self.jvm_arguments = dlg.args()
            save_config(self.username_input.text(), self.jvm_arguments, self.java_executable)

    def select_java(self):
        dlg = JavaPickerDialog(self, self.java_executable or "")
        if dlg.exec():
            self.java_executable = dlg.java_path()
            save_config(self.username_input.text(), self.jvm_arguments, self.java_executable)

    def open_folder(self, path):
        if os.path.isdir(path):
            os.startfile(path)

    def _populate_dropdown(self):
        old_text = self.version_dropdown.currentText()
        self.version_dropdown.clear()
        self.version_map.clear()

        local = _scan_local_versions()
        for v in local:
            label = f"🔧 {v}"
            self.version_dropdown.addItem(label)
            self.version_map[label] = v

        if self._online:
            try:
                remote = minecraft_launcher_lib.utils.get_version_list()
                type_labels = {"release": "Release", "snapshot": "Snapshot",
                               "old_beta": "Beta", "old_alpha": "Alpha"}
                seen = set(local)
                for v in remote:
                    vid = v["id"]
                    if vid in seen:
                        continue
                    seen.add(vid)
                    label = f"{type_labels.get(v['type'], v['type'])} - {vid}"
                    self.version_dropdown.addItem(label)
                    self.version_map[label] = vid
                self.retry_btn.hide()
            except Exception:
                self._online = False
                self.retry_btn.show()
        else:
            self.retry_btn.show()

        idx = self.version_dropdown.findText(old_text)
        if idx != -1:
            self.version_dropdown.setCurrentIndex(idx)

        last_played = load_last_played()
        if last_played:
            last_vid = max(last_played, key=last_played.get)
            for i in range(self.version_dropdown.count()):
                if self.version_map[self.version_dropdown.itemText(i)] == last_vid:
                    self.version_dropdown.setCurrentIndex(i)
                    break

    def _check_network(self):
        import socket
        new_state = True
        try:
            socket.create_connection(("launchermeta.mojang.com", 443), timeout=1)
        except Exception:
            new_state = False
        if new_state != self._online:
            self._online = new_state
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._populate_dropdown)

    def launch_game(self):
        self._populate_dropdown()
        self._online = None

        username = getattr(self, 'current_username', '').strip()
        if not username:
            username = load_config().get("username", "")
        selected_label = self.version_dropdown.currentText()
        version_id = self.version_map[selected_label]

        if not username:
            dlg = QDialog(self)
            dlg.setWindowTitle("Attention")
            dlg.setFixedSize(300, 80)
            dlg.setModal(True)
            lay = QVBoxLayout(dlg)
            lay.addWidget(QLabel("Username is required to launch Minecraft"),
                          alignment=Qt.AlignCenter)
            ok = QPushButton("OK")
            ok.clicked.connect(dlg.accept)
            lay.addWidget(ok, alignment=Qt.AlignCenter)
            dlg.exec()
            return

        save_config(username, self.jvm_arguments, self.java_executable)
        mc_dir = get_minecraft_dir()
        version_dir = os.path.join(mc_dir, "versions", version_id)
        json_file = os.path.join(version_dir, f"{version_id}.json")
        jar_file = os.path.join(version_dir, f"{version_id}.jar")
        already_installed = os.path.isfile(json_file) and os.path.isfile(jar_file)

        if not already_installed:
            from PySide6.QtCore import QThread
            from PySide6.QtWidgets import QMessageBox
            progress = QDialog(self)
            progress.setWindowTitle("Downloading…")
            progress.setFixedSize(300, 100)
            progress.setModal(True)
            layout = QVBoxLayout(progress)
            bar = QProgressBar()
            layout.addWidget(QLabel("Minecraft will launch after installation."),
                             alignment=Qt.AlignCenter)
            layout.addWidget(bar)
            self.thread = QThread()
            self.worker = InstallWorker(version_id, mc_dir)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.progress_max.connect(bar.setMaximum)
            self.worker.progress.connect(bar.setValue)
            self.worker.finished.connect(progress.accept)
            self.worker.failed.connect(
                lambda msg: (progress.reject(),
                             QMessageBox.critical(self, "Download Failed", msg)))
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()
            progress.exec()
            if progress.result() != QDialog.Accepted:
                return

        self.hide()
        try:
            launch_minecraft(username, version_id,
                             java_executable=self.java_executable,
                             jvm_args=self.jvm_arguments)
        except Exception as e:
            print(f"Launch failed: {e}")
        finally:
            self.show()


class SettingsDialog(QDialog):
    def __init__(self, parent, java_executable, jvm_arguments):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(380, 240)
        self.setModal(True)
        self.parent_window = parent
        self.jvm_arguments = list(jvm_arguments or [])
        
        self.min_spin = QSpinBox()
        self.min_spin.setRange(512, 64 * 1024)
        self.min_spin.setSingleStep(256)
        self.min_spin.setValue(2048)
        
        self.max_spin = QSpinBox()
        self.max_spin.setRange(512, 64 * 1024)
        self.max_spin.setSingleStep(256)
        self.max_spin.setValue(4096)
        
        self.min_slider = QSlider(Qt.Horizontal)
        self.min_slider.setRange(512, 64 * 1024)
        self.min_slider.setSingleStep(256)
        self.min_slider.setPageStep(1024)
        self.min_slider.setValue(2048)
        
        self.max_slider = QSlider(Qt.Horizontal)
        self.max_slider.setRange(512, 64 * 1024)
        self.max_slider.setSingleStep(256)
        self.max_slider.setPageStep(1024)
        self.max_slider.setValue(4096)
        
        self.min_spin.valueChanged.connect(self.min_slider.setValue)
        self.min_slider.valueChanged.connect(self.min_spin.setValue)
        self.max_spin.valueChanged.connect(self.max_slider.setValue)
        self.max_slider.valueChanged.connect(self.max_spin.setValue)
        self.min_spin.valueChanged.connect(self._write_ram_to_args)
        self.max_spin.valueChanged.connect(self._write_ram_to_args)
        
        self._load_ram_from_args()
        
        slider_style = """
        QSlider::handle:horizontal {
            background: rgba(0, 0, 0, 120);
            width: 18px;
            margin: -2px 0;
            border-radius: 9px;
        }

        QSlider::groove:horizontal {
            background: #DDDDDD;
            height: 4px;
            border-radius: 2px;
        }

        QSlider::handle:horizontal:hover {
            background: rgba(0, 0, 0, 160);
        }

        QSlider::handle:horizontal:pressed {
            background: rgba(0, 0, 0, 200);
        }
        """
        self.min_slider.setStyleSheet(slider_style)
        self.max_slider.setStyleSheet(slider_style)
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Min RAM (MB):"), 0, 0)
        grid.addWidget(self.min_slider, 0, 1)
        grid.addWidget(self.min_spin, 0, 2)
        grid.addWidget(QLabel("Max RAM (MB):"), 1, 0)
        grid.addWidget(self.max_slider, 1, 1)
        grid.addWidget(self.max_spin, 1, 2)
        
        btn_jvm = QPushButton("Custom JVM Args")
        btn_java = QPushButton("Select JRE")
        btn_mc = QPushButton(".minecraft")
        btn_launcher = QPushButton("Launcher Dir")
        
        for btn in (btn_jvm, btn_java, btn_mc, btn_launcher):
            btn.setStyleSheet("background-color: #888888; padding: 8px; font-size: 12px;")
        
        btn_grid = QGridLayout()
        btn_grid.addWidget(btn_jvm, 0, 0)
        btn_grid.addWidget(btn_java, 0, 1)
        btn_grid.addWidget(btn_mc, 1, 0)
        btn_grid.addWidget(btn_launcher, 1, 1)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #888888; padding: 8px; font-size: 12px;")
        close_btn.clicked.connect(self.accept)
        
        credits_btn = QPushButton("Credits")
        credits_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 120);
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 160);
            }
            QPushButton:pressed {
                background: rgba(0, 0, 0, 200);
            }
        """)
        credits_btn.clicked.connect(self._show_credits)

        for btn in [btn_jvm, btn_java, btn_mc, btn_launcher, close_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 0, 0, 120);
                    color: #ffffff;
                    font-weight: bold;
                    border: none;
                    border-radius: 4px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background: rgba(0, 0, 0, 160);
                }
                QPushButton:pressed {
                    background: rgba(0, 0, 0, 200);
                }
            """)
        
        main = QVBoxLayout(self)
        main.addLayout(grid)
        main.addLayout(btn_grid)
        main.addWidget(credits_btn)
        main.addWidget(close_btn)
        
        btn_jvm.clicked.connect(self._open_jvm_dialog)
        btn_java.clicked.connect(self._open_java_dialog)
        btn_mc.clicked.connect(lambda: self.parent_window.open_folder(get_minecraft_dir()))
        btn_launcher.clicked.connect(lambda: self.parent_window.open_folder(self.parent_window.appdata_dir))

    def _load_ram_from_args(self):
        for arg in self.jvm_arguments:
            if arg.startswith("-Xms"):
                mb = int(arg[4:-1]) if arg.endswith("M") else int(arg[4:-1]) * 1024
                self.min_spin.setValue(mb)
                self.min_slider.setValue(mb)
            elif arg.startswith("-Xmx"):
                mb = int(arg[4:-1]) if arg.endswith("M") else int(arg[4:-1]) * 1024
                self.max_spin.setValue(mb)
                self.max_slider.setValue(mb)

    def _write_ram_to_args(self):
        new_args = [a for a in self.jvm_arguments if not (a.startswith("-Xms") or a.startswith("-Xmx"))]
        new_args.append(f"-Xms{self.min_spin.value()}M")
        new_args.append(f"-Xmx{self.max_spin.value()}M")
        self.jvm_arguments = new_args
        self.parent_window.jvm_arguments = new_args
        save_config(
            load_config().get("username", ""),
            self.jvm_arguments,
            self.parent_window.java_executable
        )

    def _open_jvm_dialog(self):
        dlg = JvmArgsDialog(self, self.jvm_arguments)
        if dlg.exec():
            self.jvm_arguments = dlg.args()
            self.parent_window.jvm_arguments = self.jvm_arguments
            save_config(
                load_config().get("username", ""),
                self.jvm_arguments,
                self.parent_window.java_executable
            )
            self._load_ram_from_args()

    def _open_java_dialog(self):
        dlg = JavaPickerDialog(self, self.parent_window.java_executable or "")
        if dlg.exec():
            self.parent_window.java_executable = dlg.java_path()
            save_config(
                load_config().get("username", ""),
                self.jvm_arguments,
                self.parent_window.java_executable
            )

    def _show_credits(self):
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QDialog, QLabel, QPushButton
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl, Qt

        dlg = QDialog(self)
        dlg.setWindowTitle("Credits")
        dlg.setFixedSize(420, 360)
        dlg.setModal(True)

        label = QLabel()
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        label.setTextFormat(Qt.RichText)
        label.setText(
            "<strong>Asphalt Launcher - A Launcher for Minecraft</strong><br>"
            "An open-source and minimal Minecraft launcher built using Python<br><br>"
            '<a href="https://github.com/arsalanvally/Asphalt-Launcher">GitHub</a> • '
            '<a href="https://github.com/arsalanvally/Asphalt-Launcher/blob/main/README.md">README</a> • '
            '<a href="https://github.com/arsalanvally/Asphalt-Launcher/blob/main/LICENSE">LICENSE</a> • '
            '<a href="https://github.com/arsalanvally/Asphalt-Launcher/blob/main/BUILD.md">BUILD</a> • '
            '<a href="https://github.com/arsalanvally/Asphalt-Launcher/blob/main/FAQ.md">FAQ</a><br><br>'
            "If you find this useful, <strong>please consider giving credit</strong> by linking to my GitHub page—"
            "it's not required, but it would be <strong>greatly appreciated.</strong><br>"
            "You're <strong>free</strong> to <strong>modify</strong> and <strong>redistribute</strong> this <strong>without</strong> any <strong>restrictions.</strong>"
        )
        label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12px; padding: 8px;")

        github_btn = QPushButton("GitHub")
        thanks_btn = QPushButton("Thanks")

        style = """
            QPushButton {
                background: rgba(0, 0, 0, 120);
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 160);
            }
            QPushButton:pressed {
                background: rgba(0, 0, 0, 200);
            }
        """
        github_btn.setStyleSheet(style)
        thanks_btn.setStyleSheet(style)

        github_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/arsalanvally/Asphalt-Launcher"))
        )
        thanks_btn.clicked.connect(dlg.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(github_btn)
        btn_layout.addWidget(thanks_btn)

        layout = QVBoxLayout(dlg)
        layout.addWidget(label)
        layout.addLayout(btn_layout)

        dlg.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = AsphaltLauncher()
    launcher.show()
    sys.exit(app.exec())