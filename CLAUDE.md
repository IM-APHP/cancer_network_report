# CLAUDE.md

Guide pour les agents Claude Code travaillant sur ce dépôt. À lire avant toute modification.
Réponds et commente le code **en français** (projet intégralement francophone : variables,
docstrings, libellés UI).

> ⚠ **Données fictives par défaut.** En mode standard les données sont générées aléatoirement
> (`np.random.seed(42)`) à titre illustratif. Ne jamais présenter ces chiffres comme
> cliniquement valides. `--real-data` bascule sur la source réelle et masque les avertissements.

## Vue d'ensemble

Générateur de tableau de bord HTML statique d'activité cancérologie pour l'AP-HP, aligné sur
les indicateurs **OECI**. Produit ~500 pages HTML autonomes (Plotly embarqué) et les déploie
sur GitHub Pages via CI. Couverture 2019–2023, déclinée AP-HP, 6 GHU, hôpitaux (survie) et
établissements régionaux (comparaison).

## Pipeline de données

> **Vocabulaire.** Le **format pivot** = les **3 fichiers CSV internes** (format hub canonique
> consommé par les rapports). Les fichiers **Excel** sont les **formats source / de production**.
> Tout changement de format source ne doit impacter QUE les loaders.

```
templates/   gabarits Excel vides (format source), VERSIONNÉS
   │   fill_fake_data.py  → série fictive *_fictif dans data/
   ▼
data/*.xlsx   fictif : *_fictif.xlsx   |   réel : noms sans _fictif
   │   pivot_loader.charger_oeci()  +  regional_loader.charger_regional()
   │   export_internes.exporter_csv()    (normalisation → format PIVOT)
   ▼
data/aphp_data.csv · survival_data.csv · regional_data.csv   ← FORMAT PIVOT
   │   report_builder.load_aphp / load_survival / load_regional
   ▼
output/*.html   (index.html = page d'accueil = rapport global AP-HP)
```

## Formats source (Excel = production)

### OECI interne — `indicateurs_oeci_<ANNÉE>_M<MM>.xlsx`
**1 fichier par année** ; l'année vient du **nom de fichier**. Granularité Hôpital, agrégée via
le champ `Niveau` vers GHU puis AP-HP. 7 onglets (`Origine géo`, `Indicateurs patient`,
`Indicateurs séjour`, `Indicateurs chirurgie`, `Survie globale`, `Délais PEC`,
`Effectifs recherche`). Taxonomie `Niveau` **incohérente d'un onglet à l'autre** (normalisée par
`pivot_loader`). `Survie globale` (en-tête 4 lignes) et `Délais PEC` (2 lignes) ont des en-têtes
fusionnés multi-lignes.

### Régional externe — `canceroBR_<plage>_Pat_<date>.xlsx` et `…_Sej_<date>.xlsx`
**Multi-années dans un seul fichier** (colonne `Année`) — convention opposée à l'OECI.
Patients + séjours, 3 onglets par tranche d'âge (`Total` = `<18` + `≥18` ; on lit `Total`).
Granularité établissement (`N° Finess`, `Statut`, `Hôpital AP-HP`).

## Format pivot (3 CSV consommés par report_builder)

**`aphp_data.csv`** — clé `(annee, entite, appareil, organe)`,
`entite` ∈ {AP-HP + 6 GHU}. Mesures : `nb_patients`, `nb_nouveaux_patients`,
`nb_sejours_chirurgie`, `nb_sejours_chimiotherapie`, `nb_sejours_radiotherapie`,
`nb_sejours_palliatifs`, `delai_global_median`, `delai_chirurgie_median`, `delai_chimio_median`,
`delai_radio_median`.

**`survival_data.csv`** — clé `(annee, entite, appareil, organe, stade, population)`,
`stade` ∈ {I-III, IV} · `population` ∈ {tous, nouveaux} · `nb_patients_stade`, `survie_1an`,
`survie_5ans`. Niveaux : AP-HP + GHU + Hôpital.

