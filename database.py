
import streamlit as st
import psycopg

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


def get_connection():
    return psycopg.connect(
        host="aws-0-ap-southeast-1.pooler.supabase.com",
        port=5432,
        dbname="postgres",
        user="postgres.sbxomzjphziyposrmqnb",
        password=st.secrets["SUPABASE_DB_PASSWORD"],
        connect_timeout=10,
    )


def create_tables():
    # The tables already exist in Supabase.
    # Do not run SQLite CREATE TABLE or PRAGMA statements here.
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
