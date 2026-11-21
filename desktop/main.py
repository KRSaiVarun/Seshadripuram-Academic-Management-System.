"""
Seshadripuram College - Smart Academic Management System
PySide6 Desktop Application — Section 16B Matching Visual Design
Cosmic Glassmorphism | Neon Glowing Accents | Deep Navy & Royal Blue UI
"""

import sys
import requests
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QStackedWidget, QMessageBox, QGridLayout,
    QGraphicsDropShadowEffect, QScrollArea
)

API_BASE = "http://127.0.0.1:8000/api"

# ==============================================================================
# SECTION 16 MASTER DESIGN STYLESHEET (PySide6 QSS)
# ==============================================================================
STYLE = '''
QMainWindow, QWidget#root {
    background-color: #080816;
    color: #F8FAFC;
    font-family: "Segoe UI", -apple-system, sans-serif;
}

QScrollArea {
    background: transparent;
    border: none;
}

QFrame#sidebar {
    background-color: #0C1246;
    border-right: 1px solid rgba(0, 229, 255, 0.22);
}

QFrame#hero-banner {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #101B63, stop:0.6 #0C1246, stop:1 #280C5A);
    border: 1px solid rgba(0, 229, 255, 0.35);
    border-radius: 18px;
}

QFrame#card-blue {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0A225C, stop:1 #081136);
    border: 1px solid rgba(0, 229, 255, 0.35);
    border-radius: 16px;
}

QFrame#card-purple {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2B0A5E, stop:1 #110836);
    border: 1px solid rgba(168, 85, 247, 0.35);
    border-radius: 16px;
}

QFrame#card-emerald {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #084238, stop:1 #061F24);
    border: 1px solid rgba(0, 208, 132, 0.35);
    border-radius: 16px;
}

QFrame#card-orange {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4E280A, stop:1 #261308);
    border: 1px solid rgba(255, 138, 0, 0.35);
    border-radius: 16px;
}

QFrame#content-panel {
    background-color: #0C1246;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
}

QLabel {
    color: #F8FAFC;
}

QLabel#muted {
    color: #94A3B8;
    font-size: 11px;
}

QLabel#eyebrow {
    color: #00E5FF;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
}

QLabel#metric-val {
    font-size: 32px;
    font-weight: 800;
}

QPushButton {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 10px;
    padding: 10px 14px;
    color: #E2E8F0;
    font-weight: 600;
    text-align: left;
}

QPushButton:hover {
    background-color: rgba(0, 229, 255, 0.12);
    border-color: #00E5FF;
    color: #FFFFFF;
}

QPushButton#nav-btn-active {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(8, 123, 255, 0.4), stop:1 rgba(121, 0, 255, 0.4));
    border: 1px solid #00E5FF;
    border-left: 4px solid #00E5FF;
    color: #FFFFFF;
}

QPushButton#primary-action {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #087BFF, stop:1 #7900FF);
    border: none;
    border-radius: 12px;
    font-weight: 700;
    font-size: 13px;
    text-align: center;
    padding: 12px 18px;
    color: #FFFFFF;
}

QPushButton#primary-action:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #D500F9);
}

QLineEdit {
    background-color: #06091E;
    border: 1px solid rgba(0, 229, 255, 0.3);
    border-radius: 10px;
    padding: 12px;
    color: #FFFFFF;
    font-size: 13px;
}

QLineEdit:focus {
    border-color: #00E5FF;
    background-color: #080D2B;
}
'''

def create_shadow(blur=20, offset=(0, 8), color=QColor(0, 0, 0, 140)):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(*offset)
    shadow.setColor(color)
    return shadow

