"""
SQLAlchemy Base 모델
"""
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """SQLAlchemy Base 클래스"""
    pass