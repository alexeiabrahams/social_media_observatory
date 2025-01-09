from ..config import *
import sqlalchemy as sa
from sqlalchemy.sql.schema import Table as SQLAlchemyTable
from datetime import datetime


def instantiate_channel_metadata_table(my_table_name: str) -> SQLAlchemyTable:
    my_table = sa.Table(
        my_table_name,
        meta,
        sa.Column("channel_id", sa.types.BIGINT, primary_key=True),
        sa.Column("channel_name", sa.types.TEXT, unique=True),
        sa.Column("channel_title", sa.types.TEXT, default=None),
        sa.Column("channel_birthdate", sa.types.DateTime(timezone=True)),
        sa.Column("channel_bio", sa.types.TEXT, default=None),
        sa.Column("num_subscribers", sa.types.INTEGER, default=None),
        sa.Column("data_source", sa.types.TEXT, default="telegram-api"),
        sa.Column(
            "checkup_time", sa.types.DateTime(timezone=True), default=datetime.utcnow
        ),
        sa.Column("api_response", sa.types.JSON, nullable=False),
    )
    return my_table


def instantiate_seed_table(my_table_name: str) -> SQLAlchemyTable:
    my_table = sa.Table(
        my_table_name,
        meta,
        sa.Column("channel_id", sa.types.BIGINT, primary_key=True),
        sa.Column("channel_name", sa.types.TEXT, nullable=False),
        sa.Column("seed_list", sa.types.TEXT, primary_key=True),
    )
    return my_table


def insert_data_into_channel_metadata_table(records: list[dict]):
    stmt = sa.insert(channel_metadata_table).values(records)
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def insert_data_into_channel_metadata_table_advanced(records: list[dict]):
    # check if the table already contains channels matching the IDs of the incoming records
    stmt = sa.select(channel_metadata_table.c.channel_id).where(
        channel_metadata_table.c.channel_id.in_(
            [record["channel_id"] for record in records]
        )
    )
    with engine.connect() as conn:
        rp = conn.execute(stmt)
        rows = rp.fetchall()
    if len(rows) > 0:
        rows = [x for (x,) in rows]

    new_records = [record for record in records if record["channel_id"] not in rows]
    duplicate_records = [record for record in records if record["channel_id"] in rows]

    if len(new_records) > 0:
        insert_data_into_channel_metadata_table(new_records)

    if len(duplicate_records) > 0:
        pass  # do nothing with these


def insert_data_into_seed_table(records: list[dict]):
    stmt = sa.insert(seed_table).values(records)
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


# Connect to database
engine = sa.create_engine(
    f"postgresql://"
    f"{config['telegram-db']['user']}:"
    f"{config['telegram-db']['password']}"
    f"@{config['telegram-db']['host']}:"
    f"{config['telegram-db']['port']}/"
    f"{config['telegram-db']['dbname']}",
    echo=True,
)

# Define tables and create them if they don't already exist
meta = sa.MetaData()
channel_metadata_table = instantiate_channel_metadata_table(channel_metadata_table_name)
seed_table = instantiate_seed_table(seed_table_name)
meta.create_all(engine)
