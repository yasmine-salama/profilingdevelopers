import csv
import io
from flask import Blueprint, flash, redirect, render_template, request, url_for, Response

from app.database import init_db
from app.services.analysis import (
    build_activity_chart,
    build_skills_chart,
    get_profiles,
    get_profiles_by_ids,
    get_summary,
    get_top_skills,
)
from app.services.etl import (
    import_github_developer,
    import_github_developers,
    run_etl,
)
from app.services.github_api import GitHubImportError, search_github_users
from app.services.smart_profile import (
    build_smart_profile_for_developer,
    build_smart_profile_for_github,
)


main_bp = Blueprint("main", __name__)
DEFAULT_GITHUB_SEARCH_LIMIT = 12
DEFAULT_GITHUB_SEARCH_FILTERS = {
    "query": "",
    "limit": DEFAULT_GITHUB_SEARCH_LIMIT,
    "language": "",
    "location": "",
    "min_followers": 0,
    "min_repositories": 0,
    "sort": "",
    "order": "desc",
}


def _get_search_limit(raw_value):
    try:
        return max(1, min(int(raw_value), 20))
    except (TypeError, ValueError):
        return DEFAULT_GITHUB_SEARCH_LIMIT


def _get_non_negative_int(raw_value):
    try:
        return max(0, int(raw_value))
    except (TypeError, ValueError):
        return 0


def _get_sort_value(raw_value):
    normalized = (raw_value or "").strip().lower()
    if normalized in {"followers", "repositories", "joined"}:
        return normalized
    return ""


def _get_order_value(raw_value):
    normalized = (raw_value or "").strip().lower()
    if normalized in {"asc", "desc"}:
        return normalized
    return "desc"


def _build_search_filters(values):
    return {
        "query": values.get("q", "").strip(),
        "limit": _get_search_limit(values.get("limit")),
        "language": values.get("language", "").strip(),
        "location": values.get("location", "").strip(),
        "min_followers": _get_non_negative_int(values.get("min_followers")),
        "min_repositories": _get_non_negative_int(values.get("min_repositories")),
        "sort": _get_sort_value(values.get("sort")),
        "order": _get_order_value(values.get("order")),
    }


def _search_github_with_filters(search_filters):
    if not search_filters["query"]:
        return []
    return search_github_users(
        search_filters["query"],
        limit=search_filters["limit"],
        language=search_filters["language"],
        location=search_filters["location"],
        min_followers=search_filters["min_followers"],
        min_repositories=search_filters["min_repositories"],
        sort=search_filters["sort"],
        order=search_filters["order"],
    )


def _render_dashboard(search_results=None, search_filters=None, db_filters=None):
    init_db()
    normalized_results = search_results or []
    normalized_filters = dict(DEFAULT_GITHUB_SEARCH_FILTERS)
    if search_filters:
        normalized_filters.update(search_filters)
    summary = get_summary()
    profiles = get_profiles(filters=db_filters)
    top_skills = get_top_skills()
    skills_chart = build_skills_chart()
    activity_chart = build_activity_chart()
    return render_template(
        "dashboard.html",
        summary=summary,
        profiles=profiles,
        top_skills=top_skills,
        skills_chart=skills_chart,
        activity_chart=activity_chart,
        search_results=normalized_results,
        search_filters=normalized_filters,
        db_filters=db_filters or {},
    )


def _handle_dashboard_with_search(search_filters, db_filters=None):
    search_results = []
    if search_filters["query"]:
        try:
            search_results = _search_github_with_filters(search_filters)
        except GitHubImportError as exc:
            flash(str(exc), "error")
    return _render_dashboard(
        search_results=search_results,
        search_filters=search_filters,
        db_filters=db_filters,
    )


def _build_db_filters(values):
    return {
        "username": values.get("db_username", "").strip(),
        "location": values.get("db_location", "").strip(),
        "skill": values.get("db_skill", "").strip(),
    }


@main_bp.route("/")
def index():
    init_db()
    summary = get_summary()
    return render_template("index.html", summary=summary)


