# app/models/dto.py
# Data Transfer Objects (DTOs)
# - LabelRequest: Print job request data model
# - JobSubmitResponse: Job submission response model
# - JobStatusResponse: Job status query response model
# - TemplateInfo: Template metadata model

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LabelRequest(BaseModel):
    """
    Request model for submitting a print job.
    """

    template_name: str = Field(
        ..., description="gLabels template filename (must end with .glabels)"
    )
    data: List[Dict[str, Any]] = Field(
        ...,
        description="List of label data objects; each object represents one label, keys must match template fields",
    )
    copies: int = Field(
        1, ge=1, description="Number of copies per record (maps to glabels --copies)"
    )

    # Pydantic v2: provide general example
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "template_name": "demo.glabels",
                "data": [
                    {"ITEM": "A001", "CODE": "X123"},
                    {"ITEM": "A002", "CODE": "X124"},
                ],
                "copies": 2,
            }
        }
    )

    @field_validator("template_name")
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        if not v.lower().endswith(".glabels"):
            raise ValueError("template_name must have .glabels extension")
        if not v.endswith(".glabels"):  # normalize extension case
            v = v[:-8] + ".glabels"
        return v


class JobSubmitResponse(BaseModel):
    """
    Response model for job submission.
    """

    job_id: str
    message: str = "Job submitted successfully"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "Job submitted successfully",
            }
        }
    )


class JobStatusResponse(BaseModel):
    """
    Response model for job status query and listing.
    """

    job_id: str
    status: str = Field(
        ..., description="Job status: pending | running | done | failed"
    )
    template: str = Field(..., description="The gLabels template filename used")
    filename: str = Field(
        ..., description="Expected output PDF filename (present even if job failed)"
    )
    error: Optional[str] = Field(
        None, description="Error message if job failed; null if succeeded"
    )
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Job last updated timestamp")

    # Provide a general example; detailed cases are defined in routes
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "done",
                "template": "demo.glabels",
                "filename": "demo_20250919_123456.pdf",
                "error": None,
                "created_at": "2025-09-19T10:00:00",
                "updated_at": "2025-09-19T10:00:05",
            }
        }
    )


class TemplateInfo(BaseModel):
    """
    Template information model for listing templates with field details.
    """

    name: str = Field(..., description="Template filename (e.g., 'demo.glabels')")
    format_type: str = Field(..., description="Template format type (e.g., 'CSV')")
    has_headers: bool = Field(
        ..., description="Whether the template expects CSV with header row"
    )
    fields: List[str] = Field(
        ...,
        description="List of field names or positions (e.g., ['CODE', 'ITEM'] or ['1', '2'])",
    )
    field_count: int = Field(..., description="Number of fields in the template")
    merge_type: Optional[str] = Field(
        None, description="Internal gLabels merge type (e.g., 'Text/Comma/Line1Keys')"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "demo.glabels",
                "format_type": "CSV",
                "has_headers": True,
                "fields": ["CODE", "ITEM"],
                "field_count": 2,
                "merge_type": "Text/Comma/Line1Keys",
            }
        }
    )
