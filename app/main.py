import asyncio
import os

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.figures import get_current_figure, list_available_figures
from app.storage import CoordinateStorage
from app.websocket_manager import manager

storage = CoordinateStorage()


async def monitor_expiring_pixels():
    previous_keys = storage.get_all_keys()

    while True:
        await asyncio.sleep(0.5)
        current_keys = storage.get_all_keys()
        expired_keys = previous_keys - current_keys

        if expired_keys:
            expired_coords = []
            for key in expired_keys:
                parts = key.split(":")
                if len(parts) == 3:
                    y, x = int(parts[1]), int(parts[2])
                    expired_coords.append({"x": x, "y": y})

            if expired_coords:
                await manager.broadcast({"type": "pixels_removed", "coords": expired_coords})

        previous_keys = current_keys


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(monitor_expiring_pixels())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/figures", StaticFiles(directory="figures"), name="figures")


@app.get("/")
async def serve_index():
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/admin")
async def serve_admin():
    with open("static/admin.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/trigger")
async def serve_trigger():
    with open("static/trigger.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/coords")
async def get_coords():
    current_figure_name = storage.get_current_figure_name()
    figure = get_current_figure(override_name=current_figure_name)
    coords = storage.get_all_coords(max_x=figure.grid_width, max_y=figure.grid_height)
    return JSONResponse(content={"coords": coords})


@app.post("/api/trigger")
async def trigger():
    current_figure_name = storage.get_current_figure_name()
    figure = get_current_figure(override_name=current_figure_name)
    coords = figure.get_coords(shift_x=figure.shift_x, shift_y=figure.shift_y)
    pixels_per_trigger = figure.get_pixels_per_trigger()

    added = storage.add_pixels(coords, pixels_per_trigger=pixels_per_trigger)

    await manager.broadcast({"type": "pixels_added", "coords": added})

    return JSONResponse(content={"message": "Pixels added", "count": len(added)})


@app.post("/api/full")
async def full():
    current_figure_name = storage.get_current_figure_name()
    figure = get_current_figure(override_name=current_figure_name)
    coords = figure.get_coords(shift_x=figure.shift_x, shift_y=figure.shift_y)

    added = storage.add_all_pixels(coords)

    await manager.broadcast({"type": "pixels_added", "coords": added})

    return JSONResponse(content={"message": "Full image loaded", "count": len(added)})


@app.post("/api/clear")
async def clear():
    storage.clear()

    await manager.broadcast({"type": "clear"})

    return JSONResponse(content={"message": "Grid cleared"})


@app.get("/api/debug")
async def debug():
    debug_info = storage.get_debug_info()
    return JSONResponse(content=debug_info)


@app.get("/api/figures")
async def get_figures():
    figures = list_available_figures()
    current = storage.get_current_figure_name()
    return JSONResponse(content={"figures": figures, "current": current})


@app.get("/api/figure-settings")
async def get_figure_settings():
    current_figure_name = storage.get_current_figure_name()
    figure = get_current_figure(override_name=current_figure_name)
    background_override = storage.get_background_override()
    background = background_override if background_override else figure.background_color
    canvas_left_padding = storage.get_canvas_left_padding()

    return JSONResponse(content={
        "name": figure.name,
        "grid_width": figure.grid_width,
        "grid_height": figure.grid_height,
        "shift_x": figure.shift_x,
        "shift_y": figure.shift_y,
        "background_color": background,
        "default_background": figure.background_color,
        "canvas_left_padding": canvas_left_padding,
        "is_override": background_override is not None,
    })


@app.post("/api/set-figure")
async def set_figure(request: dict):
    figure_name = request.get("figure")
    if not figure_name:
        return JSONResponse(content={"error": "Missing figure name"}, status_code=400)

    try:
        figure = get_current_figure(override_name=figure_name)
        storage.set_current_figure(figure_name)

        background_override = storage.get_background_override()
        background = background_override if background_override else figure.background_color

        await manager.broadcast({
            "type": "figure_changed",
            "figure": {
                "name": figure.name,
                "grid_width": figure.grid_width,
                "grid_height": figure.grid_height,
                "shift_x": figure.shift_x,
                "shift_y": figure.shift_y,
                "background_color": background,
            }
        })

        return JSONResponse(content={"message": f"Figure set to {figure_name}", "figure": figure_name})
    except FileNotFoundError:
        return JSONResponse(content={"error": "Figure not found"}, status_code=404)


@app.post("/api/set-background")
async def set_background(request: dict):
    color = request.get("color")

    if color == "auto":
        storage.clear_background_override()
        current_figure_name = storage.get_current_figure_name()
        figure = get_current_figure(override_name=current_figure_name)
        actual_color = figure.background_color
    else:
        if not color:
            return JSONResponse(content={"error": "Missing color"}, status_code=400)
        storage.set_background_override(color)
        actual_color = color

    await manager.broadcast({
        "type": "background_changed",
        "background_color": actual_color
    })

    return JSONResponse(content={"message": "Background updated", "color": actual_color})


@app.post("/api/set-canvas-padding")
async def set_canvas_padding(request: dict):
    padding = request.get("padding")

    if padding is None:
        return JSONResponse(content={"error": "Missing padding value"}, status_code=400)

    try:
        padding_int = int(padding)
        if padding_int < 0 or padding_int > 1600:
            return JSONResponse(content={"error": "Padding must be between 0 and 1600"}, status_code=400)

        storage.set_canvas_left_padding(padding_int)

        await manager.broadcast({
            "type": "padding_changed",
            "left": padding_int
        })

        return JSONResponse(content={"message": "Canvas padding updated", "padding": padding_int})
    except ValueError:
        return JSONResponse(content={"error": "Invalid padding value"}, status_code=400)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
