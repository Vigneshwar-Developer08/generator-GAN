"""
Model loading and lifecycle management.

The Generator is loaded exactly once (at FastAPI startup, via the
lifespan handler in main.py) and held in memory for the lifetime of
the process. This module intentionally exposes a single module-level
singleton instance -- the ONE piece of deliberate global mutable
state allowed in this codebase -- because re-loading a GAN checkpoint
per-request would be prohibitively slow and is unnecessary since the
model is read-only after loading.
"""

import threading
import zipfile
from pathlib import Path

import torch

from app.core.config import Settings, get_settings
from app.core.exceptions import ModelFileNotFoundError, ModelLoadError, ModelNotReadyError
from app.core.generator_arch import Generator
from loguru import logger

_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)


def _is_pytorch_archive_dir(path: Path) -> bool:
    return path.is_dir() and (path / "data.pkl").exists() and (path / "version").exists()


def _pack_pytorch_archive(src_dir: Path, dest_file: Path) -> Path:
    """Repack an extracted PyTorch zip archive into a loadable .pth file."""
    prefix = src_dir.name
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(dest_file, "w", compression=zipfile.ZIP_STORED) as zf:
        for file_path in sorted(src_dir.rglob("*")):
            if not file_path.is_file():
                continue
            arcname = f"{prefix}/{file_path.relative_to(src_dir)}".replace("\\", "/")
            zinfo = zipfile.ZipInfo(arcname, _ZIP_DATE_TIME)
            zinfo.compress_type = zipfile.ZIP_STORED
            zf.writestr(zinfo, file_path.read_bytes())

    logger.info("Packed extracted checkpoint {} -> {}", src_dir, dest_file)
    return dest_file


def _resolve_checkpoint_path(model_path: Path) -> Path:
    """
    Resolve the checkpoint file to load.

    Accepts a .pth file directly, or an extracted PyTorch archive
    directory (e.g. generator_epoch_50/ with data.pkl inside). Archive
    directories are repacked into the configured .pth path on first use.
    """
    if model_path.is_file():
        return model_path

    search_roots: list[Path] = []
    if model_path.suffix:
        search_roots.append(model_path.parent / model_path.stem)
    search_roots.append(model_path.parent)

    archive_dirs: list[Path] = []
    for root in search_roots:
        if not root.is_dir():
            continue
        if _is_pytorch_archive_dir(root):
            archive_dirs.append(root)
        else:
            archive_dirs.extend(
                sorted(p for p in root.iterdir() if _is_pytorch_archive_dir(p))
            )

    if archive_dirs and model_path.suffix:
        return _pack_pytorch_archive(archive_dirs[0], model_path)

    if archive_dirs:
        return archive_dirs[0]

    return model_path


class ModelLoader:
    """
    Thread-safe holder for the loaded Generator model.

    `load()` is called once during the application lifespan startup.
    `get_model()` / `get_device()` are used by the service layer on
    every request; they raise ModelNotReadyError if called before
    `load()` has succeeded, instead of silently returning None.
    """

    def __init__(self) -> None:
        self._model: torch.nn.Module | None = None
        self._device: torch.device | None = None
        self._lock = threading.Lock()  # guards inference calls, see generator_service.py

    def load(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        model_path = _resolve_checkpoint_path(settings.model_path_resolved)

        if not model_path.exists():
            raise ModelFileNotFoundError(
                f"Generator checkpoint not found at '{model_path}'. "
                "Place the trained .pth file at that location before starting the server."
            )

        device = self._resolve_device(settings.FORCE_CPU)
        logger.info("Loading generator checkpoint from {} onto device={}", model_path, device)

        try:
            generator = Generator(
                latent_dim=settings.LATENT_DIM, ngf=settings.NGF, nc=settings.NC
            )
            state_dict = torch.load(model_path, map_location=device)
            generator.load_state_dict(state_dict)
            generator.to(device)
            generator.eval()  # inference mode: disables dropout/batchnorm updates
        except FileNotFoundError as exc:  # pragma: no cover - covered by existence check above
            raise ModelFileNotFoundError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - convert any torch load failure into domain error
            raise ModelLoadError(
                f"Failed to load generator checkpoint (possibly corrupted or "
                f"architecture mismatch): {exc}"
            ) from exc

        self._model = generator
        self._device = device
        logger.success("Generator model loaded successfully. device={}", device)

    def unload(self) -> None:
        """Release model resources on application shutdown."""
        self._model = None
        self._device = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Generator model unloaded.")

    @staticmethod
    def _resolve_device(force_cpu: bool) -> torch.device:
        if not force_cpu and torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def get_model(self) -> torch.nn.Module:
        if self._model is None:
            raise ModelNotReadyError("Model is not loaded yet. The server may still be starting up.")
        return self._model

    def get_device(self) -> torch.device:
        if self._device is None:
            raise ModelNotReadyError("Model is not loaded yet. The server may still be starting up.")
        return self._device

    @property
    def lock(self) -> threading.Lock:
        return self._lock


# Module-level singleton. Imported by generator_service.py and main.py.
model_loader = ModelLoader()
