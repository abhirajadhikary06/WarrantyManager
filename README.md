BillVault 📜💰

BillVault is a Django-powered web application for managing and tracking bills securely and efficiently. It allows users to register, log in, and perform tasks like creating, viewing, and managing their bills.

🔗 Live Site: https://billvault.pythonanywhere.com/accounts/login/


---

✨ Features

👤 User registration and authentication

🔐 Secure login/logout functionality

🧾 Create, view, update, and delete bills

🗂 Categorize and filter bills

📱 Responsive and user-friendly UI

🛠 Admin dashboard for managing data



---

⚙ Tech Stack

Backend: Django (🐍 Python)

Frontend: HTML, CSS, JavaScript (with Django Templates)

Database: SQLite 🗃 (default, configurable)

Hosting: PythonAnywhere ☁



---

🚀 Getting Started

✅ Prerequisites

Make sure you have the following installed:

🐍 Python 3.x

📦 pip

🌱 virtualenv (optional but recommended)



---

⚙ Installation

git clone https://github.com/your-username/billvault.git
cd billvault
python -m venv env
source env/bin/activate  # For Windows: env\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

➡ Visit: http://127.0.0.1:8000/accounts/login/ to access the login page.


---

🧑‍💻 Usage

1. ✍ Register a new account or log in


2. 📋 Create and manage bills from your dashboard


3. 🔎 Use filters to sort or find specific bills


4. 🛡 Admins can manage users and system-wide data from the admin panel




---

📁 Folder Structure

billvault/
├── accounts/           # 🔐 Custom user authentication
├── bills/              # 🧾 App for bill CRUD operations
├── static/             # 🎨 CSS, JS, images
├── templates/          # 🖼 HTML templates
├── manage.py
├── db.sqlite3
└── requirements.txt


---

🔐 Admin Credentials (for demo)

> ⚠ Note: Only if a demo admin account is provided



Username: abcd

Password: abcd@1234
