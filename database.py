
import streamlit as st
import psycopg
from psycopg_pool import ConnectionPool


FUNCTIONS = [
    "Being cautious",
    "Being critical",
    "Classifying and listing",
    "Comparing and contrasting",
    "Defining terms",
    "Describing data and trends",
    "Explaining causality",
    "Giving examples",
    "Linking sentences",
    "Identifying research gaps",
]

SECTIONS = [
    "Introduction",
    "Literature Review",
    "Methods",
    "Results",
    "Discussion",
    "Conclusion / Implications",
]


# ============================================================
# DATABASE CONNECTION POOL
# ============================================================

@st.cache_resource
def get_connection_pool():
    return ConnectionPool(
        conninfo=(
            "host=aws-0-ap-southeast-1.pooler.supabase.com "
            "port=5432 "
            "dbname=postgres "
            "user=postgres.sbxomzjphziyposrmqnb "
            "connect_timeout=10"
        ),
        kwargs={
            "password": st.secrets["SUPABASE_DB_PASSWORD"],
        },
        min_size=1,
        max_size=5,
        timeout=10,
        open=True,
    )



class PooledConnection:
    """Return connections to the pool when existing code calls close()."""

    def __init__(self, pool, connection):
        self._pool = pool
        self._connection = connection
        self._closed = False

    def __getattr__(self, name):
        return getattr(self._connection, name)


    def close(self):
        if not self._closed:
            self._closed = True
            try:
                if not self._connection.closed:
                    self._connection.rollback()
            finally:
                self._pool.putconn(self._connection)



def get_connection():
    pool = get_connection_pool()
    connection = pool.getconn()
    return PooledConnection(pool, connection)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def create_tables():
    # Tables already exist in Supabase.
    # Do not initialize the database on every page interaction.
    pass


def insert_default_tags():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            for function in FUNCTIONS:
                cursor.execute(
                    """
                    INSERT INTO functions (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    (function,),
                )

            for section in SECTIONS:
                cursor.execute(
                    """
                    INSERT INTO sections (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    (section,),
                )

        conn.commit()

    finally:
        conn.close()


if __name__ == "__main__":
    create_tables()
    insert_default_tags()
    print("Supabase connection and default tags checked.")
