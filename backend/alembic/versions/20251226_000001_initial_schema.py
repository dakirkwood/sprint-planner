"""Initial schema

Revision ID: 20251226_000001
Revises:
Create Date: 2025-12-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251226_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jira_user_id", sa.String(255), nullable=False),
        sa.Column("jira_display_name", sa.String(255), nullable=True),
        sa.Column("site_name", sa.String(255), nullable=True),
        sa.Column("site_description", sa.String(2000), nullable=True),
        sa.Column("jira_project_key", sa.String(50), nullable=True),
        sa.Column("llm_provider_choice", sa.String(50), nullable=True),
        sa.Column("current_stage", sa.String(50), nullable=False, server_default="upload"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("total_tickets_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sessions_jira_user_id", "sessions", ["jira_user_id"])
    op.create_index("idx_sessions_status", "sessions", ["status"])
    op.create_index("idx_sessions_current_stage", "sessions", ["current_stage"])
    op.create_index("idx_sessions_created_at", "sessions", ["created_at"])

    # Session Tasks table
    op.create_table(
        "session_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_context", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", name="uq_session_tasks_session_id"),
    )

    # Session Validations table
    op.create_table(
        "session_validations",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("validation_passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_results", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "validation_passed = false OR validation_status = 'completed'",
            name="ck_validation_passed_only_when_completed",
        ),
    )

    # Uploaded Files table
    op.create_table(
        "uploaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("csv_type", sa.String(100), nullable=True),
        sa.Column("parsed_content", postgresql.JSONB(), nullable=False),
        sa.Column("validation_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_uploaded_files_session_id", "uploaded_files", ["session_id"])
    op.create_index("idx_uploaded_files_csv_type", "uploaded_files", ["csv_type"])
    op.create_index("idx_uploaded_files_validation_status", "uploaded_files", ["validation_status"])

    # Tickets table
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("csv_source_files", postgresql.JSONB(), nullable=False),
        sa.Column("entity_group", sa.String(100), nullable=False),
        sa.Column("user_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ready_for_jira", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sprint", sa.String(255), nullable=True),
        sa.Column("assignee", sa.String(255), nullable=True),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column("jira_ticket_key", sa.String(50), nullable=True),
        sa.Column("jira_ticket_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_tickets_session_id", "tickets", ["session_id"])
    op.create_index("idx_tickets_entity_group", "tickets", ["entity_group"])
    op.create_index("idx_tickets_ready_for_jira", "tickets", ["ready_for_jira"])

    # Ticket Dependencies table
    op.create_table(
        "ticket_dependencies",
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("depends_on_ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("ticket_id", "depends_on_ticket_id"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.CheckConstraint("ticket_id != depends_on_ticket_id", name="ck_no_self_dependency"),
    )
    op.create_index("idx_ticket_dependencies_ticket_id", "ticket_dependencies", ["ticket_id"])
    op.create_index("idx_ticket_dependencies_depends_on", "ticket_dependencies", ["depends_on_ticket_id"])

    # Attachments table
    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("jira_attachment_id", sa.String(100), nullable=True),
        sa.Column("jira_upload_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("ticket_id"),
    )
    op.create_index("idx_attachments_session_id", "attachments", ["session_id"])
    op.create_index("idx_attachments_ticket_id", "attachments", ["ticket_id"])
    op.create_index("idx_attachments_jira_upload_status", "attachments", ["jira_upload_status"])

    # Jira Auth Tokens table
    op.create_table(
        "jira_auth_tokens",
        sa.Column("jira_user_id", sa.String(255), nullable=False),
        sa.Column("encrypted_access_token", sa.String(2000), nullable=False),
        sa.Column("encrypted_refresh_token", sa.String(2000), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("granted_scopes", postgresql.JSONB(), nullable=False),
        sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("jira_user_id"),
    )
    op.create_index("idx_jira_auth_tokens_expires_at", "jira_auth_tokens", ["token_expires_at"])

    # Jira Project Context table
    op.create_table(
        "jira_project_context",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_key", sa.String(50), nullable=False),
        sa.Column("project_name", sa.String(255), nullable=False),
        sa.Column("can_create_tickets", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_assign_tickets", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("available_sprints", postgresql.JSONB(), nullable=False),
        sa.Column("team_members", postgresql.JSONB(), nullable=False),
        sa.Column("cached_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("session_id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )

    # Session Errors table
    op.create_table(
        "session_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("error_category", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("operation_stage", sa.String(50), nullable=False),
        sa.Column("related_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("recovery_actions", postgresql.JSONB(), nullable=False),
        sa.Column("technical_details", postgresql.JSONB(), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_file_id"], ["uploaded_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_ticket_id"], ["tickets.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_session_errors_session_id", "session_errors", ["session_id"])
    op.create_index("idx_session_errors_category", "session_errors", ["error_category"])
    op.create_index("idx_session_errors_severity", "session_errors", ["severity"])

    # Audit Log table
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("jira_user_id", sa.String(255), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_category", sa.String(50), nullable=False),
        sa.Column("audit_level", sa.String(50), nullable=False, server_default="basic"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("event_data", postgresql.JSONB(), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_audit_log_session_id", "audit_log", ["session_id"])
    op.create_index("idx_audit_log_jira_user_id", "audit_log", ["jira_user_id"])
    op.create_index("idx_audit_log_event_category", "audit_log", ["event_category"])
    op.create_index("idx_audit_log_audit_level", "audit_log", ["audit_level"])
    op.create_index("idx_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("session_errors")
    op.drop_table("jira_project_context")
    op.drop_table("jira_auth_tokens")
    op.drop_table("attachments")
    op.drop_table("ticket_dependencies")
    op.drop_table("tickets")
    op.drop_table("uploaded_files")
    op.drop_table("session_validations")
    op.drop_table("session_tasks")
    op.drop_table("sessions")
