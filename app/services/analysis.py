import json

import plotly.express as px

from app.database import get_db


def _rows_to_dicts(rows):
    return [dict(row) for row in rows]


def get_summary():
    db = get_db()
    totals = db.execute(
        """
        SELECT
            COUNT(*) AS total_profiles,
            COALESCE(SUM(repositories), 0) AS total_repositories,
            COALESCE(SUM(commits), 0) AS total_commits,
            ROUND(COALESCE(AVG(activity_score), 0), 2) AS average_activity
        FROM developers
        """
    ).fetchone()

    latest_run = db.execute(
        """
        SELECT run_date, records_loaded, status
        FROM etl_runs
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    return {
        "total_profiles": totals["total_profiles"],
        "total_repositories": totals["total_repositories"],
        "total_commits": totals["total_commits"],
        "average_activity": totals["average_activity"],
        "latest_run": dict(latest_run) if latest_run else None,
    }


def get_profiles(filters=None):
    db = get_db()
    query = """
        SELECT
            id,
            username,
            source,
            profile_url,
            location,
            repositories,
            commits,
            stars,
            activity_score
        FROM developers
        WHERE 1=1
    """
    params = []

    if filters:
        if filters.get("username"):
            query += " AND username LIKE ?"
            params.append(f"%{filters['username']}%")
        if filters.get("location"):
            query += " AND location LIKE ?"
            params.append(f"%{filters['location']}%")
        if filters.get("skill"):
            query += """
                AND id IN (
                    SELECT developer_id
                    FROM developer_skills
                    WHERE skill_name LIKE ?
                )
            """
            params.append(f"%{filters['skill']}%")

    query += " ORDER BY activity_score DESC, username ASC"

    rows = db.execute(query, params).fetchall()
    return _rows_to_dicts(rows)


def get_profiles_by_ids(ids):
    if not ids:
        return []
    placeholders = ",".join(["?"] * len(ids))
    rows = get_db().execute(
        f"""
        SELECT
            id,
            username,
            source,
            profile_url,
            location,
            repositories,
            commits,
            stars,
            activity_score,
            avatar_url,
            bio
        FROM developers
        WHERE id IN ({placeholders})
        """,
        ids,
    ).fetchall()
    profiles = _rows_to_dicts(rows)

    # Fetch skills for each profile
    for profile in profiles:
        skill_rows = get_db().execute(
            "SELECT skill_name FROM developer_skills WHERE developer_id = ?",
            (profile["id"],),
        ).fetchall()
        profile["skills"] = [row["skill_name"] for row in skill_rows]

    return profiles


def get_top_skills(limit=10):
    rows = get_db().execute(
        """
        SELECT skill_name, COUNT(*) AS occurrences
        FROM developer_skills
        GROUP BY skill_name
        ORDER BY occurrences DESC, skill_name ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return _rows_to_dicts(rows)


def build_skills_chart():
    dataset = get_top_skills()
    if not dataset:
        return None

    figure = px.bar(
        dataset,
        x="skill_name",
        y="occurrences",
        title="Technologies les plus detectees",
        labels={"skill_name": "Technologie", "occurrences": "Occurrences"},
    )
    figure.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=380)
    return figure.to_html(full_html=False, include_plotlyjs="cdn")


def build_activity_chart():
    dataset = get_profiles()
    if not dataset:
        return None

    figure = px.scatter(
        dataset,
        x="repositories",
        y="commits",
        size="stars",
        color="source",
        hover_name="username",
        title="Activite des developpeurs",
        labels={"repositories": "Repositories", "commits": "Commits"},
    )
    figure.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=420)
    return figure.to_html(full_html=False, include_plotlyjs=False)


def get_skills_distribution_json():
    return json.dumps(get_top_skills())
