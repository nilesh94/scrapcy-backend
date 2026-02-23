from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Table, text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base

# Junction table for Many-to-Many relationship between Roles and Permissions [cite: 95]
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("scrapcy_app.roles.role_id"), primary_key=True),
    Column("perm_id", Integer, ForeignKey("scrapcy_app.permissions.perm_id"), primary_key=True),
    schema="scrapcy_app"
)

class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "scrapcy_app"}

    role_id = Column(Integer, primary_key=True, index=True)
    role_code = Column(String(30), unique=True, nullable=False)  # e.g., 'ADMIN', 'MGR_L1' [cite: 80, 111]
    role_name = Column(String(100), nullable=False)
    is_internal = Column(Integer, default=0, nullable=False)  # 1=staff, 0=client [cite: 82]
    sort_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1, nullable=False) # Soft revoke [cite: 84, 106]
    created_at = Column(TIMESTAMP(6), server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("UserRole", back_populates="role")

class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "scrapcy_app"}

    perm_id = Column(Integer, primary_key=True, index=True)
    perm_key = Column(String(100), unique=True, nullable=False) # e.g., 'auction:approve_l1' [cite: 90, 124]
    category = Column(String(50))
    description = Column(String(255))

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

class UserRole(Base):
    """Bridge table for User to Role assignment [cite: 101]"""
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "scrapcy_app"}

    user_id = Column(Integer, primary_key=True) # References users table
    role_id = Column(Integer, ForeignKey("scrapcy_app.roles.role_id"), primary_key=True)
    assigned_at = Column(TIMESTAMP(6), server_default=text("CURRENT_TIMESTAMP"))
    assigned_by = Column(Integer)
    is_active = Column(Integer, default=1) # soft revoke flag [cite: 106]

    role = relationship("Role", back_populates="users")

class AuctionApprovalLog(Base):
    """The critical immutable history table [cite: 51, 52]"""
    __tablename__ = "auction_approval_log"
    __table_args__ = {"schema": "scrapcy_app"}

    log_id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer, ForeignKey("scrapcy_app.auctions.id"), nullable=False)
    action_by = Column(Integer, nullable=False) # FK to users table [cite: 58]
    action_by_role = Column(String(30), nullable=False) # Snapshot: MGR_L1, ADMIN etc. [cite: 59]
    action = Column(String(30), nullable=False) # 'SUBMIT', 'APPROVE_L1', etc. [cite: 67, 68]
    from_status = Column(String(30), nullable=False)
    to_status = Column(String(30), nullable=False)
    comments = Column(String(1000)) # rejection reason / notes [cite: 63]
    actioned_at = Column(TIMESTAMP(6), server_default=text("CURRENT_TIMESTAMP"))
