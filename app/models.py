from pydantic import BaseModel


class Pixel(BaseModel):
    x: int
    y: int
    color: str
    draw: bool = True
    timestamp: int
    ttl: int

    def to_redis(self) -> dict[str, int | str]:
        return {
            "x": self.x,
            "y": self.y,
            "color": self.color,
            "draw": int(self.draw),
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_redis(cls, data: dict[bytes, bytes]) -> "Pixel":
        return cls(
            x=int(data[b"x"]),
            y=int(data[b"y"]),
            color=data[b"color"].decode("utf-8"),
            draw=bool(int(data[b"draw"])),
            timestamp=int(data[b"timestamp"]) if b"timestamp" in data else 0,
            ttl=int(data[b"ttl"]) if b"ttl" in data else 0,
        )
