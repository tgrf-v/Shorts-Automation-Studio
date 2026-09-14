from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RawCandidateItem(BaseModel):
    """Normalized video candidate returned from search providers."""
    title: str = Field(..., description="Video title or heading")
    url: str = Field(..., description="Primary web page or canonical video URL")
    video_url: Optional[str] = Field(default=None, description="Direct video streaming URL if available")
    thumbnail_url: Optional[str] = Field(default=None, description="Image thumbnail URL for visual matching")
    platform: str = Field(default="web", description="Platform identifier (youtube, web, pexels, etc.)")
    description: Optional[str] = Field(default=None, description="Video description snippet")
    creator: Optional[str] = Field(default=None, description="Channel, author, or uploader username")
    duration: Optional[float] = Field(default=None, description="Video duration in seconds")
    published_at: Optional[str] = Field(default=None, description="Publication timestamp or date string")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific raw metadata")


class FootageSearchProvider(ABC):
    """Abstract Base Class defining the contract for internet footage search providers."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> List[RawCandidateItem]:
        """
        Executes a search for candidate video footage matching the given query.
        Returns normalized candidate items.
        """
        pass
