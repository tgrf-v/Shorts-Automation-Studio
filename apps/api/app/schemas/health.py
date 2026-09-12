from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Overall health status of the service")
    app_env: str = Field(..., description="Application environment (e.g. development, production)")
    version: str = Field(default="0.1.0", description="API version")
