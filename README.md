# Wolkenmeer-Prognose – Fichtelgebirge

Streamlit-Dashboard für den Großen Waldstein (ca. 877 m) und die Kösseine (ca. 939 m).

## Lokal starten

Benötigt Python 3.10 oder neuer.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Kostenlos online veröffentlichen (Streamlit Community Cloud)

1. Melde dich bei GitHub an und erstelle ein **neues privates oder öffentliches Repository**.
2. Entpacke dieses ZIP und lade alle Dateien/Ordner des Projekts in das Repository hoch.
3. Öffne https://share.streamlit.io/ und verbinde dein GitHub-Konto.
4. Wähle das Repository, den Branch (meist `main`) und als Hauptdatei `app.py`.
5. Klicke auf **Deploy**. Nach dem Build stellt Streamlit eine öffentliche URL bereit.
6. Öffne die URL auf dem Handy und speichere sie bei Bedarf auf dem Startbildschirm.

Die Verfügbarkeit kostenloser Hosting- und GitHub-Funktionen kann sich ändern; prüfe die aktuellen Bedingungen beim Anbieter.

## Täglicher automatischer Lauf

Der Workflow `.github/workflows/update.yml` startet nach Aktivierung von GitHub Actions täglich um 04:15 UTC und schreibt eine `data/forecast.json`-Momentaufnahme ins Repository. In Deutschland entspricht das 06:15 Uhr während der Sommerzeit und 05:15 Uhr während der Winterzeit. GitHub-Zeitpläne können sich gelegentlich verzögern; ein manueller Test ist über **Actions → Update forecast snapshot → Run workflow** möglich.

**Wichtig:** In dieser ersten Version dient die tägliche Momentaufnahme zur Archivierung/Grundlage für den nächsten Schritt. Das Dashboard fragt die Wetter-API beim Öffnen bzw. nach Ablauf des 30-Minuten-Caches live ab. Für eine verlässlich komplett automatisierte Veröffentlichung der täglich erzeugten Prognose müssten wir als nächsten Schritt `app.py` so ändern, dass es die gespeicherte Momentaufnahme priorisiert, und optional E-Mail-/Push-Benachrichtigungen ergänzen.

## Wetterquelle und Unsicherheit

Das Dashboard verwendet die Open-Meteo Forecast API. Es zeigt Temperatur, Taupunkt, relative Feuchte, Sichtweite, Bewölkung und Grenzschichthöhe.

Die Nebeloberkante wird **nicht direkt und zuverlässig** von diesen Basisvariablen geliefert. Die derzeitige Formel ist eine grobe Heuristik und kann deutlich falsch liegen. Ein fehlender Schätzwert bedeutet nicht, dass garantiert kein Nebel vorhanden ist. Die Anzeige ist eine Orientierung, keine Garantie für ein Wolkenmeer.

Nächste sinnvolle Ausbaustufen:
- Vertikalprofile der Wettermodelle untersuchen.
- Lokale Webcams und Beobachtungen ergänzen.
- Prognosen gegen frühere Beobachtungen validieren.
- Erst nach Validierung Wahrscheinlichkeiten ausgeben.
