# Contrat des données — format pivot **long**

> **Source de vérité unique.** Ce contrat définit le format pivot interne. Il est la référence commune pour :
> - le **loader réel** (qui mappe les fichiers sources *vers* ce format, piloté par le YAML) ;
> - le **générateur fictif** (Option B, qui *produit* ce format directement) ;
> - les **tests du notebook pré-prod** (qui valident ce format avant le build HTML).
>
> Statut : **v1 — stable.** Décisions actées (voir fin de document). La dimension `age` est **réservée** (`tous` partout pour l'instant) ; sa déclinaison `pédiatrie`/`adultes` est un **chantier différé**.

---

## 1. Fichier unique, format long

Un seul fichier, **`donnees.csv`** (format long / *tidy*). Une ligne = **une observation** (une valeur d'une variable pour une combinaison de dimensions).

**Clé d'unicité :**

```
(annee, source, niveau, entite, appareil, organe, age, stade, population, variable) → valeur
```

---

## 2. Colonnes

| Colonne | Type | Description |
|---|---|---|
| `annee` | entier | Année de l'indicateur |
| `source` | catégorie | Provenance des données — voir §3 |
| `niveau` | catégorie | Grain de l'entité — voir §4 |
| `entite` | texte | AP-HP / code GHU / nom d'hôpital / type d'établissement — voir §4 |
| `appareil` | texte | Nom d'appareil, ou sentinelle `TOTAL` |
| `organe` | texte | Nom d'organe, ou sentinelle `TOTAL` |
| `age` | catégorie | `tous` / `pédiatrie` / `adultes` — `tous` = agrégat tous âges |
| `stade` | catégorie | `I-III` / `IV` — **survie uniquement**, vide sinon |
| `population` | catégorie | `tous` / `nouveaux` — décline les patients (et la survie) ; `tous` par défaut |
| `variable` | catégorie | Nom de la mesure — vocabulaire contrôlé §5 |
| `valeur` | numérique | Valeur de la mesure (`NaN` si masquée ou absente) |

---

## 3. Modalités de `source`

| `source` | Système d'origine | Couvre | Niveaux produits |
|---|---|---|---|
| `BN` | Base nationale PMSI | Régional : patients + séjours | `aphp`, `type_etab` |
| `DIM APHP` | Base PMSI AP-HP (via le DIM) | OECI **hors survie** : patients, séjours, chirurgie, délais | `aphp`, `ghu`, `hopital` |
| `EDS APHP` | Entrepôt de données AP-HP | **Survie** | `aphp`, `ghu`, `hopital` |

**Important :** un même fichier OECI **mélange deux sources** — sa feuille « Survie globale » est `EDS APHP`, ses autres feuilles sont `DIM APHP`. C'est pour cela que la survie a ses propres libellés `Niveau` et ses formes GHU courtes : autre système, autre producteur, autre format. → `source` se déclare **par feuille** dans le YAML. Le fichier régional est entièrement `BN`.

---

## 4. Modalités de `niveau` et domaines d'`entite`

| `niveau` | `entite` (valeurs) |
|---|---|
| `aphp` | `AP-HP` |
| `ghu` | `GHU Centre`, `GHU Mondor`, `GHU Nord`, `GHU PSSD`, `GHU PSL`, `GHU SUN` |
| `hopital` | Noms d'hôpitaux (référentiel hôpitaux) |
| `type_etab` | `Clinique`, `CH`, `CHU`, `PSPH`, `CLCC` |

> `AP-HP` apparaît sous **les 3 sources** (effectifs internes DIM, survie EDS, agrégat régional BN), avec des valeurs potentiellement différentes. C'est `source` qui les distingue — d'où sa présence dans la clé d'unicité.

> **Formes GHU dans les sources** : `DIM APHP` et `BN` écrivent le GHU en forme longue (`APHP.Centre-Université de Paris`…), `EDS APHP` (survie) en forme courte (`AP-HP.Centre`…). Toutes sont résolues vers les 6 codes ci-dessus via `referentiels.GHU_NOM2CODE`.

### Dimension `age`

`age` ∈ `tous` / `pédiatrie` / `adultes`. Dimension transverse : `tous` = agrégat tous âges (toujours présent) ; `pédiatrie` / `adultes` = les déclinaisons, présentes là où la source les fournit (cf. point ouvert en fin de document).

---

## 5. Vocabulaire contrôlé des `variable`

| `variable` | `source` | Niveaux | `population` | `stade` | Unité | Plage |
|---|---|---|---|---|---|---|
| `nb_patients` | `BN`, `DIM APHP` | selon source | `tous`, `nouveaux` | — | effectif | ≥ 0 |
| `nb_sejours_chirurgie` | `BN`, `DIM APHP` | selon source | `tous` | — | effectif | ≥ 0 |
| `nb_sejours_chimiotherapie` | `BN`, `DIM APHP` | selon source | `tous` | — | effectif | ≥ 0 |
| `nb_sejours_radiotherapie` | `BN`, `DIM APHP` | selon source | `tous` | — | effectif | ≥ 0 |
| `nb_sejours_palliatifs` | `BN`, `DIM APHP` | selon source | `tous` | — | effectif | ≥ 0 |
| `delai_global_median` | `DIM APHP` | `aphp`, `ghu`, `hopital` | `tous` | — | jours | ≥ 0 |
| `delai_chirurgie_median` | `DIM APHP` | `aphp`, `ghu`, `hopital` | `tous` | — | jours | ≥ 0 |
| `delai_traitement_medical_median` | `DIM APHP` | `aphp`, `ghu`, `hopital` | `tous` | — | jours | ≥ 0 |
| `delai_radio_median` | `DIM APHP` | `aphp`, `ghu`, `hopital` | `tous` | — | jours | ≥ 0 |
| `nb_patients_stade` | `EDS APHP` | `aphp`, `ghu`, `hopital` | `tous`, `nouveaux` | `I-III`, `IV` | effectif | ≥ 0 |
| `survie_1an` | `EDS APHP` | `aphp`, `ghu`, `hopital` | `tous`, `nouveaux` | `I-III`, `IV` | % | 0–100 |
| `survie_5ans` | `EDS APHP` | `aphp`, `ghu`, `hopital` | `tous`, `nouveaux` | `I-III`, `IV` | % | 0–100 |

> **`nb_nouveaux_patients` n'existe plus comme variable** : les nouveaux patients = `nb_patients` avec `population = nouveaux` (unification décidée). La colonne `population` vaut `tous` partout ailleurs (séjours, délais).
>
> « selon source » : sous `BN`, niveaux `aphp` + `type_etab` ; sous `DIM APHP`, niveaux `aphp` + `ghu` + `hopital` (comptes par hôpital **inclus**).
>
> **`age`** : s'applique potentiellement à toute `variable`, `age = tous` par défaut (chantier différé pour `pédiatrie`/`adultes`).
>
> **Délais** : la feuille source « Délais PEC » expose 4 blocs — `TOTAL` → `delai_global_median`, `CHIRURGIE` → `delai_chirurgie_median`, `MEDECINE` → `delai_traitement_medical_median`, `RADIOTHERAPIE` → `delai_radio_median`. Le bloc **`MEDECINE`** mesure le délai du **parcours de traitement médical** (oncologie médicale : chimiothérapie, thérapies ciblées, immunothérapie…), plus large que la seule chimiothérapie — d'où le nom `delai_traitement_medical_median`. À distinguer de `nb_sejours_chimiotherapie`, qui compte bien des séjours de chimiothérapie au sens strict (« DP chimio »).

---

## 6. Sentinelle `TOTAL`

`appareil = "TOTAL"` et/ou `organe = "TOTAL"` désignent les agrégats :

- `appareil = TOTAL`, `organe = TOTAL` → toutes localisations confondues (grand total de l'entité) ;
- `appareil = <X>`, `organe = TOTAL` → total de l'appareil X ;
- `appareil = <X>`, `organe = <Y>` → niveau organe.

La reconstruction des niveaux agrégés (ex. survie niveau appareil par agrégation des organes) reste **en code** (logique procédurale), pas dans les données sources.

---

## 7. Vues larges (chargement)

Le **stockage** est long ; les consommateurs (`report_builder`, `chart_utils`) reçoivent du **large** via les `load_*`, qui **filtrent une tranche puis pivotent** `variable → colonnes`. Ils renvoient exactement les DataFrames larges actuels — pas de réécriture des consommateurs.

| Fonction | Filtre | Sortie large |
|---|---|---|
| `load_aphp` | `source = DIM APHP`, niveaux `aphp`,`ghu` | colonnes = comptes + délais ; **`nb_nouveaux_patients` reconstruit** depuis `population = nouveaux` |
| `load_survival` | `source = EDS APHP` | colonnes = `nb_patients_stade`, `survie_1an`, `survie_5ans` ; index inclut `stade`, `population` |
| `load_regional` | `source = BN` | colonnes = comptes (idem : `nb_nouveaux_patients` reconstruit) |
| `load_delais_hopitaux` | `source = DIM APHP`, niveau `hopital`, variables `delai_*` | colonnes = délais |

---

## 8. Règles transverses

- `stade` est **vide** hors survie ; rempli (obligatoire) pour `nb_patients_stade`, `survie_1an`, `survie_5ans`.
- `population` ∈ {`tous`, `nouveaux`} : décline `nb_patients` et la survie ; vaut **`tous`** partout ailleurs (séjours, délais). `nb_nouveaux_patients` n'est **pas** une variable — c'est `nb_patients` + `population = nouveaux`.
- `age` est **toujours rempli** (`tous` au minimum) ; `pédiatrie`/`adultes` uniquement là où la source décline par âge.
- `valeur = NaN` signifie **masquée** (petit effectif : `ns`, `< 5`, `-`…) ou **absente**. Pas de ligne émise pour une combinaison qui n'existe pas (pas de bourrage NaN).
- **Coercition numérique à la lecture** (format FR : séparateur de milliers espace/insécable, décimale virgule, `%` ; jetons masqués → `NaN`) : gérée par le loader, déclarée dans le YAML.
- **Détection de dérive** : toute valeur de `entite` / `ghu` / `niveau` hors des « modalités attendues » déclarées (YAML) déclenche un avertissement au chargement et un test ✗ dans le notebook pré-prod.

---

## Décisions actées

- **Fichier** : `donnees.csv`.
- **Codes GHU** : `GHU Centre`, `GHU Mondor`, `GHU Nord`, `GHU PSSD`, `GHU PSL`, `GHU SUN` (formes longues `DIM APHP`/`BN` et courtes `EDS APHP` résolues via `referentiels.GHU_NOM2CODE`).
- **Comptes par hôpital** : **inclus** (niveau `hopital` pour patients/séjours sous `DIM APHP`).
- **Régional (`BN`)** : **aucun délai** (patients + séjours uniquement).
- **`load_delais_hopitaux`** : remplace bien l'ancien `delais_hopitaux_data.csv`.
- **Dimension `age`** ajoutée : `tous` / `pédiatrie` / `adultes`.
- **« tous vs nouveaux » unifié en dimension `population`** : `nb_nouveaux_patients` supprimé → `nb_patients` + `population = nouveaux` ; `load_aphp`/`load_regional` reconstruisent la colonne `nb_nouveaux_patients` pour les consommateurs.

## Dimension `age` — état actuel et chantier différé

L'âge (`Adultes` / `Pédiatrie`) est porté par une **feuille des fichiers `BN`** (régional). Il **n'est pas exploité pour l'instant** : on travaille « tous patients » → **`age = tous` partout**.

À terme (**chantier séparé**) : exploiter cette feuille `BN`, étendre l'âge aux données **OECI**, et créer des **pages HTML dédiées** par tranche d'âge. La colonne `age` est dès maintenant dans le contrat pour ne pas avoir à refaire le format à ce moment-là.

**Pour l'implémentation actuelle** : le loader et le générateur émettent **`age = tous`** sur toutes les lignes ; le YAML n'a pas besoin de décrire la feuille âge tout de suite.
