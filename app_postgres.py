import streamlit as st
import pandas as pd
from datetime import date
import html
import random
import time

SCRIPT_START = time.perf_counter()



from database import (
    get_connection,
    create_tables,
    insert_default_tags
)


# ============================================================
# DATABASE SETUP
# ============================================================
# Supabase tables and default tags have already been created.
# Do not run database initialization on every page interaction.


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Academic English Sentence Bank",
    page_icon="🌸",
    layout="wide"
)



# ============================================================
# LOAD CUSTOM CSS
# ============================================================
with open("style.css", "r", encoding="utf-8") as css_file:
    st.markdown(
        f"<style>{css_file.read()}</style>",
        unsafe_allow_html=True
    )



# ============================================================
# SESSION STATE
# ============================================================

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "browse"

if "selected_sentence_id" not in st.session_state:
    st.session_state["selected_sentence_id"] = None

if "recommend_seed" not in st.session_state:
    st.session_state["recommend_seed"] = 0

if "quick_review_seed" not in st.session_state:
    st.session_state["quick_review_seed"] = 0

if "confirm_delete" not in st.session_state:
    st.session_state["confirm_delete"] = False

if "delete_ids" not in st.session_state:
    st.session_state["delete_ids"] = []


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def go_to_page(page, sentence_id=None):

    st.session_state["current_page"] = page
    st.session_state["selected_sentence_id"] = sentence_id

    st.rerun()



@st.cache_data(ttl=300, show_spinner=False)
def get_all_tags():

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute(
                "SELECT name FROM functions ORDER BY id"
            )
            functions = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT name FROM sections ORDER BY id"
            )
            sections = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT name FROM domains ORDER BY name"
            )
            domains = [row[0] for row in cursor.fetchall()]

    finally:
        conn.close()

    return functions, sections, domains



def get_sentence_tags(sentence_id):

    conn = get_connection()
    cursor = conn.cursor()

    # Functions
    cursor.execute("""
        SELECT f.name
        FROM sentence_functions sf
        JOIN functions f
            ON sf.function_id = f.id
        WHERE sf.sentence_id = %s
        ORDER BY f.id
    """, (sentence_id,))

    functions = [
        row[0]
        for row in cursor.fetchall()
    ]

    # Sections
    cursor.execute("""
        SELECT s.name
        FROM sentence_sections ss
        JOIN sections s
            ON ss.section_id = s.id
        WHERE ss.sentence_id = %s
        ORDER BY s.id
    """, (sentence_id,))

    sections = [
        row[0]
        for row in cursor.fetchall()
    ]

    # Domains
    cursor.execute("""
        SELECT d.name
        FROM sentence_domains sd
        JOIN domains d
            ON sd.domain_id = d.id
        WHERE sd.sentence_id = %s
        ORDER BY d.name
    """, (sentence_id,))

    domains = [
        row[0]
        for row in cursor.fetchall()
    ]

    conn.close()

    return functions, sections, domains


def update_tags(
    sentence_id,
    functions,
    sections,
    domains
):

    conn = get_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------
    # Functions
    # --------------------------------------------------------

    cursor.execute(
        """
        DELETE FROM sentence_functions
        WHERE sentence_id = %s
        """,
        (sentence_id,)
    )

    for function_name in functions:

        cursor.execute(
            """
            SELECT id
            FROM functions
            WHERE name = %s
            """,
            (function_name,)
        )

        result = cursor.fetchone()

        if result:

            cursor.execute(
                """
                INSERT INTO sentence_functions
                (sentence_id, function_id)
                VALUES (%s, %s)
ON CONFLICT DO NOTHING
""",
                (
                    sentence_id,
                    result[0]
                )
            )

    # --------------------------------------------------------
    # Sections
    # --------------------------------------------------------

    cursor.execute(
        """
        DELETE FROM sentence_sections
        WHERE sentence_id = %s
        """,
        (sentence_id,)
    )

    for section_name in sections:

        cursor.execute(
            """
            SELECT id
            FROM sections
            WHERE name = %s
            """,
            (section_name,)
        )

        result = cursor.fetchone()

        if result:

            cursor.execute(
                """
                INSERT INTO sentence_sections
                (sentence_id, section_id)
                VALUES (%s, %s)
ON CONFLICT DO NOTHING
""",
                (
                    sentence_id,
                    result[0]
                )
            )

    # --------------------------------------------------------
    # Domains
    # --------------------------------------------------------

    cursor.execute(
        """
        DELETE FROM sentence_domains
        WHERE sentence_id = %s
        """,
        (sentence_id,)
    )

    for domain_name in domains:

        cursor.execute(
            """
            SELECT id
            FROM domains
            WHERE name = %s
            """,
            (domain_name,)
        )

        result = cursor.fetchone()

        if result:

            cursor.execute(
                """
                INSERT INTO sentence_domains
                (sentence_id, domain_id)
                VALUES (%s, %s)
ON CONFLICT DO NOTHING
""",
                (
                    sentence_id,
                    result[0]
                )
            )

    conn.commit()
    conn.close()


