"""
Utilities for converting generator output tensors into saved image files,
and for safely handling user-supplied filenames (path traversal defense).
"""

import re
import uuid
from pathlib import Path

import torch
from PIL import Image
from torchvision import utils as vutils

from app.core.exceptions import InvalidFilenameError

# Only lowercase hex UUID-style filenames + .png are ever accepted back in.
_SAFE_FILENAME_PATTERN = re.compile(r"^[a-f0-9]{8,32}\.png$")


def generate_filename() -> str:
    """Generate a short, collision-resistant, URL-safe filename."""
    return f"{uuid.uuid4().hex[:8]}.png"


def tensor_to_image(tensor: torch.Tensor) -> Image.Image:
    """
    Convert a single generator output tensor (1, C, H, W), range [-1, 1],
    into a PIL RGB image, range [0, 255].
    """
    if tensor.dim() != 4 or tensor.size(0) != 1:
        raise ValueError(f"Expected tensor shape (1, C, H, W), got {tuple(tensor.shape)}")

    # make_grid with normalize handles the [-1, 1] -> [0, 1] rescaling for us.
    grid = vutils.make_grid(tensor, normalize=True, value_range=(-1, 1), nrow=1, padding=0)
    array = grid.mul(255).clamp(0, 255).byte().permute(1, 2, 0).cpu().numpy()
    return Image.fromarray(array, mode="RGB")


def save_image(image: Image.Image, filename: str, generated_dir: Path, image_format: str = "PNG") -> Path:
    """Persist a PIL image to disk under generated_dir and return its full path."""
    validate_filename(filename)
    file_path = generated_dir / filename
    image.save(file_path, format=image_format)
    return file_path


def validate_filename(filename: str) -> None:
    """
    Ensure a filename is exactly the shape we generate ourselves
    (hex-uuid + .png), rejecting anything else. This blocks path
    traversal (`../../etc/passwd`), absolute paths, hidden files,
    and unexpected extensions in one check.
    """
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise InvalidFilenameError(f"Invalid filename: '{filename}'")
    if not _SAFE_FILENAME_PATTERN.match(filename):
        raise InvalidFilenameError(f"Filename does not match expected pattern: '{filename}'")


def resolve_safe_path(filename: str, generated_dir: Path) -> Path:
    """
    Validate the filename, then resolve it and double-check the resolved
    path is still inside generated_dir (defense in depth against symlink
    or resolution tricks).
    """
    validate_filename(filename)
    candidate = (generated_dir / filename).resolve()
    if generated_dir.resolve() not in candidate.parents and candidate.parent != generated_dir.resolve():
        raise InvalidFilenameError("Resolved path escapes the generated images directory.")
    return candidate
