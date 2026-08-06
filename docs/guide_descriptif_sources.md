# Guide — `descriptif_sources.yaml`

Ce guide explique **comment lire et écrire** `docs/descriptif_sources.yaml`, le fichier qui décrit
le **format brut** des fichiers sources réels (OECI, `canceroBR`, `canceroAPHP`). Il complète le
contrat de données (`contrat_donnees_pivot.md`), qui décrit lui le **format long produit**.

---

## 1. À quoi sert ce fichier — et à quoi il ne sert PAS

Le YAML décrit **uniquement la disposition physique** des fichiers Excel : où sont les en-têtes,
à quelle position sont les colonnes de dimensions, quels libellés attendre. Il répond à la question
« **où** est quoi dans le fichier brut ? ».

Il ne décrit **pas** comment fabriquer le format long. La correspondance « colonne brute →
variable du contrat » (`Nb de patients` → `nb_patients`, bloc `MEDECINE` → `delai_traitement_medical_median`…)
vit **dans le code** (`chargeur_long.py`), pas dans le YAML.

> **Le modèle mental en une phrase :**
> le **YAML** dit *où* sont les choses et *ce que veulent dire les libellés* ;
> le **code** décide *comment* les transformer en format long.

Conséquence pratique : quand un format réel change (une colonne se déplace, un onglet est renommé),
on modifie **le YAML**. Quand c'est la logique métier qui change (une nouvelle variable, une règle
d'agrégation), on modifie **le code**.

---

## 2. Anatomie du fichier

```yaml
modalites_attendues:        # référentiels globaux (contrôle de dérive)
  ghu_codes: [...]
  type_etab: [...]
  ...

sources:                    # une entrée par source de données
  oeci: { ... }
  regional: { ... }
  regional_aphp: { ... }
```

### 2.1 Une source

```yaml
regional_aphp:
  source: BN                       # la source du contrat émise pour ces lignes
  fichiers:                        # motifs glob pour retrouver les fichiers
    patients: "canceroAPHP_*_Pat_*.xlsx"
    sejours:  "canceroAPHP_*_Sej_*.xlsx"
  onglet_lu: "Total"               # onglet Excel lu (les onglets d'âge sont différés)
  onglets_age_differes: ["Age < 18 ans", "Age >= 18 ans"]
  coercition: { ... }              # règles de nettoyage des nombres (format FR)
  portee_retenue: "AP-HP"          # (canceroAPHP) portée conservée ; GH/GHU/Hop ignorés
  feuilles:                        # une entrée par feuille logique
    total_patients: { ... }
    total_sejours:  { ... }
  modalites_attendues: { ... }     # modalités propres à la source
```

| Champ | Rôle |
|---|---|
| `source` | La valeur de la colonne `source` du format long (`BN`, `DIM APHP`, `EDS APHP`). |
| `fichiers` | Motifs glob pour localiser les fichiers réels dans `data/`. |
| `onglet_lu` | Nom de l'onglet Excel effectivement lu. |
| `onglets_age_differes` | Onglets d'âge présents mais **pas encore exploités** (chantier différé). |
| `coercition` | Comment nettoyer les nombres bruts (voir §4). |
| `portee_retenue` | *(canceroAPHP)* la portée du `Niveau` à conserver ; les autres sont ignorées. |
| `feuilles` | Le cœur : la description de chaque feuille (voir §3). |
| `modalites_attendues` | Valeurs attendues pour la détection de dérive. |

### 2.2 Une feuille

```yaml
total_patients:
  fichier: patients               # renvoie vers fichiers.patients
  nom: "Total"                    # nom de l'onglet
  lignes_entete: 1                # nombre de lignes d'en-tête
  premiere_ligne_donnees: 2       # 1re ligne de données (1-based, informatif)
  dimensions:                     # POSITION (1-based) de chaque dimension
    niveau: 1
    entite: 2
    appareil: 3
    organe: 4
    annee: 5
  granularites:                   # libellé Niveau → grain normalisé
    Total: total
    Appareil: appareil
    Organe: organe
  mesures:
    disposition: simple
    colonnes_utiles: ["Nb de patients", "Nouveaux patients"]
```

