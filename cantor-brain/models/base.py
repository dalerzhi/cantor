"""
模型基类
"""
from pydantic import BaseModel
from sqlalchemy.orm import declarative_base

# SQLAlchemy 声明式基类
Base = declarative_base()


# Pydantic 响应模型
class HealthResponse(BaseModel):
    status: str
    message: str