**`regional_data.csv`** — clé `(annee, entite, appareil, organe)` où `entite` = type
d'établissement {AP-HP, Clinique, CH, CHU, PSPH, CLCC} ; mêmes mesures patients/séjours.

Sentinelle `"TOTAL"` sur `appareil`/`organe` pour les lignes roulées.

## Référentiels (`src/referentiels.py` — source unique)

`GHU_LIST` (ordre d'affichage) · `GHU_NOM2CODE` (nom complet OECI → code, dont **SUN =
Sorbonne**, **PSL = Paris Saclay**) · `STATUT2TYPE` (Privé→Clinique, CH→CH, CHR/U→CHU,
PSPH/EBNL→PSPH, CLCC→CLCC) · `APPAREIL_RESIDUEL = "Non décidable"`.

## Modules

| Fichier | Rôle |
|---|---|
| `templates/` *(versionné)* | Gabarits Excel vides au format source. |
| `src/fill_fake_data.py` | Gabarits → série fictive `*_fictif` (seed 42, `ANNEES = 2019…2023`, cohérence temporelle + creux COVID 2020). |
| `src/pivot_loader.py` | `charger_oeci()` → `(df_aphp, df_survie)` ; `mapping_hopital_ghu()`. Année ← nom de fichier. **Sélection par `Niveau`, jamais de ré-agrégation.** |
| `src/regional_loader.py` | `charger_regional()` → `df_regional`. Année ← colonne `Année`. **Agrégation par type d'établissement.** |
| `src/export_internes.py` | `exporter_csv()` : loaders → 3 CSV pivot. Reconstruit la survie niveau appareil par agrégation pondérée (clé incluant `population`). |
| `src/referentiels.py` | Correspondances figées (cf. ci-dessus). |
| `src/chart_utils.py` | Figures Plotly + helpers (`slugify`, `fig_to_html`, `COLORS`, `get_color`, `fmt_nb`, `donut_market_share`, `regional_comparison`, `survival_*`…). Ne lit aucun fichier. |
| `src/report_builder.py` | `HTML_TEMPLATE` + `build_rapport_global/ghu/appareil/organe/comparaison_hopitaux`. Lit les 3 CSV. |
| `run_reports.py` | Point d'entrée CLI. |
| `notebooks/` | 00 = génération (chaîne actuelle) ; 01-04 = reproduction par niveau (inline + IFrame). |

## Commandes

```bash
pip install -r requirements.txt        # notebooks : jupyter/nbformat/ipykernel (dév, à part)

python run_reports.py                  # fictif : fill_fake_data → export_internes → build complet
python run_reports.py --data-only      # phase données seule (xlsx + 3 CSV)
python run_reports.py --no-data        # build seul, depuis les CSV existants
python run_reports.py --real-data      # source réelle + avertissements masqués (orthogonal à --no-data)

# Builds CIBLÉS (itération rapide) :
python run_reports.py --no-data --ghu "GHU Nord"
python run_reports.py --no-data --appareil "SEIN"
python run_reports.py --no-data --appareil "APPAREIL DIGESTIF" --organe "Colon-Rectum-Anus"
python run_reports.py --no-data --comparaison-hopitaux
```

**Pas de tests ni de linter.** Valider = build ciblé puis ouverture du HTML dans `output/`.
Le build COMPLET (~500 pages) ne se fait qu'une fois en fin de chantier.

## Rapports & UI

- `build_rapport_global` écrit **`index.html`** : page d'accueil = rapport global AP-HP, intégrant
  la navigation (liste GHU, rapports par appareil/organe, comparaison inter-hôpitaux).
- Pages GHU, appareil (entity=AP-HP ou GHU), organe (entity=AP-HP ou GHU), et page de
  comparaison inter-hôpitaux (survie).
- **Barre de navigation par GHU uniforme** : bandeau « Naviguer » (AP-HP + chaque GHU, courant
  mis en évidence) présent sur toutes les pages.
