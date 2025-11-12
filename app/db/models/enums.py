from enum import Enum

class Variable(str, Enum):
    temperature = "temperature"   # temp_c
    humidity = "humidity"         # humidity_pct
    energy = "energy"             # energy_kw

class AlertLevel(str, Enum):
    info = "info"
    medium = "medium"
    critical = "critical"

class AlertStatus(str, Enum):
    open = "open"
    acknowledged = "acknowledged"
    closed = "closed"
