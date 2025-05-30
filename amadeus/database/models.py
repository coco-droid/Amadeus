"""
Database models for Amadeus application.
Defines SQLAlchemy models for providers, models, datasets, and other persistent data.
"""
import datetime
import enum
from typing import Dict, Any, Optional, List

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class JobStatus(enum.Enum):
    """Status enum for fine-tuning jobs"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Provider(Base):
    """Model representing an AI provider"""
    __tablename__ = 'providers'
    
    id = Column(Integer, primary_key=True)
    provider_id = Column(String(50), unique=True, nullable=False)  # e.g. "openai", "mistral", "unsloth"
    name = Column(String(100), nullable=False)
    provider_type = Column(String(50), nullable=False)  # e.g. "cloud", "local"
    is_available = Column(Boolean, default=True)
    is_configured = Column(Boolean, default=False)
    last_check_time = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    credentials = relationship("ProviderCredential", back_populates="provider", cascade="all, delete-orphan")
    models = relationship("Model", back_populates="provider")
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="provider")
    
    def __repr__(self):
        return f"<Provider(provider_id='{self.provider_id}', name='{self.name}', type='{self.provider_type}')>"
    
class ProviderCredential(Base):
    """Model for storing encrypted provider credentials"""
    __tablename__ = 'provider_credentials'
    
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey('providers.id'), nullable=False)
    key = Column(String(100), nullable=False)
    encrypted_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    provider = relationship("Provider", back_populates="credentials")
    
    def __repr__(self):
        return f"<ProviderCredential(provider='{self.provider.provider_id}', key='{self.key}')>"
    
    def is_expired(self, days=90):
        """Check if credential is older than specified days"""
        import datetime
        if not self.updated_at:
            return True
        
        age = datetime.datetime.utcnow() - self.updated_at
        return age.days > days
    
    def update_timestamp(self):
        """Update the timestamp when credential is modified"""
        import datetime
        self.updated_at = datetime.datetime.utcnow()

class Model(Base):
    """Model representing a language model (fine-tuned or base)"""
    __tablename__ = 'models'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    provider_id = Column(Integer, ForeignKey('providers.id'), nullable=False)  # Added ForeignKey
    model_type = Column(String(50), nullable=False)
    model_metadata = Column(JSON, default={})  # Changed from 'metadata' to 'model_metadata'
    capabilities = Column(JSON, default={})
    pricing = Column(JSON, default={})
    limits = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    provider = relationship("Provider", back_populates="models")
    fine_tuning_job = relationship("FineTuningJob", back_populates="model", uselist=False)
    
    def __repr__(self):
        return f"<Model(name='{self.name}', provider_id='{self.provider_id}')>"  # Fixed reference

class Dataset(Base):
    """Model representing a training dataset"""
    __tablename__ = 'datasets'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    file_path = Column(String(255))
    format = Column(String(50))  # e.g. "json", "csv", "jsonl"
    num_examples = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    dataset_metadata = Column(JSON, default={})  # Changed from 'metadata' to 'dataset_metadata'
    
    # Relationships
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="dataset")
    
    def __repr__(self):
        return f"<Dataset(name='{self.name}', examples={self.num_examples})>"

class FineTuningJob(Base):
    """Model representing a fine-tuning job"""
    __tablename__ = 'fine_tuning_jobs'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(100))  # External job ID from provider
    provider_id = Column(Integer, ForeignKey('providers.id'), nullable=False)
    dataset_id = Column(Integer, ForeignKey('datasets.id'))
    model_id = Column(Integer, ForeignKey('models.id'))
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    completed_at = Column(DateTime)
    parameters = Column(JSON)  # Job parameters (learning rate, epochs, etc)
    logs = Column(Text)  # Job logs
    
    # Relationships
    provider = relationship("Provider", back_populates="fine_tuning_jobs")
    dataset = relationship("Dataset", back_populates="fine_tuning_jobs")
    model = relationship("Model", back_populates="fine_tuning_job")
    
    def __repr__(self):
        return f"<FineTuningJob(id={self.id}, status='{self.status}')>"

class UserPreference(Base):
    """Model for storing user preferences"""
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<UserPreference(key='{self.key}')>"