- **Années dans les titres = DÉRIVÉES DES DONNÉES** (`last_year = int(df["annee"].max())`, plage
  min–max). Ne pas coder d'années en dur dans l'affichage. Seules `ANNEES`/`COVID` de
  `fill_fake_data` (génération) et le `2020` du creux COVID dans `chart_utils` (gardé par
  `if 2020 in years_in_data`) sont fixes.
- **Tableaux vs graphiques** : l'évolution par appareil/organe est un **tableau chiffré**
  (patients/séjours × années), pas une heatmap. Les tableaux « Survie et délais — par appareil »
  (AP-HP/GHU) sont conservés tels quels.
- **« Non décidable »** (`APPAREIL_RESIDUEL`) : exclu des affichages/agrégations, mais son rapport
  reste généré et accessible via un lien en fin de liste.

## Bandeau / footer « données fictives »

Piloté par `FAKE_DATA` (`report_builder`), basculé par `set_fake_data()` (que `--real-data`
met à `False`). `_render_page` injecte conditionnellement, selon `FAKE_DATA` :
badge « Données fictives — {période} » + bandeau jaune (`#FFF3CD`) + **`footer_note`**
(« Données simulées… » en fictif, « Indicateurs OECI » en réel). Les trois sont liés au même
drapeau : ne pas réintroduire de texte « simulé » statique.

## Notebooks

`00_generate_data` : chaîne actuelle (`fill_fake_data.main` → `export_internes.exporter_csv`),
aperçus AP-HP / régional (colonne `entite`) / survie (`population=='tous'`).
`01-04` : reproduisent chaque niveau **étape par étape** (mêmes appels `chart_utils`, figures
inline via `fig.show()`, tableaux via `IPython.display.HTML`), plus la page complète en IFrame.
Ces notebooks **dupliquent** la séquence de `build_rapport_*` : re-synchroniser si `report_builder`
évolue. Dépendances `jupyter`/`nbformat`/`ipykernel` (dév).

## Conventions & pièges

- **OECI = sélection / régional = agrégation** (volontairement inverse) : l'OECI contient déjà
  les lignes pré-agrégées par `Niveau` (on sélectionne, jamais on ne somme → sinon double
  comptage) ; le régional est par établissement (on somme par type).
- **Survie & `population`** : chaque combinaison existe en double (tous/nouveaux). **Filtrer une
  population AVANT toute somme/pondération** de `nb_patients_stade`.
- **Survie niveau appareil** : reconstruite par agrégation pondérée dans `export_internes`. Pour
  de **vraies** données : préférer les lignes source si le fichier les fournit (`Niveau = Appareil`).
- **openpyxl** : ne pas combiner `read_only=True` et accès aléatoire `ws.cell(r,c)` (quadratique).
- **En-têtes multi-lignes** (Survie, Délais) : parser par propagation des blocs fusionnés.
- **`HTML_TEMPLATE` en `str.format()`** : accolades CSS littérales doublées `{{ }}`.
- **Deux conventions temporelles** : OECI = 1 fichier/an (année dans le nom) ; régional =
  multi-années (colonne `Année`).
- **Sentinelle `"TOTAL"`** : filtrer/inclure explicitement.
- `data/` et `output/` **gitignorés** ; `templates/` **versionné** (auto-suffisance CI).

## CI / déploiement

`.github/workflows/deploy.yml` : push `main` → Python 3.11 → `pip install` →
`python run_reports.py` → publication de `output/` sur GitHub Pages. Auto-suffisant via
`templates/`. Tester un build complet localement avant de pousser.

## Points ouverts

- **Mode réel** : `--real-data` lit aujourd'hui `templates/` (gabarit vide, faute de mieux).
  Quand de vraies données arriveront dans `data/` (noms sans `_fictif`), rebrancher le mode réel
  sur `data/`.
- **Référentiel** : le fictif dérive ~15 appareils (dont « Non décidable ») / ~58 organes des
  données, vs 14/56 INCA — surplus probablement résiduel PMSI. À confirmer sur extrait réel.
- **Dépendances notebooks** (`jupyter`/`nbformat`/`ipykernel`) à déclarer (ex. `requirements-dev.txt`).
