# Wolkenmeer- & Fotografie-Prognose
## Starten
`pip install -r requirements.txt`
`streamlit run app.py`

## Kostenlos online stellen
1. ZIP entpacken.
2. Alle enthaltenen Dateien ins GitHub-Repository hochladen; `app.py` muss direkt im Hauptordner liegen.
3. Auf https://share.streamlit.io anmelden, Repository wählen, `app.py` als Hauptdatei angeben und Deploy klicken.

## Funktionen
- Stündliche Temperatur, Taupunkt, Taupunktabstand, Feuchte, tiefe/mittlere/hohe Wolken, Sichtweite, Wind, Böen, Grenzschichthöhe und Niederschlagschance
- Transparenter Nebel-Score für Großen Waldstein und Kösseine
- Sonnenaufgang/-untergang (Näherungsberechnung) und tägliche Lichtdaten
- Wolken-Eignung in Nachtstunden für Astrofotografie
- NOAA Kp-Daten, falls erreichbar

## Wichtige Grenzen
Der Nebel-Score ist KEINE kalibrierte Prozentwahrscheinlichkeit und keine verlässliche Vorhersage der Nebeloberkante. Ein hoher Wert garantiert kein Wolkenmeer. Die Milchstraßenanzeige prüft hier nur die Wolkenbedingungen; Mond, galaktisches Zentrum, astronomische Dämmerung und Lichtverschmutzung werden noch nicht exakt modelliert. Polarlicht ist in Nordbayern selten und Kp allein reicht nicht zur Sichtungsprognose.
Daten: https://open-meteo.com/ und https://www.swpc.noaa.gov/ . Nutzungsbedingungen beachten.
