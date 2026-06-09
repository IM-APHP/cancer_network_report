# CLAUDE.md

Guide pour les agents Claude Code travaillant sur ce dépôt. À lire avant toute modification.
Réponds et commente le code **en français** (projet intégralement francophone : variables,
docstrings, libellés UI).

> ⚠ **Données fictives par défaut.** Les données sont générées aléatoirement
> (`np.random.seed(42)`) à titre illustratif. Ne jamais présenter ces chiffres comme
> cliniquement valides. Le mode « données réelles » (`--real-data`) masque seulement les
> bandeaux d'avertissement ; il ne change pas la source des données.

## Vue d'ensemble

Générateur de tableau de bord HTML statique d'activité cancérologie pour l'AP-HP, aligné sur
les indicateurs **OECI**. Produit ~477 pages HTML autonomes (Plotly embarqué) et les déploie
sur GitHub Pages via CI. Référentiel INCA : 14 appareils, 56 organes, 646 codes CIM-10.
Couverture temporelle : 2019–2023 (déclinée AP-HP, 6 GHU, et — pour la survie — hôpitaux).

## Architecture du pipeline

Les données réelles arrivent dans deux **formats pivot** Excel distincts. Une couche de
chargement les normalise vers un **format interne** unique, consommé par les constructeurs de
rapports. Tout changement de format de production ne doit impacter QUE la couche de chargement.

```
Format pivot OECI (1 xlsx/an)  ─┐
                                 ├─► couche de chargement ─► DataFrames internes ─► build_rapport_*
Format pivot régional (multi-an)─┘   (normalisation + agrégation)        (report_builder.py)
```

Les fonctions `build_rapport_*` retournent un `Path` vers le HTML écrit. Pages **autonomes**
(CSS inline, Plotly via CDN), aucun asset partagé.

## Formats d'entrée (pivot = format de production réel)

### 1. OECI interne — `indicateurs_oeci_<ANNÉE>_M<MM>.xlsx`

**1 fichier par année** ; l'année est portée par le **nom de fichier** (pas de colonne année).
Granularité = Hôpital (33 sites), agrégée via un champ `Niveau` vers GHU puis AP-HP.
7 onglets : `Origine géo`, `Indicateurs patient`, `Indicateurs séjour`,
`Indicateurs chirurgie`, `Survie globale`, `Délais PEC`, `Effectifs recherche`.

Subtilités à respecter impérativement :
- La taxonomie du champ `Niveau` est **incohérente d'un onglet à l'autre**
  (`Hop`/`Hop Total`/`Hopital Organe`/`Hôpital - Organe - Appareil`, `GH`/`GHU`/`GH Total`,
  `APHP Total`/`AP-HP`/`APHP Organe`…). La couche de chargement doit la normaliser.
- `Survie globale` et `Délais PEC` ont des **en-têtes sur plusieurs lignes** avec cellules
  fusionnées. Survie = {Tous patients | Nouveaux} × {survie 1 an | 5 ans} × {stade I-III |
  stade IV}. Délais = {TOTAL | CHIRURGIE | MÉDECINE | RADIOTHÉRAPIE} × {nb, % urgences,
  moyenne, médiane}.
- Libellés GHU = noms complets (voir table de correspondance plus bas).

### 2. Régional externe — `canceroBR_<plage>_Pat_<date>.xlsx` et `…_Sej_<date>.xlsx`

Comparaison AP-HP vs établissements franciliens. **Multi-années dans un seul fichier**
(colonne `Année`, 2017–2025) — convention temporelle opposée au fichier OECI.
2 fichiers (patients `_Pat_`, séjours `_Sej_`), **3 onglets par tranche d'âge** :
`Total`, `Age < 18 ans`, `Age >= 18 ans` (où `Total` = `<18` + `≥18`).
Granularité = établissement (`N° Finess`, `Raison Sociale`, `Statut`,
`Hôpital AP-HP` ∈ {Oui, Non}). Pour la comparaison, on regroupe par `Statut`
(+ AP-HP via `Hôpital AP-HP = Oui`).

## Format interne (consommé par report_builder)

**Indicateurs principaux** — clé `(annee, entite, appareil, organe)`
`entite` ∈ {AP-HP, GHU Centre, GHU Mondor, GHU Nord, GHU PSSD, GHU PSL, GHU SUN}.
Mesures : `nb_patients`, `nb_nouveaux_patients`, `nb_sejours_chirurgie`,
`nb_sejours_chimiotherapie`, `nb_sejours_radiotherapie`, `nb_sejours_palliatifs`,
`delai_global_median`, `delai_chirurgie_median`, `delai_chimio_median`, `delai_radio_median`.

**Survie** — clé `(annee, entite, appareil, organe, stade, population)`
`stade` ∈ {I-III, IV} · `population` ∈ {tous, nouveaux} ·
mesures : `nb_patients_stade`, `survie_1an`, `survie_5ans`. Niveaux conservés : AP-HP + GHU + Hôpital.

**Régional** — clé `(annee, entite, appareil, organe)` où `entite` = type d'établissement
{AP-HP, Clinique, CH, CHU, PSPH, CLCC} ; mêmes mesures patients/séjours que ci-dessus.

### Mapping pivot → interne

| Interne | Source |
|---|---|
| `nb_patients` / `nb_nouveaux_patients` | OECI · Indicateurs patient · `Nb patients` / `Nvx patients` |
| `nb_sejours_chirurgie` | OECI · Indicateurs séjour · `Séjours avec chirurgie` |
| `nb_sejours_chimiotherapie` | OECI · Indicateurs séjour · `Séjours avec DP chimio` |
| `nb_sejours_radiotherapie` | OECI · Indicateurs séjour · `Séjours avec DP radioth` |
| `nb_sejours_palliatifs` | OECI · Indicateurs séjour · `Séjours en soins palliatifs` |
| `delai_*_median` | OECI · Délais PEC · blocs TOTAL/CHIRURGIE/MÉDECINE/RADIOTHÉRAPIE · `Médiane délais` |
| survie | OECI · Survie globale |
| régional | `canceroBR` Pat + Sej, regroupés par `Statut` |

