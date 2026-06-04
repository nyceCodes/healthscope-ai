from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime

from app.database.database import Base

class NutritionSearch(Base):

    __tablename__ = "nutrition_searches"

    id = Column(Integer, primary_key=True)

    food_name = Column(String)

    created_at = Column(DateTime)