# ==============================================================================
# LOGIN SCREEN
# ==============================================================================
class Login(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setObjectName("root")

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("hero-banner")
        card.setFixedWidth(420)
        card.setGraphicsEffect(create_shadow(30, (0, 12), QColor(0, 0, 0, 200)))

        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 40, 36, 40)
        layout.setSpacing(14)

        logo = QLabel("S")
        logo.setStyleSheet("""
            font-size: 28px; font-weight: 900; color: #FFFFFF;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00E5FF, stop:0.5 #7900FF, stop:1 #FF2DAA);
            border-radius: 14px; padding: 10px 18px;
        """)
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(54, 54)

        eyebrow = QLabel("SESHADRIPURAM COLLEGE · BENGALURU")
        eyebrow.setObjectName("eyebrow")

        title = QLabel("Welcome back.")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))

        sub = QLabel("Sign in to your academic workspace")
        sub.setObjectName("muted")

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username (e.g. admin)")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self.login)

        btn = QPushButton("Sign in  ↗")
        btn.setObjectName("primary-action")
        btn.clicked.connect(self.login)

        tagline = QLabel("LEARN  •  EXCEL  •  GROW")
        tagline.setObjectName("muted")
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet("font-size: 10px; letter-spacing: 2px; color: #7900FF; margin-top: 10px;")

        layout.addWidget(logo)
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addSpacing(14)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(btn)
        layout.addWidget(tagline)

        main_layout.addWidget(card)

    def login(self):
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            QMessageBox.warning(self, "Required", "Please enter both username and password.")
            return

        try:
            response = requests.post(f"{API_BASE}/desktop/login/", json={
                "username": username, "password": password
            }, timeout=6)
            if response.ok:
                data = response.json()
                self.on_success(data["token"], data["full_name"], data["role"])
            else:
                detail = response.json().get("detail", "Invalid username or password.")
                QMessageBox.warning(self, "Sign in failed", detail)
        except requests.RequestException:
            QMessageBox.critical(
                self, "Backend Unavailable",
                "Cannot connect to the Django API at http://127.0.0.1:8000.\n\n"
                "Start the server in a terminal:\n"
                "python manage.py runserver"
            )

