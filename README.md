# 2026 TUK Capstone Backend

## Framework
Django 6.0

## Prerequisites
python 3.12

## Setting (Windows)
```
git clone https://github.com/ScenarioHub/Backend.git
cd Backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
```

* Copy env file that includes django secret key to root directory before running server.

```
python manage.py runserver
```

You may check your development page at `http://localhost:8000/`