from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DatabaseStatus(BaseModel):
    """Database connection status information."""

    connected: bool = Field(..., description="Whether database is connected")
    type: str = Field(..., description="Database type (postgresql, csv, etc.)")
    latency_ms: Optional[float] = Field(
        None, description="Database response latency in milliseconds"
    )
    records_count: Optional[int] = Field(
        None, description="Total number of records in database"
    )
    last_updated: Optional[datetime] = Field(
        None, description="Timestamp of last data update"
    )


class HealthResponse(BaseModel):
    """API health check response model."""

    status: str = Field(
        ..., description="Overall API status (healthy, degraded, unhealthy)"
    )
    version: str = Field(..., description="API version")
    environment: str = Field(
        ..., description="Deployment environment (development, production)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Current server timestamp"
    )
    uptime_seconds: Optional[float] = Field(None, description="API uptime in seconds")
    database: DatabaseStatus = Field(..., description="Database status information")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "2.0.0",
                "environment": "production",
                "timestamp": "2025-11-09T12:00:00Z",
                "uptime_seconds": 86400.5,
                "database": {
                    "connected": True,
                    "type": "postgresql",
                    "latency_ms": 15.3,
                    "records_count": 1250,
                    "last_updated": "2025-11-09T06:00:00Z",
                },
            }
        }
