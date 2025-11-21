# Evaporating Images

A real-time pixel art animation system with evaporating pixels. Built with FastAPI, WebSockets, and Redis.

## Quick Start

### Using Docker (recommended)

```bash
docker-compose up -d
```

Access at:
- Main view: `http://localhost:8080`
- Admin panel: `http://localhost:8080/admin`

### Local development

1. Start Redis:
   ```bash
   redis-server
   ```

2. Install dependencies and run:
   ```bash
   uv sync
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
   ```

### VPS Deployment with Caddy

1. Copy `Caddyfile` to `/etc/caddy/Caddyfile`
2. Run with Docker Compose:
   ```bash
   docker-compose up -d
   ```
3. Caddy will handle SSL automatically

## Features

- Real-time pixel updates via WebSockets
- Configurable pixel art figures (JSON format)
- Mobile-friendly admin panel
- Evaporating animation with configurable TTL
- Redis-backed coordinate storage

## API Endpoints

- `GET /` - Main canvas view
- `GET /admin` - Mobile admin panel
- `GET /api/coords` - Get current grid state
- `POST /api/trigger` - Add evaporating pixels
- `POST /api/full` - Show full image
- `POST /api/clear` - Clear grid
- `WebSocket /ws` - Real-time pixel updates

## Configuration

Set via environment variables:

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Figure settings
FIGURES_DIR=figures
CURRENT_FIGURE=moose
FIGURE_SHIFT_X=7
FIGURE_SHIFT_Y=5

# Grid dimensions
GRID_WIDTH=25
GRID_HEIGHT=25

# Animation settings
PIXELS_PER_TRIGGER=70
DRAW_PROBABILITY=0.5
MIN_TTL_SECONDS=3
MAX_TTL_SECONDS=10
```

## Adding New Figures

Create a JSON file in the `figures/` directory:

```json
{
  "name": "example",
  "colors": {
    "K": "black",
    "O": "#ffa500",
    "_": null
  },
  "points": [
    ["_", "_", "_", "_", "_"],
    ["_", "_", "_", "O", "_"],
    ["_", "_", "K", "_", "_"],
    ["_", "_", "K", "O", "_"],
    ["_", "_", "_", "_", "_"]
  ]
}
```

Then set `CURRENT_FIGURE=example` to use it.

## Testing

Trigger from command line:
```bash
curl -X POST http://localhost:8080/api/trigger
```
