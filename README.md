# Projet Log Analyser

## Objectif

Ce projet analyse les journaux SSH présents dans `data/` afin de suivre les
tentatives de connexion. Le pipeline complémentaire réparti dans
`ingestion/`, `process/`, `storage/` et `serving/`
ne modifie pas le code existant. Il identifie les connexions réussies, les
mots de passe refusés et les utilisateurs invalides, puis prépare les données
pour PostgreSQL et le dashboard.

Les indicateurs demandés sont :

1. le nombre de tentatives échouées par pays ;
2. le nombre de tentatives réussies par utilisateur ;
3. la liste des tentatives échouées avec un utilisateur invalide.

## Contrainte de dépendances

Le code Python ajouté utilise uniquement la bibliothèque standard et
`matplotlib`. Aucun pilote Python PostgreSQL n'est installé : la connexion
utilise la commande système `psql`. `requests` et les fichiers existants ne
sont pas nécessaires pour ce pipeline complémentaire.

## Installation PostgreSQL

Créer une base et vérifier que `psql` est disponible :

```bash
createdb log_analyser
psql --version
```

Puis créer les tables et les vues :

```bash
psql --dbname log_analyser --file storage/schema.sql
```

Si le serveur est distant, définir les variables PostgreSQL habituelles
(`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`) et `POSTGRES_DB`.

## Chargement des logs

Le chargeur doit recevoir des dictionnaires produits par
`process.parser.parse_file`. Exemple à intégrer dans un nouveau script
d'exécution, sans changer `main.py` :

```python
from storage.load_postgres import load
from process.parser import parse_file

load(parse_file("data/auth.log.1"))
```

Répéter l'opération pour `auth.log.2`. Les fichiers `.gz` peuvent être lus
avec `gzip.open(..., mode="rt")` dans un script d'orchestration séparé.

## Pays des adresses IP

Un pays ne peut pas être déduit de façon fiable d'une adresse IP avec la seule
bibliothèque standard. Charger donc une correspondance autorisée dans
`ip_country`, par exemple :

```sql
INSERT INTO ip_country (source_ip, country)
VALUES ('45.156.87.204', 'XX')
ON CONFLICT (source_ip) DO UPDATE SET country = EXCLUDED.country;
```

Puis enrichir les événements avant le dashboard :

```sql
UPDATE auth_events AS event
SET country = country_map.country
FROM ip_country AS country_map
WHERE event.source_ip = country_map.source_ip
  AND event.country IS NULL;
```

Les IP sans correspondance apparaissent dans le dashboard sous `UNKNOWN`.

## Dashboard

Après le chargement et l'enrichissement :

```python
from serving.dashboard import create_dashboard
create_dashboard()
```

Les graphiques sont enregistrés dans `dashboard/` :

- `failed_attempts_by_country.png`
- `successful_attempts_by_user.png`
- `failed_invalid_users_by_user.png`

La troisième demande est consultable directement :

```bash
psql --dbname log_analyser --command \
  "SELECT * FROM failed_invalid_users;"
```

## Gestion des erreurs

Chaque module ajouté utilise `logging.getLogger(__name__)`. Pour activer le
fichier applicatif :

```python
from ingestion.logging_config import configure_logging
configure_logging()
```

Les erreurs de lecture, de parsing, de chargement PostgreSQL et de génération
des graphiques sont écrites dans `logs/application.log` et relancées afin de
ne pas masquer un échec. La table `module_errors` est prévue pour centraliser
les erreurs métier lors d'une future orchestration PostgreSQL.

## Architecture

```text
data/*.log(.gz)
       |
       v
process.parser
       |
       v
PostgreSQL: auth_events + ip_country
       |
       v
vues SQL
       |
       v
serving.dashboard / matplotlib
```

## Étapes de réalisation

1. Installer PostgreSQL et créer `log_analyser`.
2. Exécuter `storage/schema.sql`.
3. Ajouter le script d'orchestration séparé qui parcourt les fichiers de
   `data/`, y compris les archives gzip.
4. Charger les événements avec `storage.load_postgres`.
5. Alimenter `ip_country` avec une source de géolocalisation validée.
6. Exécuter la requête d'enrichissement des pays.
7. Générer les deux graphiques et consulter la vue des utilisateurs invalides.
8. Vérifier `logs/application.log` après chaque exécution.
