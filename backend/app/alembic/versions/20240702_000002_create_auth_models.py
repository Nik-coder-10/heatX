"""create auth models (user_roles, audit_logs ip_address/user_agent)

Revision ID: 20240702_000002
Revises: 20240630_000001
Create Date: 2024-07-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20240702_000002'
down_revision = '20240630_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_roles association table for many-to-many User <-> Role
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add ip_address and user_agent columns to audit_logs
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.add_column(sa.Column('ip_address', sa.String(45), nullable=True))
        batch_op.add_column(sa.Column('user_agent', sa.Text, nullable=True))

    # Migrate existing user->role assignments from users.role_id to user_roles
    conn = op.get_bind()
    if conn.engine.name != 'sqlite':
        # Only run on databases that support the columns (SQLite may not have role_id)
        try:
            result = conn.execute(
                sa.text("SELECT id, role_id FROM users WHERE role_id IS NOT NULL")
            )
            rows = result.fetchall()
            for user_id, role_id in rows:
                conn.execute(
                    sa.text(
                        "INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {"user_id": user_id, "role_id": role_id}
                )
        except Exception:
            # Column may not exist or table may be empty; skip migration gracefully
            pass


def downgrade() -> None:
    # Remove added columns from audit_logs
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.drop_column('user_agent')
        batch_op.drop_column('ip_address')

    # Drop user_roles table
    op.drop_table('user_roles')
