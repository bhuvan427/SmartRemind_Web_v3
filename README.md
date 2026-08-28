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
- Python 3.10 or newer
- A modern browser with Geolocation support
- MySQL 8.x or compatible MySQL server for production use (optional for local testing)

## Installation

Clone the repository and enter its directory:

```bash
git clone https://github.com/bhuvan427/SmartRemind_Web_v3.git
cd SmartRemind_Web_v3
```

Create and activate a virtual environment:

Windows PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies listed in `requirements.txt`:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The dependency list includes:
- FastAPI: web API framework
- Uvicorn: application server
- MySQL Connector/Python: MySQL database support
- `python-dotenv`: environment configuration
- HTTPX: weather and geocoding API requests

## Database Configuration

### Option A: SQLite for quick local testing

No database setup is required. If MySQL is unavailable, the app automatically uses `smartremind.sqlite3`. This local database is ignored by Git.

### Option B: MySQL for production

Copy the example configuration file:

```bash
cp .env.example .env
```

On Windows PowerShell, use:
```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=smartremind
```

The app creates the database and tables automatically when the MySQL account has permission. Otherwise create the database first:

```sql
CREATE DATABASE smartremind CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Never commit `.env` or database files. They are excluded by `.gitignore`.

## Run

From the repository directory:

```bash
uvicorn main:app --reload
```

Open http://127.0.0.1:8000 in a browser and allow location and notification permissions. For deployment, use:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

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

## Contributing

1. Create a branch:
```bash
git checkout -b feature/your-change
```

2. Test the app locally, then commit your changes:
```bash
git add .
git commit -m "Describe your change"
```

3. Push the branch and open a pull request:
```bash
git push -u origin feature/your-change
```