| Champ | Rôle |
|---|---|
| `nom` | Nom exact de l'onglet Excel. |
| `lignes_entete` | Nombre de lignes d'en-tête (1 le plus souvent ; 2 pour les feuilles séjours et Délais PEC). |
| `premiere_ligne_donnees` | 1re ligne de données (1-based). Surtout informatif : le code lit après l'en-tête. |
| `dimensions` | **Position (1-based)** de chaque colonne de dimension. `niveau: 1` = 1re colonne. |
| `granularites` | Traduit le libellé de grain lu dans `Niveau` vers le grain interne `total`/`appareil`/`organe`. |
| `niveau` | *(OECI, régional)* comment reconnaître le niveau : soit une **map** de libellés, soit des **mots-clés**. |
| `ghu_forme` | *(OECI)* `court` ou `long` selon la façon dont les GHU sont écrits sur cette feuille. |
| `mesures` | Comment lire les colonnes de mesures (voir §5). |

> **Attention aux positions** : `dimensions` donne des **positions**, pas des noms. Si une colonne
> se déplace dans un nouvel export, c'est **ici** qu'il faut corriger le chiffre — sinon le code
> lira la mauvaise colonne (et, souvent, silencieusement).

---

## 3. LE point clé : d'où vient le grain « TOTAL » ?

C'est la confusion la plus fréquente, alors elle a sa section.

Dans les fichiers bruts, les lignes agrégées portent des libellés comme **`Total Appareil`** et
**`Total Organe`** dans les colonnes appareil/organe. On pourrait croire qu'il faut déclarer ces
libellés dans le YAML. **Ce n'est pas le cas.**

Le grain est déterminé par la colonne **`Niveau`**, via `granularites`. Le code lit le `Niveau`
(`AP-HP-Total`, `AP-HP-Appareil`, `AP-HP-Organe` pour `canceroAPHP` ; `Total`/`Appareil`/`Organe`
pour `canceroBR`), en déduit le grain, **puis pose lui-même les sentinelles** `appareil = "TOTAL"`
et `organe = "TOTAL"` en fonction du grain :

| Grain (déduit du `Niveau`) | `appareil` produit | `organe` produit |
|---|---|---|
| `total` | `"TOTAL"` (sentinelle) | `"TOTAL"` (sentinelle) |
| `appareil` | valeur lue dans la colonne | `"TOTAL"` (sentinelle) |
| `organe` | valeur lue dans la colonne | valeur lue dans la colonne |

Autrement dit, pour une ligne de grain `total`, le code **écrase** ce que contiennent les colonnes
appareil/organe (`Total Appareil` / `Total Organe`) par le sentinelle `"TOTAL"`. Les libellés
`Total Appareil` / `Total Organe` **n'ont donc pas à figurer dans le YAML** : ils ne sont jamais
lus comme valeurs, ils sont remplacés.

Extrait de code correspondant (`chargeur_long._lire_feuille_aphp`) :

```python
gran = gran_brut.map(grans)                              # Niveau → total / appareil / organe
app  = appareil.where(gran != "total", SENTINELLE)       # total → appareil = TOTAL
org  = organe.where(gran == "organe", SENTINELLE)        # total/appareil → organe = TOTAL
```

> **À retenir :** le grain vient du **`Niveau`**, pas des colonnes appareil/organe. Ces colonnes ne
> servent qu'à **nommer** l'appareil/l'organe quand le grain est fin. Aux grains agrégés, elles sont
> ignorées au profit du sentinelle `TOTAL`.

---

## 4. La coercition (nettoyage des nombres)

```yaml
coercition:
  milliers: [" ", " "]        # séparateurs de milliers retirés (espace normal + insécable)
  decimale: ","                # virgule décimale → point
  pourcent: "%"                # signe % retiré
  masque: ["ns", "< 5", "-", "n.d.", "nd"]   # valeurs → NaN (non significatif, secret statistique…)
```

Le code (`_coercer_valeur`) applique ces règles pour transformer une cellule brute en `float`
(ou `NaN` si vide/masquée). Le format français réel mélange espaces normaux **et insécables**
comme séparateurs de milliers — d'où les deux entrées dans `milliers`.

