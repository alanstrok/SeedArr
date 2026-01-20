# SeedArr - Intelligent Seeding Manager

SeedArr is a web application for intelligent torrent seeding management, integrated with the *arr ecosystem (Sonarr, Radarr, Prowlarr) and qBittorrent. It provides a complete UI alternative to qbit_manage with dynamic rules per tracker.

## Features

- **Rule-Based Management**: Create flexible rules with conditions, criteria, and exceptions
- **Tracker Support**: Auto-discover trackers from qBittorrent and Prowlarr
- **Protection System**: Protect torrents by category, tags, or individually
- **Scheduled Scans**: Automatic scanning with configurable intervals
- **Dry-Run Mode**: Test rules without making changes
- **Action Logging**: Complete history of all actions taken
- **Notifications**: Discord and Telegram support
- **Backup/Restore**: Export and import your configuration

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/seedarr.git
cd seedarr

# Create config directory
mkdir -p config

# Start the application
docker-compose up -d

# Access the UI at http://localhost:8585
```

### Using Single Docker Container

```bash
docker build -t seedarr .
docker run -d \
  --name seedarr \
  -p 8585:8585 \
  -v $(pwd)/config:/config \
  -e TZ=America/Martinique \
  seedarr
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TZ` | Timezone | `America/Martinique` |
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:///config/seedarr.db` |
| `SECRET_KEY` | Encryption key for passwords | `change-this-in-production` |

### First Setup

1. Navigate to **Connections** and add your qBittorrent instance
2. Go to **Trackers** and click **Discover** to auto-detect trackers
3. Create **Rules** to define your seeding criteria
4. Configure **Settings** for scan intervals and protection

## Rule Configuration

### Conditions (Which torrents to match)
- Specific trackers or all
- Categories (tv, movies, etc.)
- Tags
- Size range

### Criteria (When to take action)
- Minimum seed time
- Minimum ratio
- Maximum seed time
- AND/OR operator for multiple conditions

### Exceptions (Do not act if)
- Seeders below threshold (protect rare torrents)
- Recent activity

### Actions
- **Delete**: Remove torrent and files
- **Delete (keep files)**: Remove torrent only
- **Pause**: Stop seeding
- **Tag**: Add a tag

## API Documentation

API documentation is available at `/docs` (Swagger UI) or `/redoc` (ReDoc).

## Development

### Backend (Python/FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8585
```

### Frontend (Vue.js/Vuetify)

```bash
cd frontend
npm install
npm run dev
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, APScheduler
- **Frontend**: Vue.js 3, Vuetify 3, Pinia, Vite
- **Database**: SQLite
- **Deployment**: Docker

## License

MIT License
