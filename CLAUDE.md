# CLAUDE.md

Guide pour les agents Claude Code travaillant sur ce dépôt. À lire avant toute modification.
Réponds et commente le code **en français** (projet intégralement francophone : variables,
docstrings, libellés UI).

> ⚠ **Données fictives par défaut.** En mode standard les données sont générées aléatoirement
> (seed fixe) à titre illustratif, par `src/generateur_fictif.py`. Ne jamais présenter ces
> chiffres comme cliniquement valides. `--real-data` bascule sur la source réelle (ingestion
> des vrais fichiers de `data/`) et masque les bandeaux d'avertissement.

## Vue d'ensemble

Générateur de tableau de bord HTML statique d'activité cancérologie pour l'AP-HP, aligné sur
les indicateurs **OECI**. Produit ~520 pages HTML autonomes (Plotly embarqué) et les déploie
sur GitHub Pages via CI. Référentiel INCA (~14 appareils / ~56 organes). Couverture
temporelle **2022–2025** (bornes `ANNEE_MIN`/`ANNEE_MAX` dans `referentiels.py`), déclinée
AP-HP, 6 GHU, et hôpitaux.

## Pipeline de données

Le format de stockage **unique** est un CSV **long / tidy** : `data/donnees.csv`. Deux
**producteurs** l'alimentent (fictif ou réel) ; les **consommateurs** (report_builder /
chart_utils) restent inchangés et lisent des vues **larges** reconstruites à la volée.

```
            FICTIF                                RÉEL
 src/generateur_fictif.py            data/*.xlsx (OECI + canceroBR réels)
   (référentiels → long,                    │  src/chargeur_long.py
    aucun xlsx, seed fixe)                  │  (piloté par descriptif_sources.yaml,
            │                               │   mapping colonne→variable EN CODE)
            └──────────────┬────────────────┘
                           ▼
                   data/donnees.csv   ← FORMAT LONG canonique (le contrat)
                           │  report_builder.load_aphp / load_survival /
                           │  load_regional / load_delais_hopitaux
                           │  (filtrent + pivotent le long → large)
                           ▼
                      output/*.html
```

Les fonctions `build_rapport_*` retournent un `Path` vers le HTML écrit. Pages **autonomes**
(CSS inline, Plotly via CDN), aucun asset partagé. Un changement de format de production réel
ne doit impacter QUE `chargeur_long.py` + `descriptif_sources.yaml`.

## Documents de référence

- **`contrat_donnees_pivot.md`** — contrat canonique du format long : colonnes, clé d'unicité,
  vocabulaire des `variable`, domaines des dimensions. **Faire foi** en cas de doute.
- **`descriptif_sources.yaml`** — descripteur déclaratif du **format brut** des fichiers réels
  (par feuille : en-têtes, position des dimensions, taxonomie `Niveau`, forme GHU, coercition,
  disposition des mesures, modalités attendues). Décrit le brut **uniquement** ; le mapping
  brut → `variable` reste **en code** dans `chargeur_long.py`.

## Format long — `data/donnees.csv`

Clé d'unicité = toutes les dimensions :
`(annee, source, niveau, entite, appareil, organe, age, stade, population, variable)` → `valeur`.

- **`source`** ∈ `{BN, DIM APHP, EDS APHP}` (déclarée par feuille ; le fichier OECI mélange
  `DIM APHP` hors survie et `EDS APHP` pour la survie). `BN` = base nationale PMSI (régional).
- **`niveau`** ∈ `{aphp, ghu, hopital, type_etab}` ; `entite` = AP-HP / 6 codes GHU / nom
  d'hôpital / type d'établissement.