---

## 5. Les trois dispositions de mesures

Le champ `mesures.disposition` indique comment sont rangées les colonnes de mesures :

### `simple`
Une colonne = une mesure. On liste les colonnes utiles par leur nom.
```yaml
mesures:
  disposition: simple
  colonnes_utiles: ["Nb de patients", "Nouveaux patients"]
```
Le mapping « colonne → variable » est fait **en code** (ex. `MAP_BN_PATIENT`).

### `blocs` (délais)
Les mesures sont organisées en **blocs** repérés par un libellé (feuille « Délais PEC »).
```yaml
mesures:
  disposition: blocs
  mapping_blocs:
    TOTAL: ...
    CHIRURGIE: ...
    MEDECINE: ...
    RADIOTHERAPIE: ...
```
Chaque bloc → une variable (le mapping vers `delai_*_median` est en code ; `MEDECINE` →
`delai_traitement_medical_median`). Les coquilles source (`RAFIOTHERAPIE`) sont tolérées par
mots-clés côté code.

### `plan_survie`
La feuille « Survie globale » croise **population × horizon × stade** (Tous/Nouveaux × 1 an/5 ans ×
I-III/IV). La structure est décrite comme un plan, et le code résout chaque axe pour produire
`survie_1an` / `survie_5ans` / `nb_patients_stade` avec les dimensions `population` et `stade`.

---

## 6. Exemple travaillé : d'une ligne brute au format long

Fichier `canceroAPHP` (Pat), une ligne au grain **appareil** :

| Niveau | Hopital-GH | Appareil patient | Organe patient | Année | Nb de patients | Nouveaux patients |
|---|---|---|---|---|---|---|
| `AP-HP-Appareil` | AP-HP | `APPAREIL DIGESTIF` | `Total Organe` | 2024 | 12 500 | 4 200 |

Traitement :

1. **Portée** : `_portee_granularite("AP-HP-Appareil")` → portée `AP-HP` (retenue), grain `Appareil`.
2. **Grain** : `granularites["Appareil"]` → `appareil`.
3. **Sentinelles** : grain `appareil` → `appareil = "APPAREIL DIGESTIF"` (lu), `organe = "TOTAL"`
   (le `Total Organe` de la colonne est écrasé).
4. **Mesures** : `Nb de patients` → `nb_patients`/`tous` = 12500 ; `Nouveaux patients` →
   `nb_patients`/`nouveaux` = 4200 (coercition : espaces retirés).
5. **Émission** (2 lignes longues) :

| annee | source | niveau | entite | appareil | organe | age | stade | population | variable | valeur |
|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | BN | aphp | AP-HP | APPAREIL DIGESTIF | TOTAL | tous | — | tous | nb_patients | 12500 |
| 2024 | BN | aphp | AP-HP | APPAREIL DIGESTIF | TOTAL | tous | — | nouveaux | nb_patients | 4200 |

---

## 7. Pièges & FAQ

- **« Il manque `Total Appareil` / `Total Organe` dans le YAML ? »** Non — le grain vient du `Niveau`,
  et les sentinelles `TOTAL` sont posées en code (cf. §3). Ces libellés ne sont jamais lus comme valeurs.
- **Une section régionale est vide en réel.** Souvent un libellé qui ne matche pas : mojibake
  (`?IL` pour `ŒIL`), espace parasite, casse. Le mapping `_APPAREIL_MAP` / la coercition absorbent
  les cas connus ; un libellé nouveau produit un **vide silencieux** — à repérer via l'inspection
  (notebook 06) plutôt que par le YAML seul.
- **Positions décalées.** Si un export ajoute/retire une colonne, les `dimensions` (positions) doivent
  être mises à jour, sinon le code lit la mauvaise colonne.
- **Feuille optionnelle absente** (`onglets_age_differes`, `Effectifs recherche`) : tolérée, signalée,
  jamais bloquante.
- **Le YAML décrit le brut, pas le produit.** Pour comprendre le format long *produit*, voir
  `contrat_donnees_pivot.md`.
