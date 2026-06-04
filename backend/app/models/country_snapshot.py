from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy import DateTime

from app.database.database import Base


class CountrySnapshot(Base):

    __tablename__ = "country_snapshots"

    id = Column(Integer, primary_key=True)

    country = Column(String)

    population = Column(Integer)

    cases = Column(Integer)

    deaths = Column(Integer)

    recovered = Column(Integer)

    active = Column(Integer)

    tests = Column(Integer)

    recovery_rate = Column(Float)

    mortality_rate = Column(Float)

    health_index = Column(Float)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )