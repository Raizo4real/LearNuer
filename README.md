# LearNeur 🧠✨

# Where Therapy Meets Imagination.

**LearNeur** is a smart, interactive, and comprehensive digital ecosystem specifically designed to support children on the Autism Spectrum. It also provides an advanced environment for parents, doctors, and system administrators to monitor the child's condition and progress. The application bridges interactive educational games, tactile physics-based playrooms, and clinical telemetry to deliver a customized and joyful therapeutic experience in one place.

---

## 📑 Table of Contents

- [About The Project](#-about-the-project)
- [Tech Stack](#-tech-stack)
- [Architecture & Rules](#-architecture--rules)
- [Project Structure](#-project-structure)
- [Pages & Mechanics](#-pages--mechanics)
- [State & Security Management](#-state--security-management)
- [Design System](#-design-system)

---

## 🎯 About The Project

**LearNeur** serves four main categories with completely separate User Experiences (UX) for each category[cite: 1, 2]:

1. **Child Portal (Sandbox Playroom):** 
   - A distraction-free visual interface relying on smooth animations and calming colors.
   - Features a custom 2D Physics engine allowing the child to interact with toys (Squishy Teddy, Hovering UFOs, Lego Blocks) to enhance cognitive and motor skills without sensory overload.
2. **Parent Dashboard:** 
   - A comprehensive statistical control panel displaying the child's progress reports.
   - Protected by a strict Kiosk Lock (PIN System) ensuring the child remains safely within the playroom.
3. **Doctor Dashboard:** 
   - A clinic management system allowing doctors to track patient performance and adjust treatment plans based on the child's actual interaction within the app.
4. **Admin & Owner Portal:** 
   - Elevated platform access to manage parents, approve new doctor registrations, and audit system data.

---

## 💻 Tech Stack

The project is built using a robust, high-performance modern web stack:

- **Backend Framework:** `FastAPI` (Python) for asynchronous, high-speed RESTful API routing.
- **Database & ORM:** `SQLAlchemy` mapping to relational databases (`PostgreSQL` / `SQLite`).
- **Frontend Logic:** `Vanilla JavaScript (ES6+)` for lightning-fast DOM manipulation and custom physics calculations without the overhead of heavy frameworks.
- **Styling:** Custom `HTML5` & `CSS3` utilizing advanced features like `Glassmorphism` and `3D Claymorphism`[cite: 1, 3].
- **Authentication:** Stateless `JWT` (JSON Web Tokens) paired with `HttpOnly` cookies[cite: 2].
- **Data Visualization:** `Chart.js` for rendering clinical telemetry and focus velocity graphs.

---

## 🏗️ Architecture & Rules

The project follows a highly secure and modular architecture:

1. **Role-Based Access Control (RBAC):**
   - The backend validates access levels (OWNER, ADMIN, DOCTOR, PARENT) before serving any data or dashboard[cite: 1, 2].
2. **Silent Security Guards:**
   - Instead of exposing authentication failures via native alerts, unauthorized users are silently redirected to the login portal, mitigating enumeration attacks.
3. **No-Cache Protocols:**
   - Administrative and clinical dashboards enforce `Cache-Control: no-cache, no-store` headers to ensure sensitive medical and user data is never stored in the browser's local cache[cite: 1, 3].
4. **Atomic Transactions & File Handling:**
   - Registration workflows handle complex relational data creation (e.g., User + Parent Profile) atomically[cite: 2].
   - The system securely processes `Multipart/Form-Data` to store physical medical verification documents locally[cite: 2].

---

## 📁 Project Structure

```text
LearNeur/
├── learneur_backend/
│   ├── main.py                  # Application factory and FastAPI init
│   ├── database.py              # SQLAlchemy setup and DB connection
│   ├── models.py                # Database tables schema (User, Doctor, Parent, etc.)
│   ├── schemas.py               # Pydantic validation models
│   ├── auth.py                  # JWT generation and password hashing
│   ├── dependencies.py          # FastAPI dependency injection utilities
│   ├── learneur.db              # SQLite database file (Development)
│   ├── .env                     # Environment variables and secrets
│   ├── routers/                 # Modular API Endpoints
│   │   ├── analytics_router.py  # child analytics router
│   │   ├── auth_router.py       # Login, registration, and RBAC routing
│   │   ├── chat_router.py       # Chat Between Parent & Doctor router
│   │   ├── doctor_router.py     # Doctor hun management
│   │   ├── forum_router.py      # Doctor Forum router
│   │   ├── game_router.py       # Child games router
│   │   ├── owner_router.py      # Owner dashboard management
│   │   ├── parent_router.py     # Parent dashboard management
│   │   └── settings.py          # Parent Settings management
│   ├── uploads/                 # Secure local storage
│   │   ├── avatars/             # User profile pictures
│   │   └── verification/        # Doctor verification documents
│   └── utils/                   # Backend helper functions
│       ├── __init__.py
│       ├── email_masker.py      # Email Masker Logic for security 
│       ├── email_tokens.py      # Email Verifcation logic
│       ├── email_utils.py       # OTP Logic
│       └── smtp_service.py      # Email sending and verification logic
│
└── learneur_frontend/
    ├── index.html               # Platform Landing Page
    ├── Login.html               # Universal Authentication portal
    ├── child_profile.html       # Sandbox Playroom (Custom Physics Engine)
    ├── dashboard.html           # Parent Control Center
    ├── admin_dashboard.html     # Admin management portal
    ├── owner_dashboard.html     # Owner management portal
    ├── doctor_hub.html          # Doctor Clinical Hub
    ├── doctor_directory.html    # Parent -> Doctor Hub
    ├── educational_engine.html  # Therapeutic education interface
    ├── game.html                # Therapeutic games interface
    ├── analytics.html           # Telemetry and data visualization
    ├── settings.html            # Parent Settings
    ├── app.js                   # Core frontend logic
    ├── config.js                # Global API base URL configuration
    ├── educationalData.js       # Client-side educational content/modules
    └── styles.css               # Global stylesheets and themes
```

## 📄 Pages & Mechanics

1. **Sandbox Playroom (`child_profile.html`):**
   - **Mechanics:** An immersive environment tailored to the child's communication level (e.g., Non-verbal, Verbal).
   - Features a custom JS physics loop (`requestAnimationFrame`) handling collisions and gravity for draggable toys, layered over a 3D grass background and floating CSS clouds.

2. **Owner/Admin Dashboards (`owner_dashboard.html`, `admin_dashboard.html`):**
   - **Mechanics:** A central hub for platform management. Uses dynamic data fetching to populate Glassmorphism tables.
   - Implements custom `Toast` notifications and non-blocking custom confirmation modals (preventing ugly native browser alerts).

3. **Doctor Hub (`doctor_hub.html`):**
   - **Mechanics:** Handles patient telemetry analytics (focus charts, frantic clicks) and includes a global medical community forum for professional discussions.

---

## 🗄️ State & Security Management

1. **Authentication State (6-Month Persistence):**
   - JWT tokens are configured with an extended `max_age` (6 months) and are securely baked into `HttpOnly` cookies, ensuring a seamless, persistent user experience for Parents and Owners without random logouts.

2. **Kiosk Lock Trap:**
   - The child's interface uses the `History API` (`window.history.pushState`) to trap the back button. If pressed, a secure PIN modal intercepts the action, requiring parental OTP/PIN authorization to exit the environment.

3. **DOM Protection:**
   - Developer tools shortcuts (F12, Ctrl+Shift+I) and context menus (Right-click) are strictly disabled within the child's portal to prevent accidental console opening and layout breaking.

---

## 🎨 Design System

- **3D Claymorphism:** Buttons and interactive cards feature deep inner shadows and highlights (`inset -4px -4px 10px`, `inset 4px 4px 10px`) to mimic real-world clay/rubber, encouraging tactile interaction for children.
- **Glassmorphism:** Dashboards utilize semi-transparent backgrounds with `backdrop-filter: blur()` to create a clean, clinical, yet modern aesthetic for doctors and admins.
- **Ambient Backgrounds:** Continuous, slow-drifting radial gradients create a soothing atmosphere without being visually aggressive.
