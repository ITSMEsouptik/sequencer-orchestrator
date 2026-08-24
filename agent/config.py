import os
from dataclasses import dataclass

_LOCAL_DB_URL = (
    "postgresql://sequencer_orchestrator_user"
    ":sequencer_orchestrator_pass"
    "@localhost:5433/sequencer-orchestrator"
)


@dataclass
class Config:
    database_url: str
    openai_api_key: str
    openai_model: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            database_url=os.environ.get("DATABASE_URL", _LOCAL_DB_URL),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        )
