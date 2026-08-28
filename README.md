# SmartRemind — Context-Aware Daily Assistant (Web Edition)

A modern Python/FastAPI + HTML/CSS/JavaScript prototype using **MySQL**. Location, weather and battery are collected automatically when the browser/device exposes them.

## New in v3
- **Saved Places page with a real “Save Place” button**.
- Save the current GPS location with one click.
- Search for a **city, village, shop or landmark** and select the correct result.
- Reverse geocoding automatically displays village/town/city, district and state.
- Saved places can be reused directly while creating reminders.
- Dashboard, Reminders, Places and Activity navigation all work.
- Dark mode is persisted in the browser.
- Context polling runs in the background while the page is open.
- Notification spam is prevented with a 5-minute server-side trigger cooldown.
- If an active weather/battery condition cannot be obtained, that condition is treated as **not satisfied** rather than incorrectly firing.

## Requirements
- Python 3.10+
- MySQL 8.x (or compatible MySQL server)
- Modern browser with Geolocation support

## Setup

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure MySQL:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=smartremind
```

The app creates the database and tables automatically if the MySQL account has permission. Otherwise create the database first:

```sql
CREATE DATABASE smartremind CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Run

```bash
uvicorn main:app --reload
```

Open:

`http://127.0.0.1:8000`

For browser GPS permissions, localhost is normally allowed. Production deployments should use HTTPS.

## How to test Saved Places

1. Open **Places**.
2. Click **Save Place**.
3. Click **Use current location** to automatically fill GPS + village/city details, or search for a place.
4. Click **Save Place**.
5. Click **Use in reminder** on the saved card.
6. Create a task and choose the radius/weather/battery/time rules.
7. Return to Dashboard. The distance updates automatically.

## Context logic

A reminder triggers only when all configured conditions are true:

`Location AND Weather AND Battery AND Time`

Conditions that are left as **Any** are ignored. If a condition is selected but the browser/API cannot provide its current value, it does not pass.

## Automatic context limitations

- GPS is provided by the browser and requires user permission.
- Weather uses Open-Meteo based on the current coordinates.
- Place names use OpenStreetMap Nominatim.
- Browser battery access is not available in every browser. When unavailable, battery-based reminders will not trigger.
- A normal web page cannot guarantee geofencing after the page is completely closed. Keep the SmartRemind page open for live monitoring in this prototype.

## Install & Contribute (Quick Guide)

These steps help other developers run the project locally and push the code to GitHub.

1. Create a virtual environment and activate it:

Windows:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure database:
- For local MySQL: copy `.env.example` to `.env` and fill in your values.
- For quick local testing without MySQL, the app will fall back to a local SQLite database automatically (no config needed). Note: SQLite file is ignored by `.gitignore` and should not be committed.

4. Run the app:
```bash
cd SmartRemind
uvicorn main:app --reload
# open http://127.0.0.1:8000 in your browser
```

5. Create a GitHub repository and push your code (two options):

- Using the GitHub website:
	- Create a new repository on GitHub (do not initialize with README or .gitignore)
	- Then run locally:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

- Using the GitHub CLI (`gh`) (authenticated):
```bash
gh repo create YOUR_USERNAME/YOUR_REPO --public --source=. --remote=origin --push
```

Notes:
- `.env` and the local SQLite database are ignored by `.gitignore` to avoid committing secrets or local state.
- If you want me to create and push the GitHub repo for you, provide a GitHub repo URL or authenticate `gh` in this environment and I can run the `gh` command.

Thanks for preparing this project — happy to help create the remote repo and push if you want me to proceed.
