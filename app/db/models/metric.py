from sqlalchemy import Column, BigInteger, Integer, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (
        Index("ix_metrics_floor_time", "floor_id", "time"),
    )

    id = Column(BigInteger, primary_key=True)
    time = Column(DateTime(timezone=True), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id", ondelete="CASCADE"), nullable=False)

    # valores
    temp_c = Column(Numeric(5, 2))
    humidity_pct = Column(Numeric(5, 2))
    energy_kw = Column(Numeric(8, 3))

    floor = relationship("Floor", back_populates="metrics")
