from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import String

from app.database.database import Base


class LifeExpectancy(Base):
    __tablename__ = "life_expectancy"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    country = Column(String)

    year = Column(Integer)

    status = Column(String)

    life_expectancy = Column(Float)

    adult_mortality = Column(Float)

    bmi = Column(Float)

    gdp = Column(Float)

    schooling = Column(Float)

    population = Column(Float)