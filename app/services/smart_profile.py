import re

from app.database import get_db
from app.services.github_api import GitHubImportError, fetch_github_candidate


ROLE_KEYWORDS = {
    "Backend Engineer": {"python", "java", "go", "api", "django", "flask", "fastapi"},
    "Frontend Engineer": {"javascript", "typescript", "react", "vue", "angular", "css"},
    "Data Engineer": {"python", "sql", "spark", "etl", "pandas", "airflow", "data"},
    "DevOps Engineer": {"docker", "kubernetes", "aws", "azure", "terraform", "ci", "cd"},
    "Full Stack Engineer": {
        "python",
        "javascript",
        "typescript",
        "react",
        "sql",
        "api",
    },
}

SENIORITY_THRESHOLDS = (
    (80, "Senior"),
    (60, "Confirmed"),
    (35, "Intermediate"),
    (0, "Junior"),
)

STOP_WORDS = {
    "and",
    "avec",
    "dans",
    "des",
    "for",
    "from",
    "github",
    "les",
    "pour",
    "profil",
    "profile",
    "sur",
    "the",
    "une",
    "use",
}


def _normalize_skills(skills):
    normalized = []
    for skill in skills or []:
        value = str(skill).strip()
        if value:
            normalized.append(value)
    return sorted(set(normalized))


def _tokenize(text):
    tokens = re.findall(r"[a-z0-9+#._-]{2,}", (text or "").lower())
    return [token for token in tokens if token not in STOP_WORDS]


def _clamp(value, min_value=0, max_value=100):
    return max(min_value, min(float(value), max_value))


def _score_breakdown(candidate):
    repositories = int(candidate.get("repositories", 0) or 0)
    commits = int(candidate.get("commits", 0) or 0)
    stars = int(candidate.get("stars", 0) or 0)
    followers = int(candidate.get("followers", 0) or 0)
    skills_count = len(candidate.get("skills", []))
    has_bio = 1 if candidate.get("bio") else 0
    has_location = 1 if candidate.get("location") else 0

    breakdown = {
        "portfolio_strength": round(_clamp(repositories * 2.4), 1),
        "delivery_signal": round(_clamp(commits / 3), 1),
        "community_signal": round(_clamp((stars * 0.4) + (followers * 1.2)), 1),
        "skills_depth": round(_clamp(skills_count * 9), 1),
        "profile_completeness": round((has_bio * 12) + (has_location * 8), 1),
    }
    total_score = round(sum(breakdown.values()) / len(breakdown), 1)
    return breakdown, total_score


def _classify_domains(skills):
    joined = " ".join(skill.lower() for skill in skills)
    domain_checks = [
        ("Backend", {"python", "java", "go", "flask", "django", "fastapi", "spring"}),
        ("Frontend", {"javascript", "typescript", "react", "vue", "angular", "css"}),
        ("Data", {"pandas", "numpy", "sql", "spark", "airflow", "data", "etl"}),
        ("DevOps", {"docker", "kubernetes", "aws", "azure", "terraform", "ci/cd"}),
        ("Mobile", {"android", "ios", "swift", "kotlin", "flutter"}),
    ]
    domains = []
    for label, keywords in domain_checks:
        if any(keyword in joined for keyword in keywords):
            domains.append(label)
    return domains or ["Generalist"]


def _build_strengths(candidate, total_score):
    strengths = []
    skills = candidate.get("skills", [])
    if skills:
        strengths.append(f"Stack visible avec {len(skills)} technologies detectees.")
    if int(candidate.get("repositories", 0) or 0) >= 10:
        strengths.append("Portfolio GitHub substantiel avec plusieurs repositories publics.")
    if int(candidate.get("stars", 0) or 0) >= 25:
        strengths.append("Signal communautaire positif via stars et followers.")
    if candidate.get("bio"):
        strengths.append("Presentation personnelle exploitable pour une analyse contextuelle.")
    if total_score >= 65:
        strengths.append("Profil globalement solide pour un screening initial rapide.")
    return strengths or ["Profil exploitable mais avec peu de signaux publics disponibles."]


def _build_focus_areas(candidate):
    focus_areas = []
    if len(candidate.get("skills", [])) < 3:
        focus_areas.append("Completer la stack technique avec plus de projets ou technologies visibles.")
    if not candidate.get("bio"):
        focus_areas.append("Ajouter une bio pour mieux contextualiser l'expertise et les objectifs.")
    if int(candidate.get("repositories", 0) or 0) < 5:
        focus_areas.append("Augmenter la profondeur du portfolio public.")
    if int(candidate.get("stars", 0) or 0) < 10:
        focus_areas.append("Renforcer la visibilite communautaire et les signaux de traction.")
    return focus_areas or ["Aucun point faible majeur detecte sur les signaux publics observes."]


