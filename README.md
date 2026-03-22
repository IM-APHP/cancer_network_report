# Rapport d'activité cancérologie — AP-HP

> ## ⚠ DONNÉES FICTIVES
> **L'ensemble des données présentées dans ce rapport sont entièrement simulées à titre illustratif.**
> Elles ont été générées aléatoirement pour démontrer le fonctionnement de l'outil et ne reflètent
> en aucun cas la réalité clinique ou statistique de l'AP-HP ou de ses groupes hospitaliers.
> **Ces chiffres ne doivent pas être utilisés à des fins médicales, administratives ou décisionnelles.**

---

Tableau de bord interactif d'activité cancérologique pour l'AP-HP, conforme aux indicateurs
de certification [OECI](https://www.oeci.eu/) (Organisation of European Cancer Institutes).

**Démo en ligne (données fictives)** : https://im-aphp.github.io/cancer_network_report/

## Contenu

Le rapport couvre **2019–2023** pour l'ensemble de l'AP-HP et ses 6 groupes hospitaliers universitaires
(GHU Centre, GHU Mondor, GHU Nord, GHU PSSD, GHU PSL, GHU SUN), décliné selon le référentiel
INCA (14 appareils, 56 organes, 646 codes CIM-10).

### Indicateurs OECI disponibles

| Indicateur | Description |
|---|---|
| Patients totaux | Nombre de patients pris en charge par année |
| Nouveaux patients | Patients identifiés pour la première fois dans l'année |
| Séjours chirurgie | Séjours avec acte chirurgical (3e lettre GHM = C) |
| Séjours chimiothérapie | Séjours avec diagnostic Z511 |
| Séjours radiothérapie | Séjours avec diagnostic Z510 |
| Soins palliatifs | Séjours avec diagnostic Z515 |
| Survie par stade | Survie à 1 an et 5 ans par stade (I → IV) |
| Délais de PEC | Délai médian (jours) entre 1re consultation et 1er traitement |

### Structure des rapports générés

| Type de rapport | Nombre | Description |
|---|---|---|
| Index | 1 | Page d'accueil avec navigation |
| Global AP-HP | 1 | Vue d'ensemble toutes pathologies |
| Par GHU | 6 | Un rapport par groupe hospitalier |
| Par appareil (AP-HP) | 14 | Un rapport par appareil pathologique |
| Par appareil × GHU | 84 | Vue GHU pour chaque appareil |
| Par organe (AP-HP) | ~53 | Un rapport par organe |
| Par organe × GHU | ~318 | Vue GHU pour chaque organe |
| **Total** | **~477** | |

## Installation

```bash
git clone https://github.com/<votre-organisation>/<nom-du-repo>.git
cd <nom-du-repo>
pip install -r requirements.txt
```

## Utilisation

### Générer tous les rapports

```bash
python run_reports.py
```

Les fichiers HTML sont générés dans `output/`. Ouvrez `output/index.html` dans votre navigateur.

### Options disponibles

```bash
# Données uniquement (sans générer les HTML)
python run_reports.py --data-only

# Rapports sans régénérer les données
python run_reports.py --no-data

# Un seul GHU
python run_reports.py --no-data --ghu "GHU Nord"

# Un seul appareil
python run_reports.py --no-data --appareil "SEIN"

# Un seul organe
python run_reports.py --no-data --appareil "APPAREIL DIGESTIF" --organe "Colon-Rectum-Anus"
```

### Utilisation des notebooks

Les notebooks Jupyter permettent une exploration interactive :

```bash
jupyter lab notebooks/
```

| Notebook | Description |
|---|---|
| `00_generate_data.ipynb` | Génération des données fictives |
| `01_rapport_global_aphp.ipynb` | Rapport global AP-HP |
| `02_rapport_ghu.ipynb` | Rapport par GHU (paramètre `GHU_NAME`) |
| `03_rapport_appareil.ipynb` | Rapport par appareil (paramètre `APPAREIL`) |
| `04_rapport_organe.ipynb` | Rapport par organe (paramètres `ORGANE`, `APPAREIL`, `ENTITY`) |

## Déploiement sur GitHub Pages

### Prérequis

1. Le dépôt doit être hébergé sur GitHub (public ou privé avec GitHub Pro/Team)
2. Activer GitHub Pages dans les paramètres du dépôt

### Activation de GitHub Pages

1. Aller dans **Settings → Pages**
2. Sous **Source**, sélectionner **GitHub Actions**
3. Pousser un commit sur la branche `main`

Le workflow `.github/workflows/deploy.yml` se déclenche automatiquement à chaque push sur `main`.
Il :
- installe Python et les dépendances
- génère tous les rapports (`python run_reports.py`)
- déploie le dossier `output/` sur GitHub Pages

L'URL du site sera :
```
https://im-aphp.github.io/cancer_network_report/
```

### Déclenchement manuel

Il est possible de déclencher le déploiement manuellement depuis **Actions → Générer et déployer les rapports → Run workflow**.

## Structure du projet

```
cancer_network_report/
├── .github/
│   └── workflows/
│       └── deploy.yml          # CI/CD GitHub Actions
├── src/
│   ├── generate_fake_data.py   # Génération des données simulées
│   ├── chart_utils.py          # Graphiques Plotly réutilisables
│   └── report_builder.py       # Assemblage des pages HTML
├── notebooks/
│   ├── 00_generate_data.ipynb
│   ├── 01_rapport_global_aphp.ipynb
│   ├── 02_rapport_ghu.ipynb
│   ├── 03_rapport_appareil.ipynb
│   └── 04_rapport_organe.ipynb
├── data/                       # CSV générés (gitignorés)
│   ├── aphp_data.csv
│   ├── regional_data.csv
│   └── survival_data.csv
├── docs/
│   └── codes_cancer_inca.xls   # Référentiel INCA (646 codes CIM-10)
├── output/                     # HTML générés (gitignorés sauf via CI)
├── run_reports.py              # Script maître
└── requirements.txt
```

## Sources et références

- [Indicateurs OECI](https://www.oeci.eu/Accreditation.aspx) — Organisation of European Cancer Institutes
- [Référentiel INCA](https://www.e-cancer.fr/) — Institut National du Cancer, liste CIM-10
- Données PMSI : entrepôt des données de santé AP-HP (EDS)
- Nomenclature CCAM — actes chirurgicaux et de radiothérapie

## Licence

Ce code est mis à disposition à titre illustratif. Les données sont entièrement fictives.
