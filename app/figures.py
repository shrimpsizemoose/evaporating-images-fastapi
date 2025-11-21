import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Figure:
    name: str
    colors: dict[str, str | None]
    points: list[list[str]]

    @classmethod
    def from_json(cls, filepath: str | Path) -> "Figure":
        with open(filepath) as f:
            data = json.load(f)
        return cls(name=data["name"], colors=data["colors"], points=data["points"])

    def get_coords(self, shift_x: int = 0, shift_y: int = 0) -> list[dict]:
        coords = []
        for row_idx, row in enumerate(self.points):
            for col_idx, color_key in enumerate(row):
                color = self.colors.get(color_key)
                if color is not None:
                    coords.append(
                        {"x": col_idx + shift_x, "y": row_idx + shift_y, "color": color}
                    )
        return coords


def load_figure(figures_dir: str, figure_name: str) -> Figure:
    filepath = Path(figures_dir) / f"{figure_name}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Figure file not found: {filepath}")
    return Figure.from_json(filepath)


def get_current_figure(override_name: str | None = None) -> Figure:
    figures_dir = os.getenv("FIGURES_DIR", "figures")
    current_figure = override_name or os.getenv("CURRENT_FIGURE", "moose")
    return load_figure(figures_dir, current_figure)


def list_available_figures() -> list[dict]:
    figures_dir = Path(os.getenv("FIGURES_DIR", "figures"))
    figures = []
    for filepath in figures_dir.glob("*.json"):
        try:
            figure = Figure.from_json(filepath)
            figures.append({"name": figure.name, "filename": filepath.stem})
        except Exception:
            continue
    return figures
