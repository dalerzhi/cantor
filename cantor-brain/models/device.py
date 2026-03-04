"""
设备模型
云手机设备的数据库模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from models.base import Base


class Device(Base):
    """云手机设备模型"""
    __tablename__ = "devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    serial_number = Column(String(255), unique=True, nullable=False)
    
    # 设备状态: available(未分配), allocated(已分配), offline(离线), maintenance(维护中)
    status = Column(String(50), default="available")
    
    # 关联的租户/组织
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    
    # 设备规格信息
    os_version = Column(String(50))
    memory = Column(String(50))
    storage = Column(String(50))
    
    # IaaS 平台相关信息
    iaas_instance_id = Column(String(255))
    iaas_project_id = Column(String(255))
    iaas_project_name = Column(String(255))
    ip_address = Column(String(50))
    resolution = Column(String(50))
    
    # 扩展元数据
    metadata = Column(JSON, default={})
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_heartbeat = Column(DateTime)
    
    # 关联关系
    organization = relationship("Organization", back_populates="devices")
    
    def __repr__(self):
        return f"<Device {self.name} ({self.status})>"
