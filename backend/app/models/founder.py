"""
Founder Models
Represents startup founders using the AI Chief of Staff
"""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, validator


class FounderPreferences(BaseModel):
    """Founder preferences and settings"""
    timezone: str = Field(default="UTC", description="Founder's timezone")
    morning_brief_time: str = Field(default="08:00", description="Time for morning brief (HH:MM)")
    evening_wrap_time: str = Field(default="18:00", description="Time for evening wrap (HH:MM)")
    notification_channels: list[str] = Field(
        default=["email"],
        description="Preferred notification channels"
    )
    language: str = Field(default="en", description="Preferred language code")
    communication_style: Optional[str] = Field(
        None,
        description="AI communication style preference: formal, casual, technical"
    )
    summary_length: str = Field(default="medium", description="Preferred summary length: brief, medium, detailed")

    @validator("morning_brief_time", "evening_wrap_time")
    def validate_time_format(cls, v):
        """Validate time format (HH:MM)"""
        try:
            hours, minutes = v.split(":")
            if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError("Time must be in HH:MM format (00:00 to 23:59)")
        return v

    @validator("communication_style")
    def validate_communication_style(cls, v):
        """Validate communication style"""
        if v is not None:
            allowed_styles = ["formal", "casual", "technical"]
            if v not in allowed_styles:
                raise ValueError(f"Communication style must be one of: {allowed_styles}")
        return v

    @validator("summary_length")
    def validate_summary_length(cls, v):
        """Validate summary length"""
        allowed_lengths = ["brief", "medium", "detailed"]
        if v not in allowed_lengths:
            raise ValueError(f"Summary length must be one of: {allowed_lengths}")
        return v


class FounderBase(BaseModel):
    """Base founder model with common fields"""
    display_name: Optional[str] = Field(None, max_length=255, description="Founder's display name")
    email: Optional[EmailStr] = Field(None, description="Founder's email address")


class FounderCreate(FounderBase):
    """Model for creating a new founder"""
    workspace_id: UUID = Field(..., description="Workspace ID the founder belongs to")
    user_id: UUID = Field(..., description="User ID from authentication system")
    preferences: FounderPreferences = Field(default_factory=FounderPreferences)


class FounderUpdate(BaseModel):
    """Model for updating founder information"""
    display_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    preferences: Optional[FounderPreferences] = None


class FounderResponse(FounderBase):
    """Response model for founder data"""
    id: UUID = Field(..., description="Unique founder identifier")
    workspace_id: UUID = Field(..., description="Associated workspace ID")
    user_id: UUID = Field(..., description="Associated user ID")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="Founder preferences")
    created_at: datetime = Field(..., description="Founder creation timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440001",
                "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "750e8400-e29b-41d4-a716-446655440002",
                "display_name": "Jane Doe",
                "email": "jane@acmestartup.com",
                "preferences": {
                    "timezone": "America/New_York",
                    "morning_brief_time": "08:00",
                    "evening_wrap_time": "18:00",
                    "notification_channels": ["email", "slack"],
                    "language": "en",
                    "communication_style": "casual",
                    "summary_length": "medium"
                },
                "created_at": "2025-10-30T10:00:00Z"
            }
        }
