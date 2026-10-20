# Audit – tartalmi megfelelőségi audit rendszer

Jelenlegi állapot: **0–4. lépés** (webes váz, jogosultság, Ügyfél → Kampány hierarchia, kampány-adatlap, szabálykártyák, hibalista, megjegyzések, értesítések, leadási jelölők, kreatív asset beolvasás és szöveges audit motor, **vizuális referencia-tár és szemantikai döntési modell ellenőrzések**).

## Indítás

```
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
python -m pytest
```

Első belépés: `AUDIT_ADMIN_EMAIL` / `AUDIT_ADMIN_PASSWORD` (alapértelmezés: `admin@example.local` / `admin`; élesben állítsd át, és adj meg `AUDIT_SECRET_KEY`-t).
Beállítások `AUDIT_` előtagú környezeti változóval vagy `.env`-ből, lásd `app/core/config.py`.

## Modularitási szabályok (tesztek kényszerítik: `tests/test_modularity.py`)

1. **Tiszta, moduláris fájlméret:** nincsenek ezer soros monolitikus kódok; minden komponens felelősség szerint van bontva.
2. **Minden képesség önálló modul** az `app/modules/<név>/` alatt: `models`, `service` (logika), `router` (HTTP), `module.py` (`setup(ctx)` összekötés). A mag (`app/core`) nem ismer domain-modult.
3. **A modulok listája konfiguráció** (`AUDIT_MODULES`). Új képesség = új mappa + egy sor; kikapcsolás = sor törlése.
4. **Moduloknak nincs kemény adatbázis-kapcsolata egymás között**: modulok közti hivatkozás sima azonosító (nem FK) ott, ahol a szétválasztás fontos.
5. **Bővítési pontok adatként, nem kódként:** `Registry` (szabálykategóriák, kinyerők, ellenőrző eszközök), a szabály `check`/`applies_to` mezője szabad JSON, az `EventBus` a modulok közti reakciókra, `ui_extras` az oldalakra kerülő extra adatokhoz.
6. **Port + adapter:** a modellfüggő részek (pl. szabály-kinyerés, beágyazó, döntési modell) egy `Protocol` mögött vannak; a megvalósítás konfigurációból vagy környezetből cserélhető (OpenRouter, helyi llama-server vagy offline fallback).
7. **Szigorú absztrakt logika:** rendszerpromptokba nem kerülnek konkrét példák, toposzok vagy szövegidézetek; tiszta strukturális állapotkiértékelés valósul meg.

## Szerkezet

```
app/
  core/          config, db, events, registry, security, modules (betöltő), clock
  modules/
    accounts/      felhasználók, szerepkörök, hozzáférés (ügyfél/kampány szint)
    tenants/       ügyfél -> kampány, kampány-hozzáférés ellenőrzés (guards)
    factsheet/     verziózott kampány-tényadat, nyitott kérdések, javasolt módosítások
    rules/         szabály-életciklus, kinyerők (extraction/), kategóriák
    issues/        hibalista-tételek, megjegyzések, állapotok
    notifications/ értesítések, @megjelölés (az issues eseményeire iratkozik fel)
    checklist/     leadási jelölők
    references/    márkaelem és termék referencia-tár (jóváhagyott logók, csomagolások)
    assets/        kreatív anyagok beolvasása (PDF/kép), réteg-deduplikáció, előnézet generálás
    audits/        tartalmi audit motor (determinisztikus + vizuális referencia + döntési modell)
      ai/          multimodális beágyazás (embedder) és döntési modellek (Clef-omni / VLM)
    ui/            szerveroldali weboldal (sablonok: templates/)
tests/
```

## Vizuális és Szemantikai Ellenőrzés Működése

1. **Referencia-tár (`references`):**
   - Ügyfél vagy kampány szinten feltölthetők hivatalos logók, termékcsomagolások és képi elemek.
   - Vizuális beágyazás generálása és tárolása.
2. **Vizuális referencia ellenőrzése (`check_visual_reference`):**
   - Amikor egy szabály képi elem meglétét írja elő (`visual_ref_id`), a motor összeveti a referenciát és a vizsgált asset előnézetét koszinusz hasonlósággal.
   - Ha a hasonlóság eléri a küszöböt (`min_similarity`), az ellenőrzés sikeres (`PASSED`).
3. **Szemantikai döntési modell (`check_decision_rule`):**
   - Olyan szubjektív/szemantikai szabályokhoz (hangnem, elrendezési forma, vizuális hangsúly), ahol hagyományos regex nem alkalmazható.
   - Döntési modell architektúra (Clef-omni / multimodális döntéshozó): az állapot és a kérdés alapján kalibrált valószínűségeket generál a megadott opciókra (`yes`/`no`).
   - Ha a modell bizonyossága meghaladja a küszöböt (`min_prob`), egyértelmű ítélet születik (`PASSED` / `FAILED`); bizonytalanság esetén a rendszer automatikusan emberi felülvizsgálatra irányítja (`WARNING`).

## Következő lépések (a terv szerint)

5. Webes konnektorok és verzióösszevetés – Adobe XD és élő URL bejárás; nyitott hibalista-tételek automatikus lezárás-javaslata új asset verzió beérkezésekor.
