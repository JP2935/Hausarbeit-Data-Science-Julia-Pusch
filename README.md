# Hausarbeit Data Science and Text Mining
# Analyse von BGH-Urteilen und EuGH-Urteilen zu Corona

Dieses Repository enthält den vollständigen Programmcode zur computergestützten Textanalyse, die der  Hausarbeit von Julia Pusch zugrunde liegt. Ziel der Analyse ist die Identifikation thematischer Schwerpunkte und deren zeitliche Entwicklung in der höchstrichterlichen Rechtsprechung zur COVID-19-Pandemie (Zeitraum 2020-2025).

## Repository-Struktur
03_LDA_Modellierung.ipynb: Vorverarbeitung der Texte (Preprocessing), linguistische Normalisierung und initiale Themenmodellierung (LDA).

04_NMF_Analyse.ipynb: Optimierte Themenmodellierung mittels NMF, Evaluation (Coherence Score) und finale Visualisierung der thematischen Evolution.

/data: (Hinweis: Die Rohdaten der Urteile sind aus datenschutzrechtlichen Gründen nicht Teil dieses öffentlichen Repositories).

## Technische Dokumentation 
Die Analyse wurde in Jupyter Notebooks implementiert, um den Prozess interaktiv und wissenschaftlich nachvollziehbar zu gestalten.

Linguistische Pipeline: Verwendung von spaCy für POS-Tagging (Nomen/Eigennamen) und Lemmatisierung.

Vektorisierung: TF-IDF-Gewichtung mit gerichts-spezifischer Optimierung der max_df-Parameter zur Noise-Reduktion.

Reproduzierbarkeit: Alle Parameter (Alpha/Eta-Werte, Iterationen, Keyword-Blacklists) sind innerhalb der Notebooks dokumentiert.

## Bezug zur Hausarbeit 
Dieses Repository ergänzt die schriftliche Ausarbeitung. Die methodischen Details, die Implementierung der Scoring-Logik sowie die juristische Interpretation der computerlinguistischen Ergebnisse sind in Kapitel 4 (Methodik) und Kapitel 5 (Ergebnisse) der Hausarbeit detailliert ausgeführt.

## Autorin
Julia Pusch | Universität Regensburg | 6. Semester LL.B. Digital Law
