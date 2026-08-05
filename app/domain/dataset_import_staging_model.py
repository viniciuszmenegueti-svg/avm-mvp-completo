from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class DatasetImportExecutionModel(Base):
    __tablename__ = "dataset_import_executions"
    __table_args__ = (
        Index(
            "ix_dataset_import_executions_version_created_at",
            "dataset_version_id",
            "created_at",
        ),
        Index(
            "ix_dataset_import_executions_status_created_at",
            "status",
            "created_at",
        ),
    )

    execution_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("dataset_versions.dataset_version_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    schema_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DatasetImportRowModel(Base):
    __tablename__ = "dataset_import_rows"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            "line_number",
            name="uq_dataset_import_rows_execution_line",
        ),
        Index(
            "ix_dataset_import_rows_execution_status_line",
            "execution_id",
            "status",
            "line_number",
        ),
        Index(
            "ix_dataset_import_rows_version_status",
            "dataset_version_id",
            "status",
        ),
        Index(
            "ix_dataset_import_rows_execution_row_hash",
            "execution_id",
            "row_hash",
        ),
    )

    row_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("dataset_import_executions.execution_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("dataset_versions.dataset_version_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    original_json: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    errors_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    row_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
