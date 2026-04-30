from urllib.parse import quote_plus

import requests
from flask import current_app


class GitHubImportError(Exception):
    pass


def _headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "dev-profile-analyzer",
    }
    token = current_app.config.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request(endpoint):
    base_url = current_app.config["GITHUB_API_BASE_URL"].rstrip("/")
    try:
        response = requests.get(
            f"{base_url}{endpoint}",
            headers=_headers(),
            timeout=current_app.config["REQUEST_TIMEOUT"],
        )
    except requests.RequestException as exc:
        raise GitHubImportError("Connexion a GitHub impossible pour le moment.") from exc
    if response.status_code == 404:
        raise GitHubImportError("Utilisateur GitHub introuvable.")
    if response.status_code == 403:
        raise GitHubImportError("Limite GitHub atteinte ou acces refuse.")
    if response.status_code == 422:
        raise GitHubImportError("Requete GitHub invalide. Verifiez les filtres de recherche.")
    if response.status_code >= 400:
        raise GitHubImportError("Echec lors de la recuperation des donnees GitHub.")
    return response.json()


def _safe_int(value):
    return int(value or 0)


def _safe_text(value):
    return str(value or "").strip()


def _safe_positive_int(value, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _normalize_search_filters(
    language="",
    location="",
    min_followers=0,
    min_repositories=0,
    sort="",
    order="desc",
):
    normalized_sort = _safe_text(sort).lower()
    if normalized_sort not in {"", "followers", "repositories", "joined"}:
        normalized_sort = ""

    normalized_order = _safe_text(order).lower() or "desc"
    if normalized_order not in {"asc", "desc"}:
        normalized_order = "desc"

    return {
        "language": _safe_text(language),
        "location": _safe_text(location),
        "min_followers": _safe_positive_int(min_followers, default=0),
        "min_repositories": _safe_positive_int(min_repositories, default=0),
        "sort": normalized_sort,
        "order": normalized_order,
    }


def _build_search_query(query, filters):
    parts = [_safe_text(query)]
    if filters["language"]:
        parts.append(f"language:{filters['language']}")
    if filters["location"]:
        quoted_location = filters["location"].replace('"', "")
        parts.append(f'location:"{quoted_location}"')
    if filters["min_followers"] > 0:
        parts.append(f"followers:>={filters['min_followers']}")
    if filters["min_repositories"] > 0:
        parts.append(f"repos:>={filters['min_repositories']}")
    return " ".join(part for part in parts if part).strip()


def _build_github_candidate(user, repos):
    languages = []
    total_stars = 0
    for repo in repos:
        language = repo.get("language")
        if language:
            languages.append(language)
        total_stars += _safe_int(repo.get("stargazers_count", 0))

    skills = sorted(set(languages))
    repositories = _safe_int(user.get("public_repos", 0))
    followers = _safe_int(user.get("followers", 0))

    return {
        "username": user.get("login", ""),
        "display_name": user.get("name") or user.get("login", ""),
        "source": "github",
        "profile_url": user.get("html_url", ""),
        "avatar_url": user.get("avatar_url", ""),
        "type": user.get("type", ""),
        "bio": user.get("bio") or "",
        "location": user.get("location") or "",
        "followers": followers,
        "repositories": repositories,
        "commits": repositories * 10,
        "stars": total_stars + followers,
        "skills": skills,
    }


def fetch_github_candidate(username):
    user = _request(f"/users/{username}")
    repos = _request(f"/users/{username}/repos?per_page=100&sort=updated")
    candidate = _build_github_candidate(user, repos)
    if not candidate["username"]:
        candidate["username"] = username
    return candidate


def fetch_github_profile(username):
    candidate = fetch_github_candidate(username)
    return {
        "username": candidate["username"],
        "source": candidate["source"],
        "profile_url": candidate["profile_url"],
        "bio": candidate["bio"],
        "location": candidate["location"],
        "repositories": candidate["repositories"],
        "commits": candidate["commits"],
        "stars": candidate["stars"],
        "skills": candidate["skills"],
    }


def _build_search_result(item, user_details):
    candidate = _build_github_candidate(user_details, [])
    candidate["username"] = item.get("login", "") or candidate["username"]
    candidate["display_name"] = user_details.get("name") or item.get("login", "")
    candidate["profile_url"] = user_details.get("html_url") or item.get("html_url", "")
    candidate["avatar_url"] = user_details.get("avatar_url") or item.get("avatar_url", "")
    candidate["type"] = user_details.get("type") or item.get("type", "")
    return candidate


def search_github_users(
    query,
    limit=8,
    language="",
    location="",
    min_followers=0,
    min_repositories=0,
    sort="",
    order="desc",
):
    normalized_query = query.strip()
    if not normalized_query:
        return []

    normalized_limit = max(1, min(int(limit), 20))
    filters = _normalize_search_filters(
        language=language,
        location=location,
        min_followers=min_followers,
        min_repositories=min_repositories,
        sort=sort,
        order=order,
    )
    search_query = _build_search_query(normalized_query, filters)
    endpoint = f"/search/users?q={quote_plus(search_query)}&per_page={normalized_limit}"
    if filters["sort"]:
        endpoint += f"&sort={quote_plus(filters['sort'])}&order={quote_plus(filters['order'])}"
    payload = _request(
        endpoint
    )
    results = []
    for item in payload.get("items", []):
        username = item.get("login", "").strip()
        if not username:
            continue
        user_details = _request(f"/users/{username}")
        results.append(_build_search_result(item, user_details))
    return results