def save_sentence_changes(
    sentence_id,
    sentence_text,
    source_text,
    keywords_text,
    remember_value,
    use_value,
    functions,
    sections,
    domains
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE sentences
        SET sentence = %s,
            source = %s,
            keywords = %s,
            remember_count = %s,
            use_count = %s
        WHERE id = %s
        """,
        (
            sentence_text,
            source_text,
            keywords_text,
            max(0, int(remember_value)),
            max(0, int(use_value)),
            sentence_id
        )
    )

    conn.commit()
    conn.close()

    update_tags(
        sentence_id,
        functions,
        sections,
        domains
    )


def delete_sentences(sentence_ids):

    conn = get_connection()
    cursor = conn.cursor()

    for sentence_id in sentence_ids:

        cursor.execute(
            """
            DELETE FROM sentence_functions
            WHERE sentence_id = %s
            """,
            (sentence_id,)
        )

        cursor.execute(
            """
            DELETE FROM sentence_sections
            WHERE sentence_id = %s
            """,
            (sentence_id,)
        )

        cursor.execute(
            """
            DELETE FROM sentence_domains
            WHERE sentence_id = %s
            """,
            (sentence_id,)
        )

        cursor.execute(
            """
            DELETE FROM review_attempts
            WHERE sentence_id = %s
            """,
            (sentence_id,)
        )

        cursor.execute(
            """
            DELETE FROM learning_records
            WHERE sentence_id = %s
            """,
            (sentence_id,)
        )

        cursor.execute(
            """
            DELETE FROM sentences
            WHERE id = %s
            """,
            (sentence_id,)
        )

    conn.commit()
    conn.close()


def get_sentence(sentence_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            sentence,
            source,
            keywords,
            remember_count,
            use_count,
            last_reviewed
        FROM sentences
        WHERE id = %s
        """,
        (sentence_id,)
    )

    row = cursor.fetchone()

    conn.close()

    return row


def ensure_learning_records_table():
    """Create a separate history table for genuine review sessions."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_records (
                    id BIGSERIAL PRIMARY KEY,
                    sentence_id BIGINT NOT NULL,
                    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    remember_count INTEGER NOT NULL DEFAULT 0,
                    use_count INTEGER NOT NULL DEFAULT 0,
                    mastery_level TEXT NOT NULL DEFAULT 'Learning',
                    practice_text TEXT
                )
            """)
        conn.commit()
    finally:
        conn.close()



@st.cache_data(ttl=60, show_spinner=False)
def get_learning_dashboard_data():
    """Return the three learning-progress metrics shown on Browse."""
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM learning_records
            """)
            total_reviews = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*)
                FROM learning_records
                WHERE reviewed_at >= CURRENT_DATE
                  AND reviewed_at < CURRENT_DATE + INTERVAL '1 day'
            """)
            today_reviews = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT sentence_id)
                FROM learning_records
            """)
            reviewed_sentences = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT DISTINCT ON (sentence_id)
                        sentence_id, mastery_level
                    FROM learning_records
                    ORDER BY sentence_id, reviewed_at DESC, id DESC
                ) latest
                WHERE mastery_level = 'Mastered'
            """)
            mastered_sentences = cursor.fetchone()[0]

        return total_reviews, reviewed_sentences, mastered_sentences, [], [], today_reviews

    finally:
        conn.close()



@st.cache_data(ttl=300, show_spinner=False)
def get_keyword_phrases():
    """Read existing keyword/pattern phrases from the sentence bank."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT keywords
                FROM sentences
                WHERE keywords IS NOT NULL
                  AND TRIM(keywords) <> ''
            """)
            rows = cursor.fetchall()
        phrases = []
        for row in rows:
            for item in (row[0] or "").replace("\\n", ";").split(";"):
                item = item.strip()
                if item and item.lower() != "nan":
                    phrases.append(item)
        return list(dict.fromkeys(phrases))
    finally:
        conn.close()


def get_sentences_by_keyword_phrase(selected_phrase):
    """Return sentences whose keyword field contains the exact phrase."""
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, sentence, source, keywords
                FROM sentences
                WHERE keywords IS NOT NULL
                  AND TRIM(keywords) <> ''
                ORDER BY id DESC
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()

    matched_rows = []

    for row in rows:
        keywords_text = row[3] or ""

        # Support semicolons and actual line breaks.
        phrases_in_sentence = [
            item.strip()
            for item in keywords_text.replace("\\n", "\n").split(";")
            for item in item.splitlines()
            if item.strip()
        ]

        if any(
            phrase.casefold() == selected_phrase.casefold()
            for phrase in phrases_in_sentence
        ):
            matched_rows.append(row)

    return matched_rows


