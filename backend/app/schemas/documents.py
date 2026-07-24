from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResumeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    file_type: Literal["pdf", "docx", "md", "txt", "text"] = "text"
    raw_text: str = Field(min_length=1, max_length=100_000)
    is_current: bool = True


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    file_type: str
    raw_text: str
    parsed_profile_json: dict[str, Any] | None
    evidence_map_json: dict[str, Any] | None
    is_current: bool
    created_at: datetime
    updated_at: datetime


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    raw_text: str = Field(min_length=1, max_length=100_000)
    is_current: bool = True


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    company: str | None
    raw_text: str
    parsed_requirements_json: dict[str, Any] | None
    is_current: bool
    created_at: datetime
    updated_at: datetime