@main_bp.route("/run-etl", methods=["POST"])
def launch_etl():
    result = run_etl()
    flash(
        f"ETL execute avec succes : {result['records_loaded']} profils charges.",
        "success",
    )
    return redirect(url_for("main.dashboard"))


@main_bp.route("/import-github", methods=["POST"])
def import_github():
    username = request.form.get("github_username", "").strip()
    if not username:
        flash("Veuillez saisir un nom d'utilisateur GitHub.", "error")
        return redirect(url_for("main.dashboard"))

    try:
        profile = import_github_developer(username)
    except GitHubImportError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.dashboard"))
    except Exception:
        flash("Une erreur inattendue est survenue pendant l'import GitHub.", "error")
        return redirect(url_for("main.dashboard"))

    flash(
        f"Profil GitHub importe avec succes : {profile['username']}.",
        "success",
    )
    return redirect(url_for("main.dashboard"))


@main_bp.route("/search-github", methods=["GET"])
def search_github():
    search_filters = _build_search_filters(request.args)
    if not search_filters["query"]:
        flash("Veuillez saisir un mot-cle pour la recherche GitHub.", "error")

    return _handle_dashboard_with_search(search_filters)


@main_bp.route("/import-github-batch", methods=["POST"])
def import_github_batch():
    usernames = request.form.getlist("github_usernames")
    search_filters = _build_search_filters(request.form)
    if not usernames:
        flash("Veuillez selectionner au moins un profil GitHub.", "error")
        return _handle_dashboard_with_search(search_filters)

    try:
        imported_records = import_github_developers(usernames)
    except GitHubImportError as exc:
        flash(str(exc), "error")
        return _handle_dashboard_with_search(search_filters)
    except Exception:
        flash("Une erreur inattendue est survenue pendant l'import en lot.", "error")
        return _handle_dashboard_with_search(search_filters)

    flash(
        f"{len(imported_records)} profil(s) GitHub importe(s) avec succes.",
        "success",
    )
    return redirect(url_for("main.dashboard", **search_filters))


@main_bp.route("/dashboard")
def dashboard():
    search_filters = _build_search_filters(request.args)
    db_filters = _build_db_filters(request.args)
    return _handle_dashboard_with_search(search_filters, db_filters=db_filters)


@main_bp.route("/export-csv")
def export_csv():
    db_filters = _build_db_filters(request.args)
    profiles = get_profiles(filters=db_filters)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Username", "Source", "Location", "Repositories",
        "Commits", "Stars", "Activity Score", "Profile URL"
    ])

    for p in profiles:
        writer.writerow([
            p["username"], p["source"], p["location"], p["repositories"],
            p["commits"], p["stars"], p["activity_score"], p["profile_url"]
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=profiles_export.csv"}
    )


@main_bp.route("/compare", methods=["POST"])
def compare_profiles():
    developer_ids = request.form.getlist("developer_ids")
    if len(developer_ids) < 2:
        flash("Veuillez selectionner au moins deux profils pour comparer.", "error")
        return redirect(url_for("main.dashboard"))

    profiles = get_profiles_by_ids(developer_ids)
    return render_template("compare.html", profiles=profiles)


@main_bp.route("/smart-profile/developer/<int:developer_id>", methods=["GET", "POST"])
def smart_profile_developer(developer_id):
    init_db()
    job_description = request.values.get("job_description", "").strip()
    smart_profile = build_smart_profile_for_developer(
        developer_id,
        job_description=job_description,
    )
    if not smart_profile:
        flash("Profil introuvable pour le Smart Candidate Profiling.", "error")
        return redirect(url_for("main.dashboard"))

    return render_template(
        "smart_profile.html",
        smart_profile=smart_profile,
        profile_source="imported",
    )


@main_bp.route("/smart-profile/github/<username>", methods=["GET", "POST"])
def smart_profile_github(username):
    init_db()
    job_description = request.values.get("job_description", "").strip()
    try:
        smart_profile = build_smart_profile_for_github(
            username,
            job_description=job_description,
        )
    except GitHubImportError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.dashboard"))

    return render_template(
        "smart_profile.html",
        smart_profile=smart_profile,
        profile_source="github_search",
    )
