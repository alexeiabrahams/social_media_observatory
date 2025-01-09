import sqlalchemy as sa
from sqlalchemy.sql.schema import Table as SQLAlchemyTable
from datetime import datetime
from ..config import config


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


def instantiate_channel_messages_table(my_table_name: str) -> SQLAlchemyTable:
    my_table = sa.Table(
        my_table_name,
        meta,
        sa.Column("channel_id", sa.types.BIGINT, primary_key=True),
        sa.Column("message_id", sa.types.INTEGER, primary_key=True),
        sa.Column("message_datetime", sa.types.DateTime(timezone=True)),
        sa.Column("message_views", sa.types.INTEGER, default=None),
        sa.Column("message_forwards", sa.types.INTEGER, default=None),
        sa.Column("message_text", sa.types.TEXT, default=None),
        sa.Column("forwardee_channel_id", sa.types.BIGINT, default=None),
        sa.Column("forwardee_message_id", sa.types.INTEGER, default=None),
        sa.Column("message_is_forward", sa.types.BOOLEAN, default=None),
        sa.Column("data_source", sa.types.TEXT, default="telegram-api"),
        sa.Column(
            "checkup_time", sa.types.DateTime(timezone=True), default=datetime.utcnow
        ),
        sa.Column("api_response", sa.types.JSON, nullable=False),
    )
    return my_table


def insert_data_into_channel_messages_table(records: list[dict]):
    stmt = sa.insert(channel_message_table).values(records)
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def insert_data_into_channel_messages_table_advanced(records: list[dict]):
    """
    This function receives a list of records to insert into the channel messages SQL table.
    That table, however, imposes a primary key restriction on unique tuples (channel_id, message_id).
    Incoming messages should therefore be partitioned into new_records and duplicate_records, where
    new records have (channel_id, message_id) tuples that do not match any records in the table, while
    duplicate records do already have matches in the table. These two partitions should be handled
    differently.
    """

    stmt = sa.select(
        channel_message_table.c.channel_id, channel_message_table.c.message_id
    ).filter(
        channel_message_table.c.channel_id.in_(
            [record["channel_id"] for record in records]
        ),
        channel_message_table.c.message_id.in_(
            [record["message_id"] for record in records]
        ),
    )

    with engine.connect() as conn:
        rp = conn.execute(stmt)
        rows = rp.fetchall()
    if len(rows) > 0:
        # there is some overlap, so there would be an integrity violation if you attempted to write
        # these records to the database. Instead, let's partition the records to those that are ok
        # to write to the table, and those that are not ok
        new_records = [
            record
            for record in records
            if (record["channel_id"], record["message_id"]) not in rows
        ]
        duplicate_records = [record for record in records if record not in new_records]
    else:
        new_records = records
        duplicate_records = []

    if len(new_records) > 0:
        stmt = sa.insert(channel_message_table).values(new_records)
        with engine.connect() as conn:
            conn.execute(stmt)
            conn.commit()
    if len(duplicate_records) > 0:
        pass  # Exercise: add code here to update rows, replacing old data with new

    return


def fetch_seed_list_names() -> list[dict]:
    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(seed_table.c.seed_list).distinct(seed_table.c.seed_list)
        )
        rows = rp.fetchall()
    return [row for (row,) in rows]


def fetch_seed_list_preview(my_seed_list_names: list[str]) -> list[dict]:
    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(seed_table).where(seed_table.c.seed_list.in_(my_seed_list_names))
        )
    records = [dict(elt._mapping) for elt in rp.fetchall()]
    return records


def fetch_birth_chart_data(
    seed_list_names: list[str], birth_chart_unit: str
) -> list[dict]:
    seed_channel_ids = list(
        set([seed["channel_id"] for seed in fetch_seed_list_preview(seed_list_names)])
    )

    stmt = (
        sa.select(
            sa.sql.func.date_trunc(
                birth_chart_unit, channel_metadata_table.c.channel_birthdate
            ),
            sa.sql.func.count(),
        )
        .filter(channel_metadata_table.c.channel_id.in_(seed_channel_ids))
        .group_by(
            sa.sql.func.date_trunc(
                birth_chart_unit, channel_metadata_table.c.channel_birthdate
            )
        )
        .order_by(
            sa.sql.func.date_trunc(
                birth_chart_unit, channel_metadata_table.c.channel_birthdate
            )
        )
    )
    with engine.connect() as conn:
        rp = conn.execute(stmt)
    records = [dict(elt._mapping) for elt in rp.fetchall()]
    return [
        {"creation_dt": record["date_trunc_1"], "count": record["count_1"]}
        for record in records
    ]


