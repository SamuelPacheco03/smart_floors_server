from pydantic import BaseModel
from typing import Optional

class BuildingBase(BaseModel):
    name: str
    address: Optional[str] = None

class BuildingCreate(BuildingBase):
    pass

class BuildingOut(BuildingBase):
    id: int
    class Config:
        from_attributes = True