`MÉDECINE` (délais) ↔ chimiothérapie. Effectifs « chirurgie » = **séjours** (onglet séjour),
pas les patients de l'onglet patient.

## Correspondances à figer

GHU (libellé réel OECI → code interne) :

| Réel | Interne |
|---|---|
| APHP.Centre-Université de Paris | GHU Centre |
| APHP.Nord-Université de Paris | GHU Nord |
| APHP.Hôpitaux Universitaires Henri-Mondor | GHU Mondor |
| APHP.Hôpitaux Universitaires Paris-Seine-Saint-Denis | GHU PSSD |
| APHP.Sorbonne Université | GHU SUN |
| APHP.Université Paris Saclay | GHU PSL |

Régional (`Statut` → type interne) : `Hôpital AP-HP = Oui` → AP-HP · Privé → Clinique ·
CH → CH · CHR/U → CHU · PSPH/EBNL → PSPH · CLCC → CLCC.

## Modules

| Fichier | Rôle |
|---|---|
| `src/generate_fake_data.py` | Génère les données fictives **au format pivot** (xlsx OECI + régional). |
| `src/fill_fake_data.py` | Remplit les gabarits de format fournis avec des données fictives (copies `_fictif`). |
| `src/pivot_loader.py` *(à créer)* | Lit les xlsx OECI (année ← nom de fichier), normalise `Niveau`/GHU, joint les onglets → DataFrames internes. |
| `src/regional_loader.py` *(à créer)* | Lit les `canceroBR` Pat+Sej, regroupe par `Statut` → DataFrame régional interne. |
| `src/chart_utils.py` | Figures Plotly réutilisables + helpers (`slugify`, `fig_to_html`, palette `COLORS`). Ne lit aucun fichier. |
| `src/report_builder.py` | Assemble les pages HTML (`HTML_TEMPLATE` + helpers) et les `build_rapport_*`. Ne génère pas les données. |
| `run_reports.py` | Point d'entrée CLI : génération → chargement → build. |

## Commandes

```bash
pip install -r requirements.txt        # pip classique, pas de uv/poetry

python run_reports.py                  # tout : données + 477 HTML (lent)
python run_reports.py --data-only      # régénère uniquement les données
python run_reports.py --no-data        # rebuild HTML sans régénérer les données

# Itération rapide — cibler UN rapport :
python run_reports.py --no-data --ghu "GHU Nord"
python run_reports.py --no-data --appareil "SEIN"
python run_reports.py --no-data --appareil "APPAREIL DIGESTIF" --organe "Colon-Rectum-Anus"

python run_reports.py --real-data      # supprime les bandeaux « données fictives »
```

**Pas de tests ni de linter configuré.** Pour valider une modification : build ciblé
(`--no-data --appareil ...`) puis ouverture du HTML produit dans `output/`. Toujours préférer
un build ciblé au build complet pour vérifier rapidement.

## Conventions & pièges

- **Sentinelle `"TOTAL"`** : lignes agrégées avec `organe == "TOTAL"` et/ou `appareil == "TOTAL"`.
  Filtrer/inclure explicitement — un oubli double les comptages ou fait disparaître les totaux.
- **Deux conventions temporelles** : OECI = 1 fichier/an (année dans le nom) ; régional =
  multi-années dans un fichier (colonne `Année`). Les deux loaders les gèrent séparément.
- **Année COVID = 2020** : traitée à part (creux ~ -8 %, badge « Année COVID-19 » remplaçant
  le delta N-1 dans `kpi_card`).
- **`GHU_LIST` est dupliqué** dans `generate_fake_data.py`, `chart_utils.py` et
  `run_reports.py` : répercuter toute modification dans les trois (candidat à factorisation).
- **`HTML_TEMPLATE` utilise `str.format()`** : toute accolade littérale (CSS) doit être
  doublée `{{ }}`, sinon `KeyError`/`IndexError` au rendu.
- Couleurs via `get_color()` / dict `COLORS` ; noms de fichiers HTML via `slugify()` ;
  nombres via `fmt_nb()` (espace fine insécable).
- Préserver les en-têtes multi-lignes et cellules fusionnées des gabarits Excel (openpyxl).
- `data/` et `output/` sont **gitignorés** ; le HTML publié est reconstruit par la CI.
- Référentiel source : `docs/codes_cancer_inca.xls`.

## CI / déploiement

`.github/workflows/deploy.yml` : push `main` (ou manuel) → Python **3.11** → `pip install` →
`python run_reports.py` → publication de `output/` sur GitHub Pages. Tester un build complet
localement avant de pousser : la CI régénère et publie tout le site.

## État de migration (en cours)

Refonte de la couche données vers le format pivot. À faire, dans l'ordre :
1. `fill_fake_data.py` — remplir les gabarits fournis (preuve de format). ← étape courante
2. `generate_fake_data.py` — produire la **série annuelle** OECI (2019→2023) au format pivot.
3. `pivot_loader.py` + `regional_loader.py` — chargement et normalisation vers le format interne.
4. Refonte survie : schéma I-III / IV + dimension `population`, adaptation de
   `survival_by_stage` / `survival_evolution`.
5. Brancher `run_reports.py` sur les nouveaux loaders ; retirer l'ancienne génération CSV.
