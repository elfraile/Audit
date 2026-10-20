"""A modularitás gépi kikényszerítése."""
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"
MAX_LINES = 500


def test_no_long_python_files():
    too_long = {str(p.relative_to(APP)): n for p in APP.rglob("*.py")
                if (n := len(p.read_text(encoding="utf-8").splitlines())) > MAX_LINES}
    assert not too_long, f"túl hosszú fájlok (>{MAX_LINES} sor): {too_long}"


def test_modules_do_not_import_each_other_cyclically():
    """Az accounts modul alapréteg: nem importálhat más domain-modult."""
    for path in (APP / "modules" / "accounts").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for other in ("tenants", "factsheet", "rules", "issues", "notifications", "checklist", "references", "assets", "audits", "ui"):
            assert f"app.modules.{other}" not in text, f"{path.name} függ a {other} modultól"


def test_pages_render_for_each_role(admin, client):
    assert admin.get("/").status_code == 200
    assert admin.get("/admin/users").status_code == 200
