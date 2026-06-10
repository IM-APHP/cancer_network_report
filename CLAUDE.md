# CLAUDE.md

Guide pour les agents Claude Code travaillant sur ce dépôt. À lire avant toute modification.
Réponds et commente le code **en français** (projet intégralement francophone : variables,
docstrings, libellés UI).

> ⚠ **Données fictives par défaut.** En mode standard les données sont générées aléatoirement
> (`np.random.seed(42)`) à titre illustratif. Ne jamais présenter ces chiffres comme
> cliniquement valides. `--real-data` bascule sur la source réelle et masque les bandeaux
> d'avertissement.

## Vue d'ensemble

Générateur de tableau de bord HTML statique d'activité cancérologie pour l'AP-HP, aligné sur
les indicateurs **OECI**. Produit ~500 pages HTML autonomes (Plotly embarqué) et les déploie
sur GitHub Pages via CI. Référentiel INCA (~14 appareils / ~56 organes). Couverture
temporelle : 2019–2023, déclinée AP-HP, 6 GHU, et — pour la survie — hôpitaux.

## Pipeline de données

Les données arrivent dans deux **formats pivot** Excel (= formats de production réels). Une
couche de chargement les normalise vers un **format interne** unique (3 CSV), consommé par les
constructeurs de rapports. Un changement de format de production ne doit impacter QUE les loaders.

```
templates/   gabarits Excel vides (format réel), VERSIONNÉS
   │   fill_fake_data.py  → série fictive *_fictif dans data/
   ▼
data/*.xlsx   fictif : *_fictif.xlsx   |   réel : noms sans _fictif
   │   pivot_loader.charger_oeci()  +  regional_loader.charger_regional()
   │   export_internes.exporter_csv()   (normalisation → format interne)
   ▼
data/aphp_data.csv · survival_data.csv · regional_data.csv
   │   report_builder.load_aphp / load_survival / load_regional
   ▼
output/*.html
```

Les fonctions `build_rapport_*` retournent un `Path` vers le HTML écrit. Pages **autonomes**
(CSS inline, Plotly via CDN), aucun asset partagé.

## Formats d'entrée (pivot)

### OECI interne — `indicateurs_oeci_<ANNÉE>_M<MM>.xlsx`
**1 fichier par année** ; l'année vient du **nom de fichier** (pas de colonne année).
Granularité Hôpital, agrégée via le champ `Niveau` vers GHU puis AP-HP. 7 onglets : `Origine géo`,
`Indicateurs patient`, `Indicateurs séjour`, `Indicateurs chirurgie`, `Survie globale`,
`Délais PEC`, `Effectifs recherche`. La taxonomie `Niveau` est **incohérente d'un onglet à
l'autre** (normalisée par `pivot_loader`). `Survie globale` (en-tête 4 lignes) et `Délais PEC`
(2 lignes) ont des **en-têtes fusionnés multi-lignes**.

### Régional externe — `canceroBR_<plage>_Pat_<date>.xlsx` et `…_Sej_<date>.xlsx`
Comparaison AP-HP vs établissements franciliens. **Multi-années dans un seul fichier**
(colonne `Année`) — convention opposée à l'OECI. Patients (`_Pat_`) + séjours (`_Sej_`),
3 onglets par tranche d'âge (`Total` = `<18` + `≥18` ; on lit `Total`). Granularité
établissement (`N° Finess`, `Statut`, `Hôpital AP-HP`).

## Format interne (3 CSV consommés par report_builder)

**`aphp_data.csv`** — clé `(annee, entite, appareil, organe)`,
`entite` ∈ {AP-HP, GHU Centre, GHU Mondor, GHU Nord, GHU PSSD, GHU PSL, GHU SUN}.
Mesures : `nb_patients`, `nb_nouveaux_patients`, `nb_sejours_chirurgie`,
`nb_sejours_chimiotherapie`, `nb_sejours_radiotherapie`, `nb_sejours_palliatifs`,
`delai_global_median`, `delai_chirurgie_median`, `delai_chimio_median`, `delai_radio_median`.

**`survival_data.csv`** — clé `(annee, entite, appareil, organe, stade, population)`,
`stade` ∈ {I-III, IV} · `population` ∈ {tous, nouveaux} · mesures `nb_patients_stade`,
`survie_1an`, `survie_5ans`. Niveaux : AP-HP + GHU + Hôpital.

**`regional_data.csv`** — clé `(annee, entite, appareil, organe)` où `entite` = type
d'établissement {AP-HP, Clinique, CH, CHU, PSPH, CLCC} ; mêmes mesures patients/séjours.

Sentinelle `"TOTAL"` sur `appareil`/`organe` pour les lignes roulées.

## Modules

