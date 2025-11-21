import os
import random

import redis


class CoordinateStorage:
    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(self.redis_url)
        self.min_ttl = int(os.getenv("MIN_TTL_SECONDS", "3"))
        self.max_ttl = int(os.getenv("MAX_TTL_SECONDS", "10"))
        self.pixels_per_trigger = int(os.getenv("PIXELS_PER_TRIGGER", "70"))
        self.draw_probability = float(os.getenv("DRAW_PROBABILITY", "0.5"))

    def add_pixels(self, coords: list[dict], evaporate: bool = False) -> list[dict]:
        pixels = coords.copy()
        random.shuffle(pixels)

        limit = len(pixels) if not evaporate else self.pixels_per_trigger

        added = []
        for coord in pixels[:limit]:
            x, y, color = coord["x"], coord["y"], coord["color"]
            key = f"coords:{y}:{x}"

            if self.redis.exists(key):
                continue

            draw = not evaporate or random.random() < self.draw_probability
            value = {"x": x, "y": y, "color": color, "draw": int(draw)}

            self.redis.hset(key, mapping=value)
            if evaporate:
                ttl = random.randint(self.min_ttl, self.max_ttl)
                self.redis.expire(key, ttl)

            added.append({**value, "draw": bool(draw)})

        return added

    def get_all_coords(self, max_x: int, max_y: int) -> list[dict]:
        coords = []
        for key in self.redis.scan_iter("coords:*"):
            data = self.redis.hgetall(key)
            x = int(data[b"x"])
            y = int(data[b"y"])

            if x < max_x and y < max_y:
                coords.append(
                    {
                        "x": x,
                        "y": y,
                        "color": data[b"color"].decode("utf-8"),
                        "draw": bool(int(data[b"draw"])),
                    }
                )

        return coords

    def clear(self):
        self.redis.flushdb()

    def get_debug_info(self) -> dict:
        coords_with_ttl = []
        for key in self.redis.scan_iter("coords:*"):
            data = self.redis.hgetall(key)
            ttl = self.redis.ttl(key)
            coords_with_ttl.append(
                {
                    "x": int(data[b"x"]),
                    "y": int(data[b"y"]),
                    "color": data[b"color"].decode("utf-8"),
                    "draw": bool(int(data[b"draw"])),
                    "ttl": ttl if ttl > 0 else None,
                }
            )

        return {
            "total_pixels": len(coords_with_ttl),
            "pixels": sorted(coords_with_ttl, key=lambda p: p["ttl"] if p["ttl"] else 999999),
        }

    def get_all_keys(self) -> set[str]:
        return {key.decode("utf-8") for key in self.redis.scan_iter("coords:*")}