- **`population`** ∈ `{tous, nouveaux}` — dimension unifiée (`nb_nouveaux_patients` **n'existe
  plus** comme variable : c'est `nb_patients` avec `population = nouveaux`). `load_aphp` /
  `load_regional` reconstruisent la colonne `nb_nouveaux_patients` pour les consommateurs.
- **`stade`** ∈ `{I-III, IV}` — survie uniquement.
- **`age`** ∈ `{tous, pédiatrie, adultes}` — réservé, vaut `tous` partout (split = chantier différé).
- Sentinelle `"TOTAL"` sur `appareil`/`organe` pour les lignes roulées.

**Vocabulaire des `variable`** : `nb_patients` · `nb_sejours_{chirurgie,chimiotherapie,
radiotherapie,palliatifs}` · `delai_{global,chirurgie,traitement_medical,radio}_median`
(DIM APHP, niveaux aphp/ghu/hopital) · `nb_patients_stade` · `survie_1an` · `survie_5ans`
(EDS APHP, avec `stade` + `population`). Le régional (`BN`) n'a **pas** de délais.

> **Délais — `MEDECINE` = traitement médical.** La feuille « Délais PEC » expose 4 blocs :
> `TOTAL`→`delai_global_median`, `CHIRURGIE`→`delai_chirurgie_median`,
> `MEDECINE`→`delai_traitement_medical_median`, `RADIOTHERAPIE`→`delai_radio_median`.
> `MEDECINE` couvre le **parcours de traitement médical** (oncologie médicale : chimio,
> thérapies ciblées, immuno…), plus large que la seule chimiothérapie — d'où le nom
> `delai_traitement_medical_median`. À distinguer de `nb_sejours_chimiotherapie` (séjours de
> chimio au sens strict, « DP chimio »), inchangé.

## Formats d'entrée réels (bruts, décrits par le YAML)

### OECI interne — `indicateurs_oeci_<ANNÉE>_M<MM>.xlsx`
**1 fichier par année** ; l'année vient du **nom de fichier**. Granularité Hôpital, agrégée via
le champ `Niveau` vers GHU puis AP-HP. Onglets : `Indicateurs patient`, `Indicateurs séjour`,
`Survie globale`, `Délais PEC`… (certains onglets — `Effectifs recherche` — peuvent être
**absents** des extraits réels ; le loader tolère). La taxonomie `Niveau` est **incohérente
d'un onglet à l'autre** (normalisée par le YAML + code). `Survie globale` (en-tête 4 lignes,
ordre de dimensions différent, GHU en **forme courte**) et `Délais PEC` (2 lignes, **blocs**)
ont des **en-têtes fusionnés multi-lignes**. 32 hôpitaux sur le fichier réel.

### Régional externe — `canceroBR_<plage>_Pat_<date>.xlsx` et `…_Sej_<date>.xlsx`
Comparaison AP-HP vs établissements franciliens. **Multi-années dans un seul fichier**
(colonne `Année`) — convention opposée à l'OECI. Patients (`_Pat_`) + séjours (`_Sej_`),
onglets par tranche d'âge (`Total` / `Age < 18 ans` / `Age >= 18 ans` ; on lit `Total`).
Granularité établissement (`N° Finess`, `Statut`, `Hôpital AP-HP`).

## Modules

| Fichier | Rôle |
|---|---|
| `src/generateur_fictif.py` | **Producteur fictif (Option B)** : génère `data/donnees.csv` directement depuis les référentiels (aucun xlsx, seed fixe). Comptes agrégés hôpital→GHU→AP-HP, survie ordonnée, masquage réaliste des effectifs < 5 (~6 % → « — »). |
| `src/chargeur_long.py` | **Producteur réel** : moteur générique piloté par `descriptif_sources.yaml`. 3 dispositions de mesures (`simple` / `blocs` / `plan_survie`), résolution niveau + forme GHU + coercition FR, transforms procéduraux (filtre de période, reconstruction survie niveau appareil, sentinelles `TOTAL`), comptes niveau hôpital, `mapping_hopital_ghu` relocalisé, détection de dérive vs `modalites_attendues`. |
| `src/format_long.py` | Convertisseur bidirectionnel large ↔ long (`tables_vers_long`), utilisé par la bascule et les helpers internes. |
| `src/export_internes.py` | Réduit à : charger (réel) → écrire `data/donnees.csv`. |
| `src/referentiels.py` | Source unique : `GHU_LIST`, `GHU_NOM2CODE`, `STATUT2TYPE`, bornes `ANNEE_MIN`/`ANNEE_MAX`, exclusions inter-hôpitaux. |
| `src/chart_utils.py` | Figures Plotly + helpers (`slugify`, `fig_to_html`, `COLORS`, `get_color`). Ne lit aucun fichier. |
| `src/report_builder.py` | `HTML_TEMPLATE` + helpers + `build_rapport_*`. Lit `donnees.csv` via `load_aphp` / `load_survival` / `load_regional` / `load_delais_hopitaux` (filtrent + pivotent le long). |
| `run_reports.py` | Point d'entrée CLI. |
| `notebooks/05_controle_preprod.ipynb` | **Garde-fou pré-prod** mode-agnostique : couverture (source × niveau × variable) + tests ✓/✗ critiques vs informatifs. À exécuter avant un build de prod. |

## Commandes

```bash
pip install -r requirements.txt

python run_reports.py                 # fictif : generateur_fictif → donnees.csv → build complet
python run_reports.py --no-data       # build seul, depuis donnees.csv existant
python run_reports.py --real-data     # source réelle (chargeur_long) + bandeaux masqués

# Itération rapide — cibler UN rapport :
python run_reports.py --no-data --ghu "GHU Nord"
python run_reports.py --no-data --appareil "SEIN"
python run_reports.py --no-data --appareil "APPAREIL DIGESTIF" --organe "Colon-Rectum-Anus"
```

**Garde-fou avant un build réel** : exécuter `notebooks/05_controle_preprod.ipynb`
(`jupyter nbconvert --execute`) — tous les tests **critiques** doivent être verts.
Valider une modif = build ciblé (`--no-data --appareil ...`) puis ouverture du HTML dans `output/`.

## Correspondances (dans `referentiels.py`)

GHU (libellé réel OECI → code interne) : Centre-Université de Paris → GHU Centre ·
Nord-Université de Paris → GHU Nord · Henri-Mondor → GHU Mondor · Paris-Seine-Saint-Denis →
GHU PSSD · **Sorbonne Université → GHU SUN** · **Université Paris Saclay → GHU PSL**
(+ formes **courtes** « AP-HP.Centre » etc. pour la feuille `Survie globale`).

Régional (`Statut` → type) : `Hôpital AP-HP = Oui` → AP-HP · Privé → Clinique · CH → CH ·
CHR/U → CHU · PSPH/EBNL → PSPH · CLCC → CLCC.

## Conventions & pièges

- **OECI = sélection / régional = agrégation** (volontairement inverse). L'OECI contient déjà
  les lignes pré-agrégées à chaque `Niveau` : on SÉLECTIONNE et on mappe, on ne somme jamais
  (sinon double comptage). Le régional est par établissement : on SOMME par type.
- **Survie & `population`** : chaque combinaison existe en double (`tous`/`nouveaux`). **Filtrer
  une population AVANT toute somme/pondération** de `nb_patients_stade`, sinon double comptage.
- **Survie niveau appareil** (`organe="TOTAL"`) : reconstruite par agrégation pondérée
  (NaN-safe) dans `chargeur_long`. Pour de **vraies** données : préférer les lignes source si le
  fichier les fournit (`Niveau = Appareil`), ne reconstruire que si absentes.
- **Délais 0 ≠ délai nul** : les cases OECI non renseignées (et le 0-fill des merges) sont
  neutralisées en **NaN** côté consommateur pour ne pas polluer les moyennes reconstruites.
- **openpyxl** : ne pas combiner `read_only=True` avec un accès aléatoire `ws.cell(r,c)`
  (quadratique → blocage). Chargement normal ou itération séquentielle.
- **En-têtes multi-lignes** (`Survie globale`, `Délais PEC`) : parser par propagation des
  libellés de blocs fusionnés (cf. dispositions `blocs` / `plan_survie` du YAML).
- **Coquilles source tolérées** : ex. bloc délais « RAFIOTHERAPIE » — résolution par mots-clés.
- **`HTML_TEMPLATE` en `str.format()`** : accolades littérales (CSS) doublées `{{ }}`.
- **Deux conventions temporelles** : OECI = 1 fichier/an (année dans le nom) ; régional =
  multi-années (colonne `Année`).
- **Sentinelle `"TOTAL"`** : filtrer/inclure explicitement.
- **Inter-hôpitaux** : mapping hôpital→GHU dérivé nativement de la source (préservé par
  `chargeur_long`) ; exclusions SSR/gériatrie via `referentiels` (garde-fou sur entrées non matchées).
- Couleurs via `get_color()`/`COLORS` ; noms de fichiers via `slugify()` ; nombres via `fmt_nb()`.
- `data/` (dont `donnees.csv`) et `output/` **gitignorés**. Le fictif est **auto-suffisant**
  (générateur → données depuis le code, plus aucun gabarit xlsx versionné nécessaire).

## CI / déploiement

`.github/workflows/deploy.yml` : push `main` (ou manuel) → `pip install` → `python run_reports.py`
→ publication de `output/` sur GitHub Pages. Auto-suffisant : le générateur fictif reconstruit
toute la donnée depuis le code (aucun fichier de données committé). Tester un build complet
localement avant de pousser.

## Points ouverts / à faire

- **Validation régionale réelle** : `chargeur_long` (disposition régionale `BN`, 8 dimensions
  par position, `STATUT2TYPE`) n'a pas encore été exercé sur de **vrais** `canceroBR` (absents de
  `data/`). Dès qu'ils arrivent : relancer la comparaison loader-vs-migration ou un `--real-data`
  complet pour confirmer.
- **`age`** (`pédiatrie`/`adultes`) : chantier différé — les onglets âge régionaux
  (`Age < 18 ans` / `Age >= 18 ans`) existent mais ne sont pas encore exploités (`age = tous`).
- **Référentiel hôpitaux** : pas de référentiel canonique unique dans les fichiers AP-HP
  (3 formes de nommage GHU selon les feuilles) — réconcilié au chargement.
