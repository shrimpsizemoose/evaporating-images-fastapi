#!/usr/bin/env python3
"""Convert a pixel-perfect image to figure JSON without any resizing or color quantization."""

import json
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image


def rgb_to_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def rgba_to_hex(rgba):
    # removes transparent
    if len(rgba) == 4 and rgba[3] < 128:
        return None
    return rgb_to_hex(rgba[:3])


def pixel_perfect_convert(
    image_path,
    output_path,
    name=None,
    padding=5,
    background_color=None,
):
    if name is None:
        name = Path(output_path).stem

    print(f"Loading image: {image_path}")
    img = Image.open(image_path)

    if img.mode == "P":
        img = img.convert("RGBA")
    elif img.mode == "RGB":
        img = img.convert("RGBA")

    width, height = img.size
    print(f"Image size: {width}x{height}")

    color_map = {}
    color_frequency = defaultdict(int)
    points = []

    for y in range(height):
        row = []
        for x in range(width):
            pixel = img.getpixel((x, y))
            hex_color = rgba_to_hex(pixel)

            if hex_color is None:
                row.append(None)
            else:
                if hex_color not in color_map:
                    color_map[hex_color] = len(color_map)
                row.append(hex_color)
                color_frequency[hex_color] += 1
        points.append(row)

    if background_color is None:
        # most common color as background
        if color_frequency:
            background_color = max(color_frequency.items(), key=lambda x: x[1])[0]
        else:
            background_color = "#7bd7f4"  # Default light blue

    print(f"Found {len(color_map)} unique colors")
    print(f"Background color: {background_color}")

    # Create color mapping with letter keys
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if len(color_map) > len(letters):
        print(
            f"Warning: Image has {len(color_map)} colors, but only {len(letters)} letters available"
        )
        print("Consider reducing color count or extending letter range")

    # sort colors by frequency (most common first)
    sorted_colors = sorted(
        color_map.keys(), key=lambda c: color_frequency[c], reverse=True
    )
    color_to_letter = {}
    for i, color in enumerate(sorted_colors[: len(letters)]):
        color_to_letter[color] = letters[i]

    colors = {"_": None}
    for color, letter in color_to_letter.items():
        colors[letter] = color

    # convert points to letters
    letter_points = []
    for row in points:
        letter_row = []
        for pixel in row:
            if pixel is None:
                letter_row.append("_")
            else:
                letter_row.append(color_to_letter.get(pixel, "_"))
        letter_points.append(letter_row)

    # calculate display grid with padding
    display_width = width + padding * 2
    display_height = height + padding * 2

    figure_data = {
        "name": name,
        "grid_width": display_width,
        "grid_height": display_height,
        "shift_x": padding,
        "shift_y": padding,
        "background_color": background_color,
        "colors": colors,
        "points": letter_points,
    }

    with open(output_path, "w") as f:
        json.dump(figure_data, f, indent=2)

    print(f"\nCreated pixel-perfect figure: {output_path}")
    print(f"Figure size: {width}x{height}")
    print(f"Display grid: {display_width}x{display_height}")
    print(f"Position: ({padding}, {padding})")
    print(f"Colors used: {len(colors) - 1}")  # -1 for the "_" key
    print("\nColor palette:")
    for key, color in sorted(colors.items()):
        if color:
            count = color_frequency.get(color, 0)
            print(f"  {key}: {color} ({count} pixels)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python pixel_perfect_convert.py <image_path> [output_path] [name] [padding] [background_color]"
        )
        print("\nExample:")
        print(
            "  python pixel_perfect_convert.py flower-queen.png figures/flower_queen.json"
        )
        print("\nDefaults:")
        print("  output_path: figures/<image_name>.json")
        print("  name: output filename stem")
        print("  padding: 5")
        print("  background_color: auto-detected (most common color)")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = (
        sys.argv[2] if len(sys.argv) > 2 else f"figures/{Path(image_path).stem}.json"
    )
    name = sys.argv[3] if len(sys.argv) > 3 else None
    padding = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    background_color = sys.argv[5] if len(sys.argv) > 5 else None

    pixel_perfect_convert(image_path, output_path, name, padding, background_color)
