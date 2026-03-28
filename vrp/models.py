"""Pydantic data models for VRP report data."""

from typing import Optional
from pydantic import BaseModel, Field


class Attachment(BaseModel):
    id: int
    filename: str
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    url: str = ""
    local_path: Optional[str] = None


class Update(BaseModel):
    index: int
    author: str = "Unknown"
    timestamp: Optional[str] = None
    text_plain: str = ""
    text_html: Optional[str] = None
    attachments: list[Attachment] = Field(default_factory=list)
    is_description: bool = False
    is_bounty_award: bool = False


class Issue(BaseModel):
    id: str
    url: str
    title: str = "Untitled"
    status: str = "Unknown"
    severity: str = "Unknown"
    priority: str = "Unknown"
    component: str = "Unknown"
    os_platforms: list[str] = Field(default_factory=list)
    chrome_version: Optional[str] = None
    cve_ids: list[str] = Field(default_factory=list)
    reporter: str = "Unknown"
    assignee: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    bounty_confirmed: bool = False
    bounty_amount: Optional[float] = None
    bounty_rationale: Optional[str] = None
    attachments: list[Attachment] = Field(default_factory=list)
    update_count: int = 0
    description_snippet: str = ""


class IndexEntry(BaseModel):
    """Lightweight entry for index.json."""
    id: str
    title: str
    url: str
    status: str = "Unknown"
    severity: str = "Unknown"
    component: str = "Unknown"
    bounty_amount: Optional[float] = None
    created_date: Optional[str] = None
    year: Optional[int] = None
    attachment_count: int = 0
    local_path: str = ""
    has_markdown: bool = False
