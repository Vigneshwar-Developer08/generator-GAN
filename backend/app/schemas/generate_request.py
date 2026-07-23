"""Request schema for POST /generate."""

from typing import Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """
    Optional generation parameters.

    An empty body `{}` is valid: a random seed is used and a fresh
    image is generated on every call.
    """

    seed: Optional[int] = Field(
        default=None,
        ge=0,
        le=2**32 - 1,
        description="Optional seed for reproducible generation. Omit for a random image.",
        examples=[123],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{}, {"seed": 123}],
        }
    }
