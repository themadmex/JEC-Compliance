from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GraphObject(Base):
    __tablename__ = "graph_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_type: Mapped[str] = mapped_column(Text, nullable=False)
    external_key: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    subtitle: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text, default="{}")
    data: Mapped[str | None] = mapped_column(Text)
    synced_at: Mapped[str | None] = mapped_column(DateTime)
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)


class GraphLink(Base):
    __tablename__ = "graph_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    left_type: Mapped[str | None] = mapped_column(Text)
    left_id: Mapped[int | None] = mapped_column(Integer)
    right_type: Mapped[str | None] = mapped_column(Text)
    right_id: Mapped[int | None] = mapped_column(Integer)
    link_type: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("graph_objects.id"))
    target_id: Mapped[int | None] = mapped_column(ForeignKey("graph_objects.id"))
    relationship: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