# ==============================================================================
# DASHBOARD SCREEN
# ==============================================================================
class Dashboard(QWidget):
    def __init__(self, token, full_name, role):
        super().__init__()
        self.token = token
        self.full_name = full_name
        self.role = role
        self.setObjectName("root")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Left Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(18, 24, 18, 24)
        sb_layout.setSpacing(10)

        brand_row = QHBoxLayout()
        logo_s = QLabel("S")
        logo_s.setStyleSheet("font-size: 20px; font-weight: 900; color: #00E5FF; background: #101B63; border-radius: 8px; padding: 6px 12px;")
        brand_text = QVBoxLayout()
        b_name = QLabel("Seshadripuram")
        b_name.setFont(QFont("Segoe UI", 12, QFont.Bold))
        b_sub = QLabel("COLLEGE · BENGALURU")
        b_sub.setObjectName("muted")
        brand_text.addWidget(b_name)
        brand_text.addWidget(b_sub)
        brand_row.addWidget(logo_s)
        brand_row.addLayout(brand_text)
        sb_layout.addLayout(brand_row)
        sb_layout.addSpacing(18)

        ws_label = QLabel("WORKSPACE")
        ws_label.setObjectName("eyebrow")
        sb_layout.addWidget(ws_label)

        nav_items = [
            ("◈  Overview", True),
            ("◎  Students", False),
            ("♙  Faculty", False),
            ("▦  Departments", False),
            ("◷  Attendance", False),
            ("✧  Examinations", False),
            ("▤  Timetable", False),
            ("▧  Reports", False)
        ]
        for name, is_active in nav_items:
            btn = QPushButton(name)
            if is_active:
                btn.setObjectName("nav-btn-active")
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        # User Profile Footer
        profile_frame = QFrame()
        profile_frame.setObjectName("content-panel")
        pf_layout = QVBoxLayout(profile_frame)
        pf_layout.setContentsMargins(12, 12, 12, 12)
        u_name = QLabel(full_name)
        u_name.setFont(QFont("Segoe UI", 11, QFont.Bold))
        u_role = QLabel(role)
        u_role.setObjectName("muted")
        pf_layout.addWidget(u_name)
        pf_layout.addWidget(u_role)
        sb_layout.addWidget(profile_frame)

        layout.addWidget(sidebar)

        # 2. Main Content Area
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(18)

        # Top Header Bar
        top_bar = QHBoxLayout()
        header_text = QVBoxLayout()
        h_eyebrow = QLabel("ACADEMIC OPERATIONS / DESKTOP DASHBOARD")
        h_eyebrow.setObjectName("eyebrow")
        h_title = QLabel("Your campus, in focus.")
        h_title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header_text.addWidget(h_eyebrow)
        header_text.addWidget(h_title)
        top_bar.addLayout(header_text)
        top_bar.addStretch()

        online_badge = QLabel("●  LIVE API CONNECTED")
        online_badge.setStyleSheet("color: #00D084; font-size: 11px; font-weight: 700; background: rgba(0, 208, 132, 0.12); padding: 6px 14px; border-radius: 20px; border: 1px solid rgba(0, 208, 132, 0.3);")
        top_bar.addWidget(online_badge)
        content_layout.addLayout(top_bar)

        # Hero Banner
        hero = QFrame()
        hero.setObjectName("hero-banner")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_tag = QLabel("LEARN  •  EXCEL  •  GROW")
        hero_tag.setObjectName("eyebrow")
        hero_h1 = QLabel("Academic Operations, Connected.")
        hero_h1.setFont(QFont("Segoe UI", 16, QFont.Bold))
        hero_p = QLabel("Unified management system synchronized in real time with the Seshadripuram PostgreSQL/SQLite backend.")
        hero_p.setObjectName("muted")
        hero_layout.addWidget(hero_tag)
        hero_layout.addWidget(hero_h1)
        hero_layout.addWidget(hero_p)
        content_layout.addWidget(hero)

        # 4 Colourful KPI Cards Grid
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(16)
        content_layout.addLayout(self.kpi_grid)

        # Action Buttons
        actions_row = QHBoxLayout()
        refresh_btn = QPushButton("↻  Refresh Backend Data")
        refresh_btn.setObjectName("primary-action")
        refresh_btn.clicked.connect(self.refresh)
        actions_row.addWidget(refresh_btn)
        actions_row.addStretch()
        content_layout.addLayout(actions_row)

        content_layout.addStretch()
        layout.addWidget(content_area)

        # Initial fetch
        self.refresh()

    def refresh(self):
        try:
            r = requests.get(
                f"{API_BASE}/desktop/summary/",
                headers={"Authorization": f"Token {self.token}"},
                timeout=5
            )
            r.raise_for_status()
            data = r.json()

            # Clear previous grid items
            for i in reversed(range(self.kpi_grid.count())):
                item = self.kpi_grid.takeAt(i)
                if item.widget():
                    item.widget().deleteLater()

            # 4 KPI metrics matching web design Section 16A
            metrics = [
                ("ACTIVE STUDENTS", data["students"], "card-blue", "#00E5FF", "👨‍🎓"),
                ("FACULTY MEMBERS", data["faculty"], "card-purple", "#D500F9", "👩‍🏫"),
                ("DEPARTMENTS", data["departments"], "card-emerald", "#00D084", "🏛️"),
                ("PROGRAMMES", data["programs"], "card-orange", "#FFD700", "✦")
            ]

            for index, (label, val, card_id, accent, icon) in enumerate(metrics):
                card = QFrame()
                card.setObjectName(card_id)
                card_box = QVBoxLayout(card)
                card_box.setContentsMargins(18, 16, 18, 16)

                top_row = QHBoxLayout()
                lbl = QLabel(label)
                lbl.setObjectName("eyebrow")
                lbl.setStyleSheet(f"color: {accent};")
                ico = QLabel(icon)
                top_row.addWidget(lbl)
                top_row.addStretch()
                top_row.addWidget(ico)

                v = QLabel(f"{val:,}")
                v.setObjectName("metric-val")
                v.setStyleSheet(f"color: #FFFFFF;")

                sub = QLabel("Verified Database Record")
                sub.setObjectName("muted")

                card_box.addLayout(top_row)
                card_box.addWidget(v)
                card_box.addWidget(sub)

                self.kpi_grid.addWidget(card, index // 2, index % 2)

        except requests.RequestException as exc:
            QMessageBox.warning(
                self, "Sync Issue",
                f"Could not refresh live academic statistics from Django API.\n\nError: {exc}"
            )

# ==============================================================================
# MAIN WINDOW CONTAINER
# ==============================================================================
class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seshadripuram College · Smart Academic Management")
        self.resize(1100, 740)
        self.setMinimumSize(850, 600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.stack.addWidget(Login(self.show_dashboard))

    def show_dashboard(self, token, name, role):
        self.dashboard = Dashboard(token, name, role)
        self.stack.addWidget(self.dashboard)
        self.stack.setCurrentIndex(1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = Window()
    window.show()
    sys.exit(app.exec())
