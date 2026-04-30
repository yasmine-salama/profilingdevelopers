import json
from pathlib import Path

import pandas as pd
from flask import current_app

from app.database import get_db, init_db
from app.services.github_api import fetch_github_profile


def _normalize_skills(skills):
    if skills is None:
        return []
    if isinstance(skills, list):
        normalized = [str(skill).strip() for skill in skills if str(skill).strip()]
        return sorted(set(normalized))
    if isinstance(skills, str):
        normalized = [item.strip() for item in skills.split(",") if item.strip()]
        return sorted(set(normalized))
    return []


def _activity_score(row):
    repositories = int(row.get("repositories", 0) or 0)
    commits = int(row.get("commits", 0) or 0)
    stars = int(row.get("stars", 0) or 0)
    return round(repositories * 1.5 + commits * 0.3 + stars * 0.8, 2)


def _clean_dataframe(df):
    cleaned = df.copy()
    cleaned["username"] = cleaned["username"].fillna("unknown").astype(str).str.strip()
    cleaned["source"] = cleaned["source"].fillna("local").astype(str).str.strip()
    cleaned["profile_url"] = cleaned["profile_url"].fillna("")
    cleaned["bio"] = cleaned["bio"].fillna("")
    cleaned["location"] = cleaned["location"].fillna("")
    cleaned["repositories"] = pd.to_numeric(cleaned["repositories"], errors="coerce").fillna(0).astype(int)
    cleaned["commits"] = pd.to_numeric(cleaned["commits"], errors="coerce").fillna(0).astype(int)
    cleaned["stars"] = pd.to_numeric(cleaned["stars"], errors="coerce").fillna(0).astype(int)
    cleaned["skills"] = cleaned["skills"].apply(_normalize_skills)
    cleaned = cleaned.drop_duplicates(subset=["username", "source"])
    cleaned["activity_score"] = cleaned.apply(_activity_score, axis=1)
    return cleaned


def load_source_data():
    source_path = Path(current_app.config["SAMPLE_DATA_PATH"])
    with source_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return pd.DataFrame(payload)


def _insert_profile_record(db, record):
    existing = db.execute(
        """
        SELECT id
        FROM developers
        WHERE username = ? AND source = ?
        """,
        (record["username"], record["source"]),
    ).fetchone()

    if existing:
        db.execute(
            "DELETE FROM developer_skills WHERE developer_id = ?",
            (existing["id"],),
        )
        db.execute("DELETE FROM developers WHERE id = ?", (existing["id"],))

    cursor = db.execute(
        """
        INSERT INTO developers (
            username, source, profile_url, bio, location,
            repositories, commits, stars, activity_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["username"],
            record["source"],
            record["profile_url"],
            record["bio"],
            record["location"],
            record["repositories"],
            record["commits"],
            record["stars"],
            record["activity_score"],
        ),
    )
    developer_id = cursor.lastrowid
    for skill in record["skills"]:
        db.execute(
            """
            INSERT INTO developer_skills (developer_id, skill_name, skill_score)
            VALUES (?, ?, ?)
            """,
            (developer_id, skill, 1),
        )
    return developer_id


def run_etl():
    init_db()
    dataframe = _clean_dataframe(load_source_data())
    db = get_db()

    db.execute("DELETE FROM developer_skills")
    db.execute("DELETE FROM developers")

    inserted = 0
    for record in dataframe.to_dict(orient="records"):
        _insert_profile_record(db, record)
        inserted += 1

    db.execute(
        """
        INSERT INTO etl_runs (source_name, records_loaded, status)
        VALUES (?, ?, ?)
        """,
        ("sample_developers.json", inserted, "success"),
    )
    db.commit()
    return {"records_loaded": inserted, "status": "success"}


def _prepare_github_record(username):
    github_record = fetch_github_profile(username.strip())
    dataframe = _clean_dataframe(pd.DataFrame([github_record]))
    return dataframe.to_dict(orient="records")[0]


def _normalize_usernames(usernames):
    normalized_usernames = []
    seen = set()
    for username in usernames:
        normalized_username = username.strip()
        if not normalized_username:
            continue
        lowered_username = normalized_username.lower()
        if lowered_username in seen:
            continue
        seen.add(lowered_username)
        normalized_usernames.append(normalized_username)
    return normalized_usernames


def import_github_developer(username):
    init_db()
    record = _prepare_github_record(username)
    db = get_db()

    _insert_profile_record(db, record)
    db.execute(
        """
        INSERT INTO etl_runs (source_name, records_loaded, status)
        VALUES (?, ?, ?)
        """,
        (f"github:{record['username']}", 1, "success"),
    )
    db.commit()
    return record


def import_github_developers(usernames):
    init_db()
    normalized_usernames = _normalize_usernames(usernames)
    if not normalized_usernames:
        return []

    records = [_prepare_github_record(username) for username in normalized_usernames]
    db = get_db()
    imported_records = []
    for record in records:
        _insert_profile_record(db, record)
        imported_records.append(record)
    db.execute(
        """
        INSERT INTO etl_runs (source_name, records_loaded, status)
        VALUES (?, ?, ?)
        """,
        ("github:batch", len(imported_records), "success"),
    )
    db.commit()
    return imported_records