def render_keyword_cloud(phrases):
    """Display clickable keyword phrases in a soft pink grid."""
    if not phrases:
        st.caption("No keywords or patterns found yet.")
        return

    rng = random.Random(
        st.session_state["quick_review_seed"]
    )
    shown = rng.sample(phrases, min(40, len(phrases)))
    rng.shuffle(shown)

    st.caption("Select a phrase to find its source sentences.")

    pink_colors = [
        "#FFF0F3",
        "#FCE7EF",
        "#F9EAF2",
        "#FDF1F5",
    ]

    st.markdown(
        """
        <style>
        div[class*="st-key-quick_phrase_"] button {
            color: #76515F !important;
            border: 1px solid #F0D5E0 !important;
            transition: background-color 0.2s ease;
        }
        div[class*="st-key-quick_phrase_"] button:hover {
            border-color: #DDA7BC !important;
            color: #76515F !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(4)

    for index, phrase in enumerate(shown):
        with columns[index % 4]:
            color = pink_colors[index % len(pink_colors)]

            st.markdown(
                f"""
                <style>
                div.st-key-quick_phrase_{index}_{hash(phrase)} button {{
                    background-color: {color} !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                phrase,
                key=f"quick_phrase_{index}_{hash(phrase)}",
                use_container_width=True,
                help=f"Find sentences containing: {phrase}"
            ):
                st.session_state["selected_keyword_phrase"] = phrase
                st.rerun()






# ============================================================
# TAGS
# ============================================================

all_functions, all_sections, all_domains = get_all_tags()


# ============================================================
# GLOBAL HEADER
# ============================================================

st.title("Academic English Sentence Bank")

st.caption(
    "A personal database for collecting, organising, "
    "and reviewing academic English sentences."
)


# ============================================================
# NAVIGATION
# ============================================================


current_page = st.session_state["current_page"]

nav1, nav2, nav3 = st.columns(3)

with nav1:
    if st.button(
        "Import",
        width="stretch"
    ):
        go_to_page("add")

with nav2:
    if st.button(
        "Browse",
        width="stretch"
    ):
        go_to_page("browse")

with nav3:
    if st.button(
        "Recommend",
        width="stretch"
    ):
        go_to_page("recommend")

st.divider()



@st.cache_data(ttl=60, show_spinner=False)
def get_recommendation_rows():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    sentence,
                    source,
                    keywords,
                    remember_count,
                    use_count
                FROM sentences
                """
            )
            return cursor.fetchall()
    finally:
        conn.close()



# ============================================================
# PAGE 1 — IMPORT
# ============================================================

if current_page == "add":
    
    if "import_success_count" not in st.session_state:
        st.session_state.import_success_count = None

    st.header("➕ Add a New Sentence")

    sentence = st.text_area(
        "Sentence",
        placeholder="Paste your academic sentence here...",
        height=120
    )

    source = st.text_input(
        "Source",
        placeholder=(
            "e.g., Moorhouse & Kohnke (2024), "
            "or the publication title"
        )
    )

    keywords = st.text_input(
        "Keywords / Pattern",
        placeholder=(
            "e.g., may suggest that; "
            "in contrast to"
        )
    )

    selected_functions = st.multiselect(
        "Function",
        options=all_functions
    )

    selected_sections = st.multiselect(
        "Section",
        options=all_sections
    )

    selected_domains = st.multiselect(
        "Domain",
        options=all_domains
    )

    if st.button(
        "➕ Add Sentence",
        type="primary"
    ):

        if not sentence.strip():

            st.warning(
                "Please enter a sentence."
            )

        else:

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO sentences
                (sentence, source, keywords)
                VALUES (%s, %s, %s)
RETURNING id
                """,
                (
                    sentence.strip(),
                    source.strip(),
                    keywords.strip()
                )
            )

            sentence_id = cursor.fetchone()[0]

            conn.commit()
            conn.close()

            update_tags(
                sentence_id,
                selected_functions,
                selected_sections,
                selected_domains
            )

            st.success(
                "✅ Sentence added successfully!"
            )


    # --------------------------------------------------------
    # IMPORT EXCEL
    # --------------------------------------------------------

    st.divider()

    st.header("📥 Import Sentences from Excel")

    
    uploaded_file = st.file_uploader(
        "Upload your Excel file",
        type=["xlsx"],
        key="excel_upload"
    )

    
    if st.session_state.import_success_count is not None:
        imported_count = st.session_state.import_success_count

        st.success(
            f"Successfully imported {imported_count} sentence(s)!"
        )

        st.write("Would you like to clear the current import area?")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Clear import area", key="clear_import_area"):
                st.session_state.import_success_count = None
                st.session_state["excel_upload"] = None
                st.rerun()

        with col2:
            if st.button("Keep current content", key="keep_import_content"):
                st.session_state.import_success_count = None
                st.rerun()


    if uploaded_file is not None:

        try:

            import_df = pd.read_excel(
                uploaded_file
            )

            required_columns = [
                "Sentence",
                "Function",
                "Section",
                "Domain",
                "Keywords / Pattern",
                "Source"
            ]

            missing_columns = [
                column
                for column in required_columns
                if column not in import_df.columns
            ]

            if missing_columns:

                st.error(
                    "Missing columns: "
                    + ", ".join(missing_columns)
                )

            else:

                st.write("### Preview")

                st.dataframe(
                    import_df,
                    width="stretch",
                    hide_index=True
                )

                st.write(
                    f"**{len(import_df)} sentence(s) "
                    f"ready to import.**"
                )

                if st.button(
                    "🚀 Import to Database",
                    type="primary"
                ):

                    conn = get_connection()
                    cursor = conn.cursor()

                    imported_count = 0

                    for _, row in import_df.iterrows():

                        sentence_text = str(
                            row["Sentence"]
                        ).strip()

                        if (
                            not sentence_text
                            or sentence_text.lower() == "nan"
                        ):
                            continue

                        source_text = str(
                            row["Source"]
                        ).strip()

                        keywords_text = str(
                            row["Keywords / Pattern"]
                        ).strip()

                        cursor.execute(
                            """
                            INSERT INTO sentences
                            (sentence, source, keywords)
                            VALUES (%s, %s, %s)
RETURNING id
                            """,
                            (
                                sentence_text,
                                source_text,
                                keywords_text
                            )
                        )

                        sentence_id = cursor.fetchone()[0]

                        # Function

                        function_text = str(
                            row["Function"]
                        ).strip()

                        if function_text.lower() == "nan":
                            function_text = ""

                        function_list = [
                            x.strip()
                            for x in function_text.split(";")
                            if x.strip()
                        ]

                        for function_name in function_list:

                            cursor.execute(
                                """
                                INSERT INTO functions
                                (name)
                                VALUES (%s)
ON CONFLICT DO NOTHING
""",
                                (function_name,)
                            )

                            cursor.execute(
                                """
                                SELECT id
                                FROM functions
                                WHERE name = %s
                                """,
                                (function_name,)
                            )

                            result = cursor.fetchone()

                            if result:

                                cursor.execute(
                                    """
                                    INSERT INTO
                                    sentence_functions
                                    (sentence_id, function_id)
                                    VALUES (%s, %s)
ON CONFLICT DO NOTHING
""",
                                    (
                                        sentence_id,
                                        result[0]
                                    )
                                )

                        # Section

                        section_text = str(
                            row["Section"]
                        ).strip()

                        if section_text.lower() == "nan":
                            section_text = ""

                        section_list = [
                            x.strip()
                            for x in section_text.split(";")
                            if x.strip()
                        ]

                        for section_name in section_list:

                            cursor.execute(
                                """
                                INSERT INTO sections
                                (name)
                                VALUES (%s)
ON CONFLICT DO NOTHING
""",
                                (section_name,)
                            )

                            cursor.execute(
                                """
                                SELECT id
                                FROM sections
                                WHERE name = %s
                                """,
                                (section_name,)
                            )

                            result = cursor.fetchone()

                            if result:

                                cursor.execute(
                                    """
                                    INSERT INTO
                                    sentence_sections
                                    (sentence_id, section_id)
                                    VALUES (%s, %s)
ON CONFLICT DO NOTHING
""",
                                    (
                                        sentence_id,
                                        result[0]
                                    )
                                )

                        # Domain

                        domain_text = str(
                            row["Domain"]
                        ).strip()

                        if domain_text.lower() == "nan":
                            domain_text = ""

                        domain_list = [
                            x.strip()
                            for x in domain_text.split(";")
                            if x.strip()
                        ]

                        for domain_name in domain_list:

                            cursor.execute(
                                """
                                INSERT INTO domains
                                (name)
                                VALUES (%s)
ON CONFLICT DO NOTHING
""",
                                (domain_name,)
                            )

                            cursor.execute(
                                """
                                SELECT id
                                FROM domains
                                WHERE name = %s
                                """,
                                (domain_name,)
                            )

                            result = cursor.fetchone()

                            if result:

                                cursor.execute(
                                    """
                                    INSERT INTO
                                    sentence_domains
                                    (sentence_id, domain_id)
                                    VALUES (%s, %s)
ON CONFLICT DO NOTHING
""",
                                    (
                                        sentence_id,
                                        result[0]
                                    )
                                )

                        imported_count += 1

                    conn.commit()
                    conn.close()
                    # Refresh cached tags and keywords after importing
                    get_all_tags.clear()
                    get_keyword_phrases.clear()

                    st.session_state.import_success_count = imported_count
                    st.rerun()

        except Exception as e:

            st.error(
                f"Something went wrong: {e}"
            )


# ============================================================
# PAGE 2 — BROWSE
# ============================================================

elif current_page == "browse":


    # Learning progress dashboard
    try:
        total_reviews, reviewed_sentences, mastered_sentences, recent_records, _, today_reviews = get_learning_dashboard_data()

        with st.expander("Learning Progress", expanded=True):
            progress_col1, progress_col2, progress_col3 = st.columns(3)
            progress_col1.metric("Review sessions", total_reviews)
            progress_col2.metric("Sentences reviewed", reviewed_sentences)
            progress_col3.metric("Currently mastered", mastered_sentences)
            
            daily_goal = 10
            daily_progress = min(today_reviews / daily_goal, 1.0)

            st.markdown(
                f"""
                <div class="daily-progress-card">
                    <div class="daily-progress-heading">
                        <span>🌸 Today's Review</span>
                        <span>{today_reviews} / {daily_goal}</span>
                    </div>
                    <div class="daily-progress-track">
                        <div class="daily-progress-fill"
                             style="width: {daily_progress * 100}%;">
                        </div>
                    </div>
                    <div class="daily-progress-caption">
                        {daily_progress * 100:.0f}% completed ·
                        Keep growing, one sentence at a time.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


    except Exception as e:
        st.warning(f"Learning progress could not be loaded: {e}")

        # Quick Review: clickable keyword phrases and related sentences
    with st.expander("Quick Review", expanded=True):

        refresh_col, _ = st.columns([1, 8])

        with refresh_col:
            if st.button("Refresh", key="refresh_quick_review"):
                st.session_state["quick_review_seed"] += 1
                st.rerun()

        try:
            render_keyword_cloud(get_keyword_phrases())
        except Exception as e:
            st.warning(f"Quick Review could not be loaded: {e}")

        # Display sentences associated with the selected phrase
        selected_phrase = st.session_state.get(
            "selected_keyword_phrase"
        )

        if selected_phrase:
            st.divider()

            header_col, clear_col = st.columns([5, 1])

            with header_col:
                st.subheader(f"{selected_phrase}")

            with clear_col:
                if st.button(
                    "Clear",
                    key="clear_selected_keyword"
                ):
                    st.session_state["selected_keyword_phrase"] = None
                    st.rerun()

            try:
                related_sentences = get_sentences_by_keyword_phrase(
                    selected_phrase
                )

                if not related_sentences:
                    st.info("No matching sentences found.")

                else:
                    st.caption(
                        f"{len(related_sentences)} related sentence(s)"
                    )

                    for row in related_sentences:
                        sentence_id, sentence_text, source_text, keywords_text = row

                        with st.container(border=True):
                            st.write(sentence_text)

                            if source_text:
                                st.caption(f"Source: {source_text}")

                            review_col, _ = st.columns([1, 5])

                            with review_col:
                                if st.button(
                                    "Review →",
                                    key=f"quick_phrase_review_{sentence_id}",
                                    type="primary"
                                ):
                                    go_to_page(
                                        "review",
                                        int(sentence_id)
                                    )

            except Exception as e:
                st.warning(
                    f"Could not load related sentences: {e}"
                )

    # ===== Quick Review ends here. Keep everything below unchanged. =====

    st.divider()

    search_text = st.text_input(
        "Search",
        placeholder="Search sentence, keywords, or source..."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        filter_function = st.multiselect(
            "Filter by Function",
            all_functions
        )

    with col2:
        filter_section = st.multiselect(
            "Filter by Section",
            all_sections
        )

    with col3:
        filter_domain = st.multiselect(
            "Filter by Domain",
            all_domains
        )



    # Aggregate each tag type separately to reduce intermediate rows.
    query = """
        WITH function_tags AS (
            SELECT
                sf.sentence_id,
                ARRAY_AGG(f.name ORDER BY f.name) AS functions
            FROM sentence_functions sf
            JOIN functions f ON f.id = sf.function_id
            GROUP BY sf.sentence_id
        ),
        section_tags AS (
            SELECT
                ss.sentence_id,
                ARRAY_AGG(sec.name ORDER BY sec.name) AS sections
            FROM sentence_sections ss
            JOIN sections sec ON sec.id = ss.section_id
            GROUP BY ss.sentence_id
        ),
        domain_tags AS (
            SELECT
                sd.sentence_id,
                ARRAY_AGG(d.name ORDER BY d.name) AS domains
            FROM sentence_domains sd
            JOIN domains d ON d.id = sd.domain_id
            GROUP BY sd.sentence_id
        )
        SELECT
            s.id,
            s.sentence,
            s.source,
            s.keywords,
            s.remember_count,
            s.use_count,
            s.last_reviewed,
            COALESCE(ft.functions, ARRAY[]::text[]) AS functions,
            COALESCE(st.sections, ARRAY[]::text[]) AS sections,
            COALESCE(dt.domains, ARRAY[]::text[]) AS domains
        FROM sentences s
        LEFT JOIN function_tags ft ON ft.sentence_id = s.id
        LEFT JOIN section_tags st ON st.sentence_id = s.id
        LEFT JOIN domain_tags dt ON dt.sentence_id = s.id
    """


    conditions = []
    parameters = []

    if filter_function:
        placeholders = ", ".join(
            ["%s"] * len(filter_function)
        )
        conditions.append(
            f"""
            EXISTS (
                SELECT 1
                FROM sentence_functions sf2
                JOIN functions f2
                    ON sf2.function_id = f2.id
                WHERE sf2.sentence_id = s.id
                AND f2.name IN ({placeholders})
            )
            """
        )
        parameters.extend(filter_function)

    if filter_section:
        placeholders = ", ".join(
            ["%s"] * len(filter_section)
        )
        conditions.append(
            f"""
            EXISTS (
                SELECT 1
                FROM sentence_sections ss2
                JOIN sections sec2
                    ON ss2.section_id = sec2.id
                WHERE ss2.sentence_id = s.id
                AND sec2.name IN ({placeholders})
            )
            """
        )
        parameters.extend(filter_section)

    if filter_domain:
        placeholders = ", ".join(
            ["%s"] * len(filter_domain)
        )
        conditions.append(
            f"""
            EXISTS (
                SELECT 1
                FROM sentence_domains sd2
                JOIN domains d2
                    ON sd2.domain_id = d2.id
                WHERE sd2.sentence_id = s.id
                AND d2.name IN ({placeholders})
            )
            """
        )
        parameters.extend(filter_domain)

    if search_text.strip():
        conditions.append(
            """
            (
                s.sentence ILIKE %s
                OR s.keywords ILIKE %s
                OR s.source ILIKE %s
            )
            """
        )
        pattern = f"%{search_text.strip()}%"
        parameters.extend([pattern, pattern, pattern])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY s.id DESC"


    # Measure Browse database query
    browse_query_start = time.perf_counter()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, parameters)
            rows = cursor.fetchall()
    finally:
        conn.close()

    browse_query_time = time.perf_counter() - browse_query_start

    print(
        f"[PERF] Browse query: {browse_query_time:.2f}s | "
        f"Rows: {len(rows)}"
    )


    # Tags are already included in each query result.
    # Keep ID and Source internally, but hide them in the UI.
    table_data = []

    for row in rows:
        table_data.append({
            "Select": False,
            "ID": row[0],
            "Sentence": row[1],
            "Function": row[7] or [],
            "Section": row[8] or [],
            "Domain": row[9] or [],
            "Keywords / Pattern": row[3] or "",
            "Remember": row[4] or 0,
            "Use": row[5] or 0,
            "Last Reviewed": row[6] or "",
            "Source": row[2] or "",
        })

    browse_df = pd.DataFrame(table_data)


    edited_df = st.data_editor(
        browse_df,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "✓",
                help="Select sentences",
                width="small"
            ),
            "ID": None,
            "Sentence": st.column_config.TextColumn(
                "Sentence",
                width="large"
            ),
            "Function": st.column_config.MultiselectColumn(
                "Function",
                options=all_functions,
                width="medium"
            ),
            "Section": st.column_config.MultiselectColumn(
                "Section",
                options=all_sections,
                width="medium"
            ),
            "Domain": st.column_config.MultiselectColumn(
                "Domain",
                options=all_domains,
                width="medium"
            ),
            "Keywords / Pattern": st.column_config.TextColumn(
                "Keywords / Pattern",
                width="medium"
            ),
            "Remember": st.column_config.NumberColumn(
                "Remember",
                min_value=0,
                step=1,
                width="small"
            ),
            "Use": st.column_config.NumberColumn(
                "Use",
                min_value=0,
                step=1,
                width="small"
            ),
            "Last Reviewed": st.column_config.TextColumn(
                "Last Reviewed",
                disabled=True,
                width="small"
            ),
            "Source": None,
        },
        disabled=["ID", "Last Reviewed", "Source"],
        key="browse_sentence_table"
    )

    # Save only rows whose content actually changed
    original_content = (
        browse_df
        .drop(columns=["Select"])
        .reset_index(drop=True)
    )

    edited_content = (
        edited_df
        .drop(columns=["Select"])
        .reset_index(drop=True)
    )

    changed_indices = [
        i
        for i in range(len(edited_content))
        if not edited_content.iloc[i].equals(
            original_content.iloc[i]
        )
    ]

    if changed_indices:
        for i in changed_indices:
            edited_row = edited_df.iloc[i]

            functions = edited_row["Function"]
            sections = edited_row["Section"]
            domains = edited_row["Domain"]

            if not isinstance(functions, list):
                functions = []
            if not isinstance(sections, list):
                sections = []
            if not isinstance(domains, list):
                domains = []

            save_sentence_changes(
                int(edited_row["ID"]),
                str(edited_row["Sentence"]).strip(),
                str(edited_row["Source"] or "").strip(),
                str(edited_row["Keywords / Pattern"] or "").strip(),
                max(0, int(edited_row["Remember"] or 0)),
                max(0, int(edited_row["Use"] or 0)),
                functions,
                sections,
                domains
            )

        st.success(
            f"Saved changes to {len(changed_indices)} sentence(s)."
        )
        st.rerun()

    # Select sentences for review or deletion
    selected_ids = edited_df.loc[
        edited_df["Select"] == True,
        "ID"
    ].tolist()

    if selected_ids:
        st.divider()
        st.write(
            f"**{len(selected_ids)} sentence(s) selected.**"
        )

        action_col1, action_col2 = st.columns(2)

        with action_col1:
            if st.button(
                "Review",
                type="primary",
                key="review_selected_browse"
            ):
                if len(selected_ids) == 1:
                    go_to_page("review", int(selected_ids[0]))
                else:
                    st.warning(
                        "Please select only one sentence to review at a time."
                    )

        with action_col2:
            if st.button(
                "Delete",
                key="delete_selected_browse"
            ):
                st.session_state["confirm_delete"] = True
                st.session_state["delete_ids"] = [
                    int(x) for x in selected_ids
                ]
                st.rerun()

    # Delete confirmation
    if st.session_state.get("confirm_delete", False):
        delete_ids = st.session_state.get("delete_ids", [])

        st.warning(
            f"Are you sure you want to delete {len(delete_ids)} sentence(s)?"
        )

        confirm_col1, confirm_col2 = st.columns(2)

        with confirm_col1:
            if st.button(
                "Yes, Delete",
                key="yes_delete_browse"
            ):
                delete_sentences(delete_ids)
                st.session_state["confirm_delete"] = False
                st.session_state["delete_ids"] = []
                st.success("Sentences deleted.")
                st.rerun()

        with confirm_col2:
            if st.button(
                "Cancel",
                key="cancel_delete_browse"
            ):
                st.session_state["confirm_delete"] = False
                st.session_state["delete_ids"] = []
                st.rerun()


# ============================================================
# PAGE 3 — REVIEW
# ============================================================

elif current_page == "review":

    selected_id = (
        st.session_state.get(
            "selected_sentence_id"
        )
    )


    # --------------------------------------------------------
    # If no sentence selected
    # --------------------------------------------------------

    if not selected_id:

        st.info(
            "Choose a sentence from Browse or Recommend "
            "to start reviewing."
        )

        st.write("")

        if st.button(
            "🔍 Go to Browse",
            type="primary"
        ):

            go_to_page("browse")


    else:

        selected_row = get_sentence(
            selected_id
        )


        if not selected_row:

            st.warning(
                "This sentence no longer exists."
            )

            if st.button(
                "← Back to Browse"
            ):

                go_to_page("browse")


        else:

            sentence_id = selected_row[0]

            sentence_text = selected_row[1]

            source_text = selected_row[2]

            keywords_text = selected_row[3]

            remember_count = selected_row[4]

            use_count = selected_row[5]

            last_reviewed = selected_row[6]


            functions, sections, domains = (
                get_sentence_tags(
                    sentence_id
                )
            )


            # ------------------------------------------------
            # BACK BUTTON
            # ------------------------------------------------

            if st.button(
                "← Back",
                key="review_back_top"
            ):

                go_to_page("browse")


            st.divider()


            # ------------------------------------------------
            # SENTENCE
            # ------------------------------------------------

            st.markdown(
                "### Sentence"
            )

            safe_sentence = html.escape(
                sentence_text
            )

            st.markdown(
                f"""
                <div style="
                    font-size: 28px;
                    line-height: 1.7;
                    padding: 28px;
                    border-radius: 12px;
                    border: 1px solid #d9d9d9;
                    background-color: #fafafa;
                    margin-bottom: 20px;
                ">
                {safe_sentence}
                </div>
                """,
                unsafe_allow_html=True
            )


            # ------------------------------------------------
            # INFORMATION
            # ------------------------------------------------

            st.markdown(
                "### Information"
            )

            info_col1, info_col2 = (
                st.columns(2)
            )


            with info_col1:

                st.write(
                    "**Function:** "
                    + (
                        ", ".join(functions)
                        if functions
                        else "—"
                    )
                )

                st.write(
                    "**Section:** "
                    + (
                        ", ".join(sections)
                        if sections
                        else "—"
                    )
                )

                st.write(
                    "**Domain:** "
                    + (
                        ", ".join(domains)
                        if domains
                        else "—"
                    )
                )


            with info_col2:

                st.write(
                    "**Keywords / Pattern:** "
                    + (
                        keywords_text
                        if keywords_text
                        else "—"
                    )
                )

                st.write(
                    "**Source:** "
                    + (
                        source_text
                        if source_text
                        else "—"
                    )
                )


            # ------------------------------------------------
            # PROGRESS
            # ------------------------------------------------

            st.divider()

            st.markdown(
                "### Learning Progress"
            )

            progress_col1, progress_col2, progress_col3 = (
                st.columns(3)
            )


            with progress_col1:

                new_remember = st.number_input(
                    "Remember",
                    min_value=0,
                    value=int(remember_count),
                    step=1,
                    key=f"review_remember_{sentence_id}"
                )


            with progress_col2:

                new_use = st.number_input(
                    "Use",
                    min_value=0,
                    value=int(use_count),
                    step=1,
                    key=f"review_use_{sentence_id}"
                )


            with progress_col3:

                st.write(
                    "**Last Reviewed**"
                )

                st.write(
                    last_reviewed
                    if last_reviewed
                    else "Never"
                )


            mastery_level = st.selectbox(
                "Current mastery",
                ["Not started", "Learning", "Getting familiar", "Confident", "Mastered"],
                index=1,
                key=f"mastery_{sentence_id}"
            )


            # ------------------------------------------------
            # PRACTICE
            # ------------------------------------------------

            st.divider()

            st.markdown(
                "### Your Practice"
            )

            st.caption(
                "Write your own sentence using this "
                "sentence as a model. You can copy "
                "your sentence to ChatGPT later if "
                "you want feedback."
            )

            practice_text = st.text_area(
                "Your sentence",
                placeholder=(
                    "Write your own academic sentence here..."
                ),
                height=150,
                key=f"practice_{sentence_id}"
            )


            # ------------------------------------------------
            # SAVE
            # ------------------------------------------------

            if st.button(
                "Save Progress",
                type="primary",
                key=f"save_review_{sentence_id}"
            ):

                today = date.today().isoformat()

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    UPDATE sentences
                    SET remember_count = %s,
                        use_count = %s,
                        last_reviewed = %s
                    WHERE id = %s
                    """,
                    (
                        int(new_remember),
                        int(new_use),
                        today,
                        sentence_id
                    )
                )

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS learning_records (
                        id BIGSERIAL PRIMARY KEY,
                        sentence_id BIGINT NOT NULL,
                        reviewed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        remember_count INTEGER NOT NULL DEFAULT 0,
                        use_count INTEGER NOT NULL DEFAULT 0,
                        mastery_level TEXT NOT NULL DEFAULT 'Learning',
                        practice_text TEXT
                    )
                """)
                cursor.execute(
                    """
                    INSERT INTO learning_records
                        (sentence_id, remember_count, use_count, mastery_level, practice_text)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        sentence_id,
                        int(new_remember),
                        int(new_use),
                        mastery_level,
                        practice_text.strip() if practice_text else None
                    )
                )

                conn.commit()
                conn.close()

                st.success(
                    f"✅ Saved. Last reviewed: {today}"
                )

                st.rerun()


