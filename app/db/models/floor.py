from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

class Floor(Base):
    __tablename__ = "floors"
    __table_args__ = (
        Index("ix_floors_building_name_unique", "building_id", "name", unique=True),
    )

    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    building = relationship("Building", back_populates="floors")
    thresholds = relationship("Threshold", back_populates="floor", cascade="all, delete-orphan")
    metrics = relationship("Metric", back_populates="floor", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="floor", cascade="all, delete-orphan")
