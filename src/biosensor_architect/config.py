"""Application configuration loaded from environment variables."""

from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Settings:
    """Global settings for BioSensor-Architect."""

    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    ncbi_api_key: str = field(default_factory=lambda: os.getenv("NCBI_API_KEY", ""))
    chroma_persist_dir: Path = field(
        default_factory=lambda: Path(os.getenv("CHROMA_PERSIST_DIR", "./data/literature_index"))
    )
    default_model: str = field(default_factory=lambda: os.getenv("DEFAULT_MODEL", "gpt-4o"))
    design_rounds: int = field(default_factory=lambda: int(os.getenv("DESIGN_ROUNDS", "1")))
    crossref_email: str = field(
        default_factory=lambda: os.getenv("CROSSREF_EMAIL", "biosensor-architect@example.com")
    )


settings = Settings()
