from pydantic import BaseModel
from datetime import datetime


class HistorySnapshot(BaseModel):

    id: int

    country: str

    health_index: float

    recovery_rate: float

    mortality_rate: float

    created_at: datetime

    class Config:
        from_attributes = True