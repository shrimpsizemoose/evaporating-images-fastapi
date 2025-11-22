#!/usr/bin/env python3
"""Convert an image to a figure JSON file for evaporating-images."""

import json
import sys
from pathlib import Path

from PIL import Image
from sklearn.cluster import KMeans
import numpy as np


def rgb_to_hex(rgb):
    """Convert RGB tuple to hex color string."""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def euclidean_distance(c1, c2):
    """Calculate euclidean distance between two RGB colors."""
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def quantize_colors(image_path, num_colors=8, transparent_threshold=240):
    """Extract dominant colors from image using k-means clustering.

    Args:
        image_path: Path to input image
        num_colors: Number of colors to extract
        transparent_threshold: RGB value threshold for treating as transparent (e.g., 240 for near-white)

    Returns:
        List of hex color strings
    """
    img = Image.open(image_path).convert('RGB')
    pixels = np.array(img).reshape(-1, 3)

    # Filter out very light pixels (likely background)
    mask = ~np.all(pixels > transparent_threshold, axis=1)
    filtered_pixels = pixels[mask]

    if len(filtered_pixels) == 0:
        filtered_pixels = pixels

    kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=10)
    kmeans.fit(filtered_pixels)

    colors = kmeans.cluster_centers_.astype(int)
    hex_colors = [rgb_to_hex(tuple(color)) for color in colors]

    return hex_colors


def resize_and_pixelate(image_path, grid_size=25):
    """Resize image to grid and get pixel colors.

    Args:
        image_path: Path to input image
        grid_size: Target grid dimensions (width and height)

    Returns:
        2D array of RGB tuples
    """
    img = Image.open(image_path).convert('RGB')
    img_resized = img.resize((grid_size, grid_size), Image.LANCZOS)

    pixels = []
    for y in range(grid_size):
        row = []
        for x in range(grid_size):
            rgb = img_resized.getpixel((x, y))
            row.append(rgb)
        pixels.append(row)

    return pixels


def map_to_palette(pixels, palette, transparent_color=None):
    """Map pixel colors to nearest palette color.

    Args:
        pixels: 2D array of RGB tuples
        palette: List of hex color strings
        transparent_color: RGB tuple to treat as transparent (None)

    Returns:
        2D array of palette indices
    """
    palette_rgb = [hex_to_rgb(c) for c in palette]

    mapped = []
    for row in pixels:
        mapped_row = []
        for pixel in row:
            if transparent_color and euclidean_distance(pixel, transparent_color) < 30:
                mapped_row.append(None)
            else:
                distances = [euclidean_distance(pixel, p) for p in palette_rgb]
                closest_idx = distances.index(min(distances))
                mapped_row.append(closest_idx)
        mapped.append(mapped_row)

    return mapped


def create_figure_json(image_path, output_path, grid_size=25, num_colors=8, name=None, display_grid_size=None, shift_x=None, shift_y=None):
    """Convert image to figure JSON file.

    Args:
        image_path: Path to input image
        output_path: Path to output JSON file
        grid_size: Grid dimensions for the figure
        num_colors: Number of colors in palette
        name: Figure name (defaults to output filename stem)
        display_grid_size: Display grid size (defaults to grid_size + 5)
        shift_x: Horizontal shift (defaults to centering)
        shift_y: Vertical shift (defaults to centering)
    """
    if name is None:
        name = Path(output_path).stem

    print(f"Extracting {num_colors} colors from image...")
    palette = quantize_colors(image_path, num_colors)

    print(f"Resizing to {grid_size}x{grid_size} grid...")
    pixels = resize_and_pixelate(image_path, grid_size)

    print("Mapping pixels to palette...")
    mapped = map_to_palette(pixels, palette)

    # Calculate display grid and centering
    if display_grid_size is None:
        display_grid_size = grid_size + 5

    if shift_x is None:
        shift_x = (display_grid_size - grid_size) // 2

    if shift_y is None:
        shift_y = (display_grid_size - grid_size) // 2

    # Create color mapping with letter keys
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    colors = {"_": None}
    for i, color in enumerate(palette[:len(letters)]):
        colors[letters[i]] = color

    # Convert mapped indices to letter keys
    points = []
    for row in mapped:
        point_row = []
        for val in row:
            if val is None:
                point_row.append("_")
            else:
                point_row.append(letters[val])
        points.append(point_row)

    figure_data = {
        "name": name,
        "grid_width": display_grid_size,
        "grid_height": display_grid_size,
        "shift_x": shift_x,
        "shift_y": shift_y,
        "colors": colors,
        "points": points
    }

    with open(output_path, 'w') as f:
        json.dump(figure_data, f, indent=2)

    print(f"\nCreated figure: {output_path}")
    print(f"Figure size: {grid_size}x{grid_size}")
    print(f"Display grid: {display_grid_size}x{display_grid_size}")
    print(f"Position: ({shift_x}, {shift_y})")
    print(f"Colors used: {num_colors}")
    print(f"\nPalette:")
    for key, color in colors.items():
        if color:
            print(f"  {key}: {color}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python image_to_figure.py <image_path> [output_path] [grid_size] [num_colors] [name]")
        print("\nExample:")
        print("  python image_to_figure.py flower.png figures/flower.json 25 8 'queen_of_night'")
        print("\nDefaults:")
        print("  output_path: figures/<image_name>.json")
        print("  grid_size: 25")
        print("  num_colors: 8")
        print("  name: output filename stem")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"figures/{Path(image_path).stem}.json"
    grid_size = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    num_colors = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    name = sys.argv[5] if len(sys.argv) > 5 else None

    create_figure_json(image_path, output_path, grid_size, num_colors, name)
