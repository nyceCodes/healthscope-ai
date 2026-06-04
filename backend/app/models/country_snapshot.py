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

    risk_score = Column(Float)

    created_at = Column(DateTime)