| Fichier | Rôle |
|---|---|
| `templates/` *(versionné)* | Gabarits Excel vides au format réel (source de `fill_fake_data`). |
| `src/fill_fake_data.py` | Remplit les gabarits de `templates/` → série fictive `*_fictif` dans `data/` (seed 42, `ANNEES`, cohérence temporelle + creux COVID 2020). |
| `src/pivot_loader.py` | `charger_oeci(dossier, fictif)` → `(df_aphp, df_survie)`. Année ← nom de fichier. **Sélection par `Niveau`, jamais de ré-agrégation.** |
| `src/regional_loader.py` | `charger_regional(dossier, fictif)` → `df_regional`. Année ← colonne `Année`. **Agrégation par type d'établissement.** |
| `src/export_internes.py` | `exporter_csv(dossier_data, fictif)` : loaders → 3 CSV internes. Reconstruit la survie niveau appareil par agrégation pondérée (clé incluant `population`). |
| `src/referentiels.py` | Source unique : `GHU_LIST`, table GHU (nom complet → code), table `Statut` → type. |
| `src/chart_utils.py` | Figures Plotly + helpers (`slugify`, `fig_to_html`, `COLORS`, `get_color`). Ne lit aucun fichier. |
| `src/report_builder.py` | `HTML_TEMPLATE` + helpers (`fmt_nb`, …) + `build_rapport_*`. Lit les 3 CSV via `load_*`. |
| `run_reports.py` | Point d'entrée CLI. |

## Commandes

```bash
pip install -r requirements.txt

python run_reports.py                 # fictif : fill_fake_data → export_internes → build complet
python run_reports.py --data-only     # phase données seule (xlsx fictifs + 3 CSV)
python run_reports.py --no-data       # build seul, depuis les CSV existants
python run_reports.py --real-data     # source réelle + bandeaux masqués (orthogonal à --no-data)

# Itération rapide — cibler UN rapport :
python run_reports.py --no-data --ghu "GHU Nord"
python run_reports.py --no-data --appareil "SEIN"
python run_reports.py --no-data --appareil "APPAREIL DIGESTIF" --organe "Colon-Rectum-Anus"
```

**Pas de tests ni de linter configuré.** Valider une modification = build ciblé
(`--no-data --appareil ...`) puis ouverture du HTML dans `output/`. Préférer un build ciblé
au build complet.

## Correspondances (dans `referentiels.py`)

GHU (libellé réel OECI → code interne) : Centre-Université de Paris → GHU Centre ·
Nord-Université de Paris → GHU Nord · Henri-Mondor → GHU Mondor · Paris-Seine-Saint-Denis →
GHU PSSD · **Sorbonne Université → GHU SUN** · **Université Paris Saclay → GHU PSL**.

Régional (`Statut` → type) : `Hôpital AP-HP = Oui` → AP-HP · Privé → Clinique · CH → CH ·
CHR/U → CHU · PSPH/EBNL → PSPH · CLCC → CLCC.

## Conventions & pièges

- **OECI = sélection / régional = agrégation** (volontairement inverse). L'OECI contient déjà
  les lignes pré-agrégées à chaque `Niveau` : on SÉLECTIONNE et on mappe, on ne somme jamais
  (sinon double comptage). Le régional est par établissement : on SOMME par type.
- **Survie & `population`** : chaque combinaison existe en double (`tous`/`nouveaux`). **Filtrer
  une population AVANT toute somme/pondération** de `nb_patients_stade`, sinon double comptage.
- **Survie niveau appareil** (`organe="TOTAL"`) : absente des fichiers OECI, reconstruite par
  agrégation pondérée dans `export_internes`. Pour de **vraies** données : préférer les lignes
  source si le fichier les fournit (`Niveau = Appareil`), ne reconstruire que si absentes.
- **openpyxl** : ne pas combiner `read_only=True` avec un accès aléatoire `ws.cell(r,c)`
  (quadratique → blocage). Chargement normal ou itération séquentielle.
- **En-têtes multi-lignes** (`Survie globale`, `Délais PEC`) : parser par propagation des
  libellés de blocs fusionnés.
- **`HTML_TEMPLATE` en `str.format()`** : accolades littérales (CSS) doublées `{{ }}`.
- **Deux conventions temporelles** : OECI = 1 fichier/an (année dans le nom) ; régional =
  multi-années (colonne `Année`).
- **Année COVID 2020** : creux ~ -10 %, badge « Année COVID-19 » remplaçant le delta N-1.
- **Sentinelle `"TOTAL"`** : filtrer/inclure explicitement.
- Couleurs via `get_color()`/`COLORS` ; noms de fichiers via `slugify()` ; nombres via `fmt_nb()`.
- `data/` et `output/` **gitignorés** ; `templates/` **versionné** (auto-suffisance CI).

## CI / déploiement

`.github/workflows/deploy.yml` : push `main` (ou manuel) → Python 3.11 → `pip install` →
`python run_reports.py` → publication de `output/` sur GitHub Pages. Auto-suffisant grâce à
`templates/` versionné (le checkout neuf reconstruit toute la donnée fictive). Tester un build
complet localement avant de pousser.

## Points ouverts / à faire

- **Mode réel** : `--real-data` lit actuellement `templates/` (gabarit vide, faute de mieux).
  Quand de vraies données arriveront dans `data/` (noms sans `_fictif`), faire pointer le mode
  réel vers `data/`.
- **Référentiel** : le fictif dérive ~15 appareils (dont « Non décidable ») / ~58 organes des
  données, vs 14/56 INCA — le surplus est probablement la catégorie résiduelle PMSI. À confirmer
  sur un extrait réel.
- **Notebook** `notebooks/00_generate_data.ipynb` référence encore l'ancien `generate_fake_data`
  (illustratif, hors CI) — à rafraîchir.
