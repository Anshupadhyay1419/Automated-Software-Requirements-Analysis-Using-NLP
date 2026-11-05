"""Small helpers shared by the API routes."""
from fastapi import HTTPException


def get_or_404(db, model, row_id):
    row = db.get(model, row_id)
    if row is None:
        raise HTTPException(404, f"{model.__name__} {row_id} was not found.")
    return row


def to_dict(row) -> dict:
    """Turn a database row into a dictionary that can be sent as JSON."""
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}
