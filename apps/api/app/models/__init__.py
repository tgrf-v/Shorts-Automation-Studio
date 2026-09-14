from app.core.database import Base
from app.models.project import Project, ProjectStatus
from app.models.media_asset import MediaAsset, MediaAssetType
from app.models.transcript import Transcript
from app.models.scene import Scene
from app.models.keyframe import Keyframe
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus, AnalysisJobStep
from app.models.script import Script, ScriptStatus
from app.models.script_job import ScriptJob, ScriptJobStatus, ScriptJobStep
from app.models.tts_generation import TTSGeneration, TTSStatus
from app.models.audio_segment import AudioSegment
from app.models.tts_job import TTSJob, TTSJobStatus, TTSJobStep
from app.models.footage_search import FootageSearch, FootageSearchStatus
from app.models.footage_candidate import FootageCandidate
from app.models.scene_footage_selection import SceneFootageSelection

__all__ = [
    "Base",
    "Project",
    "ProjectStatus",
    "MediaAsset",
    "MediaAssetType",
    "Transcript",
    "Scene",
    "Keyframe",
    "AnalysisJob",
    "AnalysisJobStatus",
    "AnalysisJobStep",
    "Script",
    "ScriptStatus",
    "ScriptJob",
    "ScriptJobStatus",
    "ScriptJobStep",
    "TTSGeneration",
    "TTSStatus",
    "AudioSegment",
    "TTSJob",
    "TTSJobStatus",
    "TTSJobStep",
    "FootageSearch",
    "FootageSearchStatus",
    "FootageCandidate",
    "SceneFootageSelection",
]