def fetch_time_series_chart_data(
    seed_list_names: list[str],
    start_date: str,
    end_date: str,
    time_series_chart_unit: str,
) -> list[dict]:
    seed_channel_ids = list(
        set([seed["channel_id"] for seed in fetch_seed_list_preview(seed_list_names)])
    )

    stmt = (
        sa.select(
            sa.sql.func.date_trunc(
                time_series_chart_unit, channel_message_table.c.message_datetime
            ),
            sa.sql.func.count(),
        )
        .filter(
            channel_message_table.c.channel_id.in_(seed_channel_ids),
            channel_message_table.c.message_datetime
            >= datetime.strptime(start_date, "%Y-%m-%d"),
            channel_message_table.c.message_datetime
            <= datetime.strptime(end_date, "%Y-%m-%d"),
        )
        .group_by(
            sa.sql.func.date_trunc(
                time_series_chart_unit, channel_message_table.c.message_datetime
            )
        )
        .order_by(
            sa.sql.func.date_trunc(
                time_series_chart_unit, channel_message_table.c.message_datetime
            )
        )
    )

    with engine.connect() as conn:
        rp = conn.execute(stmt)
    records = [dict(elt._mapping) for elt in rp.fetchall()]
    return [
        {"message_dt": record["date_trunc_1"], "count": record["count_1"]}
        for record in records
    ]


def fetch_top_messages(
    seed_list_names: list[str], start_date: str, end_date: str, the_limit: int
) -> list[dict]:
    seed_channel_ids = list(
        set([seed["channel_id"] for seed in fetch_seed_list_preview(seed_list_names)])
    )

    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(channel_message_table)
            .filter(
                channel_message_table.c.channel_id.in_(seed_channel_ids),
                channel_message_table.c.message_views.is_not(None),
                channel_message_table.c.message_datetime
                >= datetime.strptime(start_date, "%Y-%m-%d"),
                channel_message_table.c.message_datetime
                <= datetime.strptime(end_date, "%Y-%m-%d"),
            )
            .order_by(channel_message_table.c.message_views.desc())
            .limit(the_limit)
        )
    records = [dict(elt._mapping) for elt in rp.fetchall()]
    return records


def fetch_seed_metadata_full(seed_list_names: list[str]) -> list[dict]:
    seed_channel_ids = list(
        set([seed["channel_id"] for seed in fetch_seed_list_preview(seed_list_names)])
    )

    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(channel_metadata_table)
            .where(channel_metadata_table.c.channel_id.in_(seed_channel_ids))
            .order_by(channel_metadata_table.c.num_subscribers.desc())
        )
    records = [dict(elt._mapping) for elt in rp.fetchall()]
    return records


channel_message_table_name = config["telegram-db"]["channel-messages-table"]
channel_metadata_table_name = config["telegram-db"]["channel-metadata-table"]
seed_table_name = config["telegram-db"]["channel-seed-table"]

engine = sa.create_engine(
    f"postgresql://"
    f"{config['telegram-db']['user']}:"
    f"{config['telegram-db']['password']}"
    f"@{config['telegram-db']['host']}:"
    f"{config['telegram-db']['port']}/"
    f"{config['telegram-db']['dbname']}",
    echo=True,
    pool_size=20,
    max_overflow=0,
)


# Define Telegram tables and create them if they don't already exist
meta = sa.MetaData()
channel_message_table = instantiate_channel_messages_table(channel_message_table_name)
channel_metadata_table = instantiate_channel_metadata_table(channel_metadata_table_name)
seed_table = instantiate_seed_table(seed_table_name)
meta.create_all(engine)
