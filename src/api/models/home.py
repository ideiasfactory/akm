from typing import List
from pydantic import BaseModel, Field


class FeatureInfo(BaseModel):
    """Feature information for home page display."""

    icon: str = Field(..., description="Emoji icon for the feature")
    title: str = Field(..., description="Feature title")
    description: str = Field(..., description="Feature description")


class EndpointInfo(BaseModel):
    """Endpoint information for home page display."""

    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    path: str = Field(..., description="Endpoint path")
    description: str = Field(..., description="Endpoint description")


class HomePageData(BaseModel):
    """Data model for home page rendering."""

    title: str = Field(default="API Key Management Service", description="Page title")
    subtitle: str = Field(
        default="Secure API Key Management with Scope-Based Access Control", description="Page subtitle"
    )
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Deployment environment")
    environment_class: str = Field(..., description="CSS class for environment badge")
    description: str = Field(
        default=(
            "A production-ready FastAPI application for managing API keys "
            "with fine-grained scope-based access control and project organization."
        ),
        description="Main description text",
    )
    features: List[FeatureInfo] = Field(
        default_factory=list, description="List of features to display"
    )
    endpoints: List[EndpointInfo] = Field(
        default_factory=list, description="List of endpoints to display"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "API Key Management Service",
                "subtitle": "Secure API Key Management with Scope-Based Access Control",
                "version": "1.0.0",
                "environment": "production",
                "environment_class": "production",
                "description": "A production-ready FastAPI application...",
                "features": [
                    {
                        "icon": "🔐",
                        "title": "Secure Key Management",
                        "description": "SHA-256 hashed keys with expiration",
                    }
                ],
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/akm/keys",
                        "description": "API key management",
                    }
                ],
            }
        }
