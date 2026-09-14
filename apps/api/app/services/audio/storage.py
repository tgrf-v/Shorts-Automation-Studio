import os
import re
import uuid
import shutil
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path


class BaseAudioStorage(ABC):
    """Abstract interface for audio storage (Local filesystem or future Cloudflare R2)."""

    @abstractmethod
    async def save_file(self, content: bytes, project_id: Optional[uuid.UUID], filename: str) -> str:
        """Saves audio file content and returns stored file path/identifier."""
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Deletes audio file if it exists."""
        pass

    @abstractmethod
    def get_absolute_path(self, file_path: str) -> str:
        """Resolves the physical absolute path for file reading or inspection."""
        pass


class LocalAudioStorage(BaseAudioStorage):
    """
    Local filesystem storage implementation for audio assets.
    Persists audio files under storage/audio_assets/{project_id or 'shared'}/
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir:
            self.base_dir = os.path.abspath(base_dir)
        else:
            # Default to repo root / storage / audio_assets
            app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
            self.base_dir = os.path.join(app_root, "storage", "audio_assets")
        os.makedirs(self.base_dir, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
        return clean.strip('._') or "audio_track"

    async def save_file(self, content: bytes, project_id: Optional[uuid.UUID], filename: str) -> str:
        folder_name = str(project_id) if project_id else "shared"
        target_dir = os.path.join(self.base_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        clean_name = self._sanitize_filename(filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{clean_name}"
        full_path = os.path.join(target_dir, unique_name)

        with open(full_path, "wb") as f:
            f.write(content)

        return full_path

    async def delete_file(self, file_path: str) -> bool:
        if not file_path:
            return False
        abs_path = self.get_absolute_path(file_path)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
                return True
            except Exception:
                return False
        return False

    def get_absolute_path(self, file_path: str) -> str:
        if os.path.isabs(file_path):
            return file_path
        return os.path.abspath(os.path.join(self.base_dir, file_path))
