# Analyse-Repository
# Thema der Hausarbeit: "Analyse von BGH-Urteilen und EuGH-Urteilen zu Corona"

Dieses Repository enthält den computerlinguistischen Analyse-Code und die Datengrundlage zur Untersuchung pandemiebezogener Entscheidungen des BGH und des EuGH für meine wissenschaftliche Hausarbeit zur Vorlesung Data Science und Text Mining. 

## Über die Arbeit
Im Rahmen meiner Hausarbeit wurde die höchstrichterliche Rechtsprechung zu pandemiebezogenen Fragestellungen (Zeitraum 2020–2025) systematisch erfasst. Ziel war es, mittels Legal NLP inhaltliche Schwerpunkte und zeitliche Dynamiken der Rechtsprechung datengestützt zu identifizieren.

## Repository-Struktur
Das Repository ist wie folgt gegliedert, um eine einfache Nachvollziehbarkeit der Analyse zu gewährleisten:

/data/: Enthält die bereinigten Datensätze (urteile_cleaned.pkl und Urteile_Bereinigt.csv), die als Grundlage für die Modelle dienen.

/scripts/: Beinhaltet die Jupyter Notebooks zur TF-IDF-Gewichtung, zur LDA- und zur NMF-Modellierung, sowie die Python-Skripte zur Vorfilterung des Korpus.

/config/: Enthält die Konfigurationsdatei zur Steuerung der Analyseparameter im Rahmen der TF-IDF-Gewichtung.

Ferner beinhaltet das Repository noch eine requirements.txt zur einfacheren Reproduzierbarkeit.

## Erstellerin
Julia Pusch | Universität Regensburg | 6. Semester LL.B. Digital Law

Hinweis: Eine detaillierte methodische Herleitung sowie die juristische Interpretation der Ergebnisse finden sich in der schriftlichen Ausarbeitung