def _recommended_roles(skills):
    skill_tokens = {skill.lower() for skill in skills}
    scored_roles = []
    for role, keywords in ROLE_KEYWORDS.items():
        overlap = len(skill_tokens & keywords)
        if overlap:
            scored_roles.append((overlap, role))
    scored_roles.sort(reverse=True)
    return [role for _, role in scored_roles[:3]] or ["Software Engineer"]


def _build_summary(candidate, total_score, domains, recommended_roles):
    return (
        f"{candidate['display_name']} presente un profil {candidate['seniority'].lower()} "
        f"oriente {', '.join(domains).lower()}, avec un score intelligent de {total_score}/100. "
        f"Les roles les plus naturels sont {', '.join(recommended_roles).lower()}."
    )


def _match_job_description(candidate, job_description):
    normalized_description = (job_description or "").strip()
    if not normalized_description:
        return {
            "job_description": "",
            "score": None,
            "matched_keywords": [],
            "missing_keywords": [],
            "recommendation": "Ajoutez une fiche de poste pour calculer un matching cible.",
        }

    job_keywords = sorted(set(_tokenize(normalized_description)))
    profile_keywords = set(
        _tokenize(candidate.get("bio", ""))
        + _tokenize(candidate.get("location", ""))
        + [skill.lower() for skill in candidate.get("skills", [])]
        + _tokenize(" ".join(candidate.get("recommended_roles", [])))
    )
    matched_keywords = [keyword for keyword in job_keywords if keyword in profile_keywords]
    missing_keywords = [keyword for keyword in job_keywords if keyword not in profile_keywords]

    base_match = (len(matched_keywords) / max(len(job_keywords), 1)) * 100
    score = round((_clamp(base_match) * 0.7) + (candidate["smart_score"] * 0.3), 1)

    if score >= 75:
        recommendation = "Bonne adequation initiale pour un entretien technique."
    elif score >= 55:
        recommendation = "Adequation partielle; verifier les competences manquantes en entretien."
    else:
        recommendation = "Adequation faible a ce stade; profil a requalifier selon le besoin."

    return {
        "job_description": normalized_description,
        "score": score,
        "matched_keywords": matched_keywords[:12],
        "missing_keywords": missing_keywords[:12],
        "recommendation": recommendation,
    }


def _hydrate_candidate(candidate):
    skills = _normalize_skills(candidate.get("skills", []))
    candidate["skills"] = skills
    candidate["display_name"] = candidate.get("display_name") or candidate.get("username", "")
    candidate["followers"] = int(candidate.get("followers", 0) or 0)
    breakdown, total_score = _score_breakdown(candidate)
    candidate["score_breakdown"] = breakdown
    candidate["smart_score"] = total_score
    candidate["seniority"] = next(
        label for threshold, label in SENIORITY_THRESHOLDS if total_score >= threshold
    )
    candidate["domains"] = _classify_domains(skills)
    candidate["recommended_roles"] = _recommended_roles(skills)
    candidate["strengths"] = _build_strengths(candidate, total_score)
    candidate["focus_areas"] = _build_focus_areas(candidate)
    candidate["summary"] = _build_summary(
        candidate, total_score, candidate["domains"], candidate["recommended_roles"]
    )
    return candidate


def get_developer_candidate(developer_id):
    row = get_db().execute(
        """
        SELECT
            id,
            username,
            source,
            profile_url,
            bio,
            location,
            repositories,
            commits,
            stars,
            activity_score
        FROM developers
        WHERE id = ?
        """,
        (developer_id,),
    ).fetchone()
    if not row:
        return None

    skill_rows = get_db().execute(
        """
        SELECT skill_name
        FROM developer_skills
        WHERE developer_id = ?
        ORDER BY skill_name ASC
        """,
        (developer_id,),
    ).fetchall()

    candidate = dict(row)
    candidate["display_name"] = candidate["username"]
    candidate["followers"] = 0
    candidate["avatar_url"] = ""
    candidate["type"] = "Imported profile"
    candidate["skills"] = [skill_row["skill_name"] for skill_row in skill_rows]
    return candidate


def build_smart_profile_from_candidate(candidate, job_description=""):
    enriched_candidate = _hydrate_candidate(dict(candidate))
    job_match = _match_job_description(enriched_candidate, job_description)
    return {
        "candidate": enriched_candidate,
        "job_match": job_match,
    }


def build_smart_profile_for_developer(developer_id, job_description=""):
    candidate = get_developer_candidate(developer_id)
    if not candidate:
        return None
    return build_smart_profile_from_candidate(candidate, job_description=job_description)


def build_smart_profile_for_github(username, job_description=""):
    candidate = fetch_github_candidate(username)
    return build_smart_profile_from_candidate(candidate, job_description=job_description)
