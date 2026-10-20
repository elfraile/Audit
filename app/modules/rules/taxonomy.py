"""Szabálykategóriák (alapértelmezett készlet). Adat, nem kód: a modulok újakat regisztrálhatnak."""
from app.core.registry import Registry

DEFAULT_CATEGORIES = {
    "presence": "Kötelező elem jelenléte",
    "text_content": "Szöveges tartalom",
    "terminology": "Megnevezések, terminológia",
    "brand_element": "Márkaelem-használat",
    "placement": "Elhelyezés, elrendezés",
    "readability": "Olvashatóság",
    "channel_constraint": "Csatorna-korlát",
    "consistency": "Konzisztencia a kampányadatokkal",
    "tone": "Hangvétel, üzenet",
    "unclassified": "Besorolatlan",
}


def register_defaults(categories: Registry) -> None:
    for key, label in DEFAULT_CATEGORIES.items():
        categories.register(key, label)
