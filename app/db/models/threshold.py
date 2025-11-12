from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime, func, Enum, Numeric, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.models.enums import Variable

class Threshold(Base):
    __tablename__ = "thresholds"
    __table_args__ = (
        # Un umbral activo por variable y piso (puedes tener históricos inactivos)
        UniqueConstraint("floor_id", "variable", "is_active", name="uq_active_threshold_per_var_floor"),
        Index("ix_thresholds_floor_var", "floor_id", "variable"),
    )

    id = Column(Integer, primary_key=True)
    floor_id = Column(Integer, ForeignKey("floors.id", ondelete="CASCADE"), nullable=False)
    variable = Column(Enum(Variable, name="variable_enum"), nullable=False)
    lower = Column(Numeric(8, 3), nullable=False)
    upper = Column(Numeric(8, 3), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    floor = relationship("Floor", back_populates="thresholds")
