from pydantic import BaseModel
from typing import Optional

class FloorBase(BaseModel):
    building_id: int
    name: str
    number: int

class FloorCreate(FloorBase):
    pass

class FloorOut(FloorBase):
    id: int
    class Config:
        from_attributes = True
