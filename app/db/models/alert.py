from sqlalchemy import Column, BigInteger, Integer, DateTime, String, Enum, ForeignKey, func, Index
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.models.enums import Variable, AlertLevel, AlertStatus

class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_floor_created", "floor_id", "created_at"),
    )

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id", ondelete="CASCADE"), nullable=False)

    variable = Column(Enum(Variable, name="variable_enum"), nullable=False)
    level = Column(Enum(AlertLevel, name="alert_level_enum"), nullable=False)
    status = Column(Enum(AlertStatus, name="alert_status_enum"), nullable=False, default=AlertStatus.open)

    message = Column(String(300), nullable=False)
    recommendation = Column(String(300))

    floor = relationship("Floor", back_populates="alerts")
