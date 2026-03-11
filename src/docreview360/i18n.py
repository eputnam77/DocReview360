# SPDX-License-Identifier: MIT
"""Internationalization (i18n) support for DocReview360.

Provides:
- Supported locale list
- In-process translation table (English, Spanish, French, German)
- ``translate(key, locale)`` for server-side string lookup
- ``detect_locale(accept_language)`` to pick the best locale from an
  ``Accept-Language`` header value
- ``format_date(dt, locale)`` for locale-aware short date strings
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Supported locales
# ---------------------------------------------------------------------------

SUPPORTED_LOCALES: list[str] = ["en", "es", "fr", "de"]
DEFAULT_LOCALE = "en"

# ---------------------------------------------------------------------------
# Translation table
# Organised as: key → {locale: translated_string}
# Keys follow dot-notation namespacing, e.g. "common.save".
# ---------------------------------------------------------------------------

_TRANSLATIONS: dict[str, dict[str, str]] = {
    # ---- navigation --------------------------------------------------------
    "nav.dashboard": {"en": "Dashboard", "es": "Panel", "fr": "Tableau de bord", "de": "Dashboard"},
    "nav.projects": {"en": "Projects", "es": "Proyectos", "fr": "Projets", "de": "Projekte"},
    "nav.documents": {"en": "Documents", "es": "Documentos", "fr": "Documents", "de": "Dokumente"},
    "nav.admin": {"en": "Admin", "es": "Administración", "fr": "Administration", "de": "Administration"},
    "nav.logout": {"en": "Log out", "es": "Cerrar sesión", "fr": "Déconnexion", "de": "Abmelden"},
    # ---- common actions ----------------------------------------------------
    "common.save": {"en": "Save", "es": "Guardar", "fr": "Enregistrer", "de": "Speichern"},
    "common.cancel": {"en": "Cancel", "es": "Cancelar", "fr": "Annuler", "de": "Abbrechen"},
    "common.delete": {"en": "Delete", "es": "Eliminar", "fr": "Supprimer", "de": "Löschen"},
    "common.edit": {"en": "Edit", "es": "Editar", "fr": "Modifier", "de": "Bearbeiten"},
    "common.submit": {"en": "Submit", "es": "Enviar", "fr": "Soumettre", "de": "Einreichen"},
    "common.loading": {"en": "Loading…", "es": "Cargando…", "fr": "Chargement…", "de": "Laden…"},
    "common.error": {"en": "An error occurred.", "es": "Se produjo un error.", "fr": "Une erreur s'est produite.", "de": "Ein Fehler ist aufgetreten."},
    "common.success": {"en": "Success", "es": "Éxito", "fr": "Succès", "de": "Erfolg"},
    "common.search": {"en": "Search", "es": "Buscar", "fr": "Rechercher", "de": "Suchen"},
    "common.filter": {"en": "Filter", "es": "Filtrar", "fr": "Filtrer", "de": "Filtern"},
    "common.export": {"en": "Export", "es": "Exportar", "fr": "Exporter", "de": "Exportieren"},
    # ---- document states ---------------------------------------------------
    "doc.status.draft": {"en": "Draft", "es": "Borrador", "fr": "Brouillon", "de": "Entwurf"},
    "doc.status.review": {"en": "Under Review", "es": "En revisión", "fr": "En révision", "de": "In Prüfung"},
    "doc.status.approved": {"en": "Approved", "es": "Aprobado", "fr": "Approuvé", "de": "Genehmigt"},
    "doc.status.rejected": {"en": "Rejected", "es": "Rechazado", "fr": "Rejeté", "de": "Abgelehnt"},
    "doc.status.archived": {"en": "Archived", "es": "Archivado", "fr": "Archivé", "de": "Archiviert"},
    # ---- approval workflow -------------------------------------------------
    "approval.approve": {"en": "Approve", "es": "Aprobar", "fr": "Approuver", "de": "Genehmigen"},
    "approval.reject": {"en": "Reject", "es": "Rechazar", "fr": "Rejeter", "de": "Ablehnen"},
    "approval.pending": {"en": "Pending", "es": "Pendiente", "fr": "En attente", "de": "Ausstehend"},
    # ---- errors ------------------------------------------------------------
    "error.not_found": {"en": "Not found.", "es": "No encontrado.", "fr": "Non trouvé.", "de": "Nicht gefunden."},
    "error.forbidden": {"en": "Access denied.", "es": "Acceso denegado.", "fr": "Accès refusé.", "de": "Zugriff verweigert."},
    "error.server": {"en": "Server error. Please try again.", "es": "Error del servidor. Inténtelo de nuevo.", "fr": "Erreur serveur. Réessayez.", "de": "Serverfehler. Bitte erneut versuchen."},
    # ---- date/time labels --------------------------------------------------
    "date.created_at": {"en": "Created", "es": "Creado", "fr": "Créé le", "de": "Erstellt"},
    "date.updated_at": {"en": "Updated", "es": "Actualizado", "fr": "Mis à jour", "de": "Aktualisiert"},
    "date.due_date": {"en": "Due date", "es": "Fecha de vencimiento", "fr": "Date d'échéance", "de": "Fälligkeitsdatum"},
}

# Short date format patterns per locale (used in format_date)
_DATE_FORMATS: dict[str, str] = {
    "en": "%m/%d/%Y",
    "es": "%d/%m/%Y",
    "fr": "%d/%m/%Y",
    "de": "%d.%m.%Y",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def translate(key: str, locale: str = DEFAULT_LOCALE, **kwargs: Any) -> str:
    """Return the translated string for *key* in *locale*.

    Falls back to English if the locale has no translation for this key,
    then to the key itself if English also lacks it.

    ``kwargs`` are substituted via ``str.format_map`` so that translations can
    include ``{placeholder}`` variables.
    """
    locale = _normalise(locale)
    strings = _TRANSLATIONS.get(key, {})
    text = strings.get(locale) or strings.get("en") or key
    if kwargs:
        try:
            text = text.format_map(kwargs)
        except (KeyError, IndexError):
            pass
    return text


def detect_locale(accept_language: str | None) -> str:
    """Pick the best supported locale from an ``Accept-Language`` header value.

    Returns ``DEFAULT_LOCALE`` when no supported locale is found.

    Example::

        detect_locale("fr-CH, fr;q=0.9, en;q=0.8")  # → "fr"
    """
    if not accept_language:
        return DEFAULT_LOCALE
    # Parse "lang[-region][;q=weight]" tokens
    tokens: list[tuple[float, str]] = []
    for part in accept_language.split(","):
        part = part.strip()
        match = re.match(r"^([a-zA-Z]{2,3})(?:-[a-zA-Z0-9]+)?(?:;q=([\d.]+))?", part)
        if match:
            lang = match.group(1).lower()
            weight = float(match.group(2)) if match.group(2) else 1.0
            tokens.append((weight, lang))
    tokens.sort(key=lambda x: x[0], reverse=True)
    for _, lang in tokens:
        if lang in SUPPORTED_LOCALES:
            return lang
    return DEFAULT_LOCALE


def format_date(dt: datetime | None, locale: str = DEFAULT_LOCALE) -> str:
    """Return a locale-appropriate short date string for *dt*.

    Returns an empty string for ``None``.
    """
    if dt is None:
        return ""
    locale = _normalise(locale)
    fmt = _DATE_FORMATS.get(locale, _DATE_FORMATS["en"])
    return dt.strftime(fmt)


def list_locales() -> list[dict[str, str]]:
    """Return metadata for all supported locales."""
    _NAMES: dict[str, str] = {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
    }
    return [
        {"code": code, "name": _NAMES.get(code, code), "is_default": code == DEFAULT_LOCALE}
        for code in SUPPORTED_LOCALES
    ]


def get_namespace(namespace: str, locale: str = DEFAULT_LOCALE) -> dict[str, str]:
    """Return all translation strings that start with ``namespace.`` for *locale*.

    Useful for shipping a locale bundle to the frontend.
    """
    locale = _normalise(locale)
    prefix = namespace + "."
    return {
        key[len(prefix):]: translate(key, locale)
        for key in _TRANSLATIONS
        if key.startswith(prefix)
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalise(locale: str) -> str:
    """Lower-case and strip region subtag; fall back to DEFAULT_LOCALE."""
    if not locale:
        return DEFAULT_LOCALE
    base = locale.strip().lower().split("-")[0].split("_")[0]
    return base if base in SUPPORTED_LOCALES else DEFAULT_LOCALE
