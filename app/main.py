import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.figures import get_current_figure
from app.storage import CoordinateStorage
from app.websocket_manager import manager

app = FastAPI()

storage = CoordinateStorage()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_index():
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/admin")
async def serve_admin():
    with open("static/admin.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/coords")
async def get_coords():
    max_x = int(os.getenv("GRID_WIDTH", "25"))
    max_y = int(os.getenv("GRID_HEIGHT", "25"))
    coords = storage.get_all_coords(max_x=max_x, max_y=max_y)
    return JSONResponse(content={"coords": coords})


@app.post("/api/trigger")
async def trigger():
    figure = get_current_figure()
    shift_x = int(os.getenv("FIGURE_SHIFT_X", "7"))
    shift_y = int(os.getenv("FIGURE_SHIFT_Y", "5"))
    coords = figure.get_coords(shift_x=shift_x, shift_y=shift_y)

    added = storage.add_pixels(coords, evaporate=True)

    await manager.broadcast({"type": "pixels_added", "coords": added})

    return JSONResponse(content={"message": "Pixels added", "count": len(added)})


@app.post("/api/full")
async def full():
    figure = get_current_figure()
    shift_x = int(os.getenv("FIGURE_SHIFT_X", "7"))
    shift_y = int(os.getenv("FIGURE_SHIFT_Y", "5"))
    coords = figure.get_coords(shift_x=shift_x, shift_y=shift_y)

    added = storage.add_pixels(coords, evaporate=False)

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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
