# This file is a demo file for using sqlite
from sqlalchemy import ( ## pip install sqlalchemy
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    DateTime,
)
from datetime import datetime

engine = create_engine("sqlite:///:memory:")
metadata_obj = MetaData()

# Create file tracking table
table_name = "file_tracking"
file_tracking_table = Table(
    table_name,
    metadata_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", DateTime, default=datetime.utcnow, nullable=False),
    Column("original_filename", String(255), nullable=False),
    Column("original_download_url", String(1024), nullable=False),
    Column("generated_filename", String(255), nullable=False),
    Column("generated_download_url", String(1024), nullable=False),
)
metadata_obj.create_all(engine)

from sqlalchemy import insert

# Example of how to insert a file record
def add_file_record(
    original_filename: str,
    original_download_url: str,
    generated_filename: str,
    generated_download_url: str,
) -> int:
    """
    Add a new file record to the tracking database.
    Returns the ID of the newly created record.
    """
    stmt = insert(file_tracking_table).values(
        original_filename=original_filename,
        original_download_url=original_download_url,
        generated_filename=generated_filename,
        generated_download_url=generated_download_url,
    )
    with engine.begin() as connection:
        result = connection.execute(stmt)
        return result.inserted_primary_key[0]

# Example usage:
if __name__ == "__main__":
    # Example record
    record_id = add_file_record(
        original_filename="example.pdf",
        original_download_url="https://example.com/files/original.pdf",
        generated_filename="processed_example.pdf",
        generated_download_url="https://example.com/files/processed.pdf"
    )
    print(f"Added file record with ID: {record_id}")