import os
import random
import time

import redis

from app.models import Pixel


class CoordinateStorage:
    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(self.redis_url)
        self.min_ttl = int(os.getenv("MIN_TTL_SECONDS", "3"))
        self.max_ttl = int(os.getenv("MAX_TTL_SECONDS", "10"))
        self.pixels_per_trigger = int(os.getenv("PIXELS_PER_TRIGGER", "70"))
        self.draw_probability = float(os.getenv("DRAW_PROBABILITY", "0.5"))

    def add_pixels(self, coords: list[dict], pixels_per_trigger: int | None = None) -> list[dict]:
        pixels = coords.copy()
        random.shuffle(pixels)

        limit = pixels_per_trigger if pixels_per_trigger is not None else self.pixels_per_trigger

        added = []
        for coord in pixels[:limit]:
            key = f"coords:{coord['y']}:{coord['x']}"

            if self.redis.exists(key):
                continue

            pixel = Pixel(
                x=coord["x"],
                y=coord["y"],
                color=coord["color"],
                draw=True,
                timestamp=int(time.time() * 1000),
                ttl=random.randint(self.min_ttl, self.max_ttl),
            )

            self.redis.hset(key, mapping=pixel.to_redis())
            self.redis.expire(key, pixel.ttl)

            added.append(pixel.model_dump())

        return added

    def add_all_pixels(self, coords: list[dict]) -> list[dict]:
        added = []
        for coord in coords:
            key = f"coords:{coord['y']}:{coord['x']}"

            if self.redis.exists(key):
                continue

            pixel = Pixel(
                x=coord["x"],
                y=coord["y"],
                color=coord["color"],
                draw=True,
                timestamp=int(time.time() * 1000),
                ttl=random.randint(5, 15),
            )

            self.redis.hset(key, mapping=pixel.to_redis())
            self.redis.expire(key, pixel.ttl)

            added.append(pixel.model_dump())

        return added

    def get_all_coords(self, max_x: int, max_y: int) -> list[dict]:
        coords = []
        for key in self.redis.scan_iter("coords:*"):
            data = self.redis.hgetall(key)
            pixel = Pixel.from_redis(data)

            if pixel.x < max_x and pixel.y < max_y:
                coords.append(pixel.model_dump())

        return coords

    def clear(self):
        self.redis.flushdb()

    def get_debug_info(self) -> dict:
        coords_with_ttl = []
        for key in self.redis.scan_iter("coords:*"):
            data = self.redis.hgetall(key)
            pixel = Pixel.from_redis(data)
            ttl_remaining = self.redis.ttl(key)

            pixel_dict = pixel.model_dump()
            pixel_dict["ttl_remaining"] = ttl_remaining if ttl_remaining > 0 else None
            coords_with_ttl.append(pixel_dict)

        return {
            "total_pixels": len(coords_with_ttl),
            "pixels": sorted(coords_with_ttl, key=lambda p: p["ttl_remaining"] if p["ttl_remaining"] else 999999),
        }

    def get_all_keys(self) -> set[str]:
        return {key.decode("utf-8") for key in self.redis.scan_iter("coords:*")}

    def set_current_figure(self, figure_name: str) -> None:
        self.redis.set("settings:current_figure", figure_name)

    def get_current_figure_name(self) -> str | None:
        value = self.redis.get("settings:current_figure")
        return value.decode("utf-8") if value else None

    def set_background_override(self, color: str) -> None:
        self.redis.set("settings:background_override", color)

    def get_background_override(self) -> str | None:
        value = self.redis.get("settings:background_override")
        return value.decode("utf-8") if value else None

    def clear_background_override(self) -> None:
        self.redis.delete("settings:background_override")

    def set_canvas_left_padding(self, padding: int) -> None:
        self.redis.set("settings:canvas_left_padding", padding)

    def get_canvas_left_padding(self) -> int:
        value = self.redis.get("settings:canvas_left_padding")
        return int(value) if value else 20
