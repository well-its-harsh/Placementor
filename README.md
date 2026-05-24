# Placementor

Placementor is a comprehensive, AI-powered Placement Portal built with Django. It streamlines the placement process by offering tools for resume parsing, interview scheduling via Google Calendar, and AI-driven insights.

## 🚀 Features

- **Robust Backend**: Built on Django with a MySQL database.
- **AI Integration**: Leverages Google Generative AI (Gemini) for smart resume analysis and insights.
- **Resume Parsing**: Automatically extracts relevant information from PDF resumes using PyPDF2.
- **Automated Scheduling**: Integrates with the Google Calendar API to schedule and manage interviews effortlessly.
- **Secure File Handling**: Manages resumes and other media uploads securely.

## 🛠️ Technology Stack

- **Framework**: Django 5.2
- **Database**: MySQL (via `mysqlclient`)
- **AI & Processing**: `google-generativeai`, `PyPDF2`
- **Integrations**: Google Calendar API (`google-api-python-client`, `google-auth`)
- **Environment Management**: `django-environ`, `python-dotenv`

## ⚙️ Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/well-its-harsh/Placementor.git
cd Placementor
```

### 2. Set up the Virtual Environment
Create and activate a virtual environment.
```powershell
python -m venv env
# On Windows PowerShell
.\env\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Configuration
Update the `placement_portal/settings.py` (or your `.env` file) with your local MySQL credentials:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'placement_cell',
        'USER': 'root',
        'PASSWORD': 'your_mysql_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```
Create the database in MySQL:
```sql
CREATE DATABASE placement_cell;
```

### 5. Run Migrations
```bash
cd placement_portal
python manage.py makemigrations
python manage.py migrate
```

### 6. Start the Development Server
```bash
python manage.py runserver
```

## 🔑 Environment Variables & Credentials
- Create a `.env` file in your root directory based on the database and secret keys required.
- **Google API**: Add your `credentials.json` for Google Calendar integration in the base directory as configured in `settings.py`.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.
