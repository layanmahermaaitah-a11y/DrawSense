from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    
    # الإضافات الجديدة
    bio = Column(Text, nullable=True) 
    email_notifications = Column(Boolean, default=True) 

    profile_image = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=False)
    verification_code = Column(String(6), nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)

    drawings = relationship("Drawing", back_populates="owner", cascade="all, delete-orphan")


class Drawing(Base):
    __tablename__ = "drawings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=True)
    image_url = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())
    is_favorite = Column(Boolean, default=False, nullable=False)

    # العلاقات
    owner = relationship("User", back_populates="drawings")
    analysis_results = relationship("AnalysisResult", back_populates="drawing", cascade="all, delete-orphan")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    drawing_id = Column(Integer, ForeignKey("drawings.id", ondelete="CASCADE"), nullable=False)
    prediction_label = Column(String(100), nullable=True)
    confidence_score = Column(Float, nullable=True)
    ai_details = Column(JSONB, nullable=True)  # تخزين بيانات المودل
    created_at = Column(DateTime, server_default=func.now())

    # العلاقات
    drawing = relationship("Drawing", back_populates="analysis_results")