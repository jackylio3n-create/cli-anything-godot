"""Helpers for lightweight procedural assets and .import sidecars."""

from __future__ import annotations

from pathlib import Path
import hashlib
import math
import struct
import wave
import zlib
from typing import Any, Iterable

from .project import GodotConfig, format_variant


def _write_png_rgba(
    output_file: str | Path,
    width: int,
    height: int,
    pixels_rgba: Iterable[tuple[int, int, int, int]],
) -> Path:
    if width < 1 or height < 1:
        raise ValueError(f"PNG dimensions must be positive, got {width}x{height}")

    p = Path(output_file)
    p.parent.mkdir(parents=True, exist_ok=True)

    row_bytes = bytearray()
    pixel_iter = iter(pixels_rgba)
    for _y in range(height):
        row_bytes.append(0)  # filter type 0 (None)
        for _x in range(width):
            r, g, b, a = next(pixel_iter)
            row_bytes.extend((r & 0xFF, g & 0xFF, b & 0xFF, a & 0xFF))
    compressed = zlib.compress(bytes(row_bytes), level=9)

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # RGBA
    png_data = header + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    p.write_bytes(png_data)
    return p


def create_solid_color_png(
    output_file: str | Path,
    *,
    width: int = 256,
    height: int = 256,
    color: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> Path:
    """Create a flat-color RGBA PNG without external dependencies."""
    pixels = [color] * (width * height)
    return _write_png_rgba(output_file, width, height, pixels)


def create_checkerboard_png(
    output_file: str | Path,
    *,
    width: int = 256,
    height: int = 256,
    cell_size: int = 16,
    color_a: tuple[int, int, int, int] = (220, 220, 220, 255),
    color_b: tuple[int, int, int, int] = (120, 120, 120, 255),
) -> Path:
    """Create a procedural checkerboard texture."""
    if cell_size < 1:
        raise ValueError(f"cell_size must be >= 1, got {cell_size}")
    pixels: list[tuple[int, int, int, int]] = []
    for y in range(height):
        for x in range(width):
            use_a = ((x // cell_size) + (y // cell_size)) % 2 == 0
            pixels.append(color_a if use_a else color_b)
    return _write_png_rgba(output_file, width, height, pixels)


def _default_uid(seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:20]
    return f"uid://{digest}"


def write_import_file(
    project_dir: str | Path,
    asset_file: str | Path,
    *,
    importer: str = "texture",
    resource_type: str = "CompressedTexture2D",
    uid: str | None = None,
    params: dict[str, Any] | None = None,
) -> Path:
    """Write a deterministic ``.import`` sidecar for an asset file."""
    root = Path(project_dir).resolve()
    asset_path = Path(asset_file).resolve()
    rel_asset = asset_path.relative_to(root).as_posix()
    res_path = f"res://{rel_asset}"

    cfg = GodotConfig()
    cfg.set("remap", "importer", format_variant(importer))
    cfg.set("remap", "type", format_variant(resource_type))
    cfg.set("remap", "uid", format_variant(uid or _default_uid(res_path)))
    cfg.set("deps", "source_file", format_variant(res_path))
    cfg.set("deps", "dest_files", "[]")
    for key, value in sorted((params or {}).items()):
        cfg.set("params", key, format_variant(value))

    import_file = Path(f"{asset_path}.import")
    return cfg.save(import_file)


def _hex_to_rgba(color: str) -> tuple[int, int, int, int]:
    value = color.strip().lstrip("#")
    if len(value) == 6:
        value += "ff"
    if len(value) != 8:
        raise ValueError(f"Unsupported color format: {color}")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4, 6))  # type: ignore[return-value]


def create_procedural_sprite(path, shape="square", color="#6fa8ff", size=128):
    """Requested API: write a simple procedural sprite PNG."""
    if size < 1:
        raise ValueError(f"size must be >= 1, got {size}")
    rgba = _hex_to_rgba(color)
    transparent = (0, 0, 0, 0)
    shape_name = shape.lower().strip()

    pixels: list[tuple[int, int, int, int]] = []
    center = (size - 1) / 2.0
    radius = size / 2.0
    for y in range(size):
        for x in range(size):
            if shape_name == "square":
                pixels.append(rgba)
            elif shape_name == "circle":
                distance = math.hypot(x - center, y - center)
                pixels.append(rgba if distance <= radius else transparent)
            elif shape_name == "triangle":
                if y == 0:
                    pixels.append(rgba if x == int(center) else transparent)
                    continue
                left = center - (y / (size - 1)) * center
                right = center + (y / (size - 1)) * center
                pixels.append(rgba if left <= x <= right else transparent)
            else:
                raise ValueError(f"Unsupported shape: {shape}")

    return _write_png_rgba(path, size, size, pixels)


def create_procedural_tone(path, frequency=440, duration_ms=250):
    """Requested API: write a simple mono WAV tone without external tools."""
    sample_rate = 44100
    sample_count = max(1, int(sample_rate * (duration_ms / 1000.0)))
    amplitude = 0.35
    fade_samples = max(1, int(sample_rate * 0.01))
    pcm = bytearray()
    for i in range(sample_count):
        sample = math.sin(2.0 * math.pi * float(frequency) * (i / sample_rate))
        # Apply short linear fade-in/out to avoid clicks.
        gain = 1.0
        if i < fade_samples:
            gain = i / fade_samples
        elif i > sample_count - fade_samples:
            gain = max(0.0, (sample_count - i) / fade_samples)
        value = int(max(-1.0, min(1.0, sample * amplitude * gain)) * 32767)
        pcm.extend(struct.pack("<h", value))

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(pcm))
    return output