# ============================================================
# PAGE 4 — RECOMMEND
# ============================================================

elif current_page == "recommend":


    # --------------------------------------------------------
    # REFRESH
    # --------------------------------------------------------

    refresh_col1, refresh_col2 = st.columns(
        [5, 1]
    )

    with refresh_col2:

        if st.button(
            "🔄 Refresh",
            key="refresh_recommendations"
        ):
            get_recommendation_rows.clear()
            
            st.session_state[
                "recommend_seed"
            ] += 1

            st.rerun()

   
    # --------------------------------------------------------
    # GET SENTENCES
    # --------------------------------------------------------

    all_rows = get_recommendation_rows()

    if not all_rows:
        st.info(
            "Your sentence bank is empty."
        )



    else:

        # ----------------------------------------------------
        # RECOMMENDATION LOGIC
        # ----------------------------------------------------
        #
        # Lower Remember + lower Use
        # = higher priority.
        #
        # RANDOM is used to make refresh produce
        # different recommendations when possible.
        # ----------------------------------------------------

        random.seed(
            st.session_state["recommend_seed"]
        )

        shuffled_rows = list(
            all_rows
        )

        random.shuffle(
            shuffled_rows
        )

        shuffled_rows.sort(
            key=lambda row: (
                int(row[4] or 0)
                + int(row[5] or 0)
            )
        )

        recommended_rows = (
            shuffled_rows[:5]
        )


        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        for row in recommended_rows:

            sentence_id = row[0]

            sentence_text = row[1]

            source_text = row[2]

            keywords_text = row[3]

            remember_count = row[4]

            use_count = row[5]


            with st.container(
                border=True
            ):

                safe_sentence = html.escape(
                    sentence_text
                )


                # --------------------------------------------
                # Sentence
                # --------------------------------------------

                st.markdown(
                    f"""
                    <div style="
                        font-size: 22px;
                        line-height: 1.6;
                        margin-bottom: 12px;
                    ">
                    {safe_sentence}
                    </div>
                    """,
                    unsafe_allow_html=True
                )


                # --------------------------------------------
                # Bottom information
                # --------------------------------------------

                bottom_col1, bottom_col2, bottom_col3 = (
                    st.columns([6, 1, 1])
                )


                with bottom_col1:

                    if keywords_text:

                        st.caption(
                            f"Pattern: {keywords_text}"
                        )


                with bottom_col2:

                    st.caption(
                        f"🧠 {remember_count}"
                    )


                with bottom_col3:

                    st.caption(
                        f"✍️ {use_count}"
                    )


                # --------------------------------------------
                # Review
                # --------------------------------------------

                if st.button(
                    "Review →",
                    key=f"recommend_review_{sentence_id}"
                ):

                    # IMPORTANT:
                    # Change the page state BEFORE rerun.
                    # This makes Review replace Recommend.
                    go_to_page(
                        "review",
                        sentence_id
                    )




print(
    f"[PERF] Page: {st.session_state.get('current_page', 'unknown')} | "
    f"Total script time: {time.perf_counter() - SCRIPT_START:.2f}s"
)

# ============================================================
# END
# ============================================================