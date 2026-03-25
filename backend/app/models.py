from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
import datetime
import uuid

from .database import Base

class Article(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True, index=True) # Habr ID e.g. "802425"
    url = Column(String, index=True)
    score = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    versions = relationship("ArticleVersion", back_populates="article")

class ArticleVersion(Base):
    __tablename__ = "article_versions"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String, ForeignKey("articles.id"))
    title = Column(String, index=True)
    content_html = Column(String, nullable=True)
    fetched_at = Column(DateTime, default=datetime.datetime.utcnow)

    article = relationship("Article", back_populates="versions")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, default="pending") # pending, processing, completed, failed
    progress = Column(Integer, default=0)
    target_start_date = Column(String, nullable=True)
    target_end_date = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
