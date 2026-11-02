# Projet Log Analyser

Application Python d'analyse des journaux Linux `auth.log`. Elle lit les fichiers
ordinaires et `.gz`, extrait les événements SSH/PAM, affiche un tableau de bord
Matplotlib et peut enregistrer les résultats dans MySQL.

## 1. Installation

Avec Python 3.9 ou plus récent :

```bash
uv sync
# ou, sans uv :
python -m pip install -e .
```

## 2. Analyse locale

Le dossier `data` est analysé par défaut. Tous les fichiers de logs du dossier
sont lus, au lieu du seul dernier fichier :

```bash
python main.py data
```

## 3. Interface Matplotlib

```bash
python main.py data --gui
```

L'interface fournit des cartes KPI, les événements par type, les IP et utilisateurs
les plus fréquents, ainsi que le pays des IP publiques via Ipinfo. Pour augmenter
la limite gratuite d'Ipinfo, définir facultativement un token :

```bash
export IPINFO_TOKEN='votre_token_ipinfo'
```

Les IP privées (`127.0.0.1`, réseaux locaux, etc.) sont affichées comme
`Réseau local` et ne sont pas envoyées à Ipinfo.

## 4. Connexion MariaDB/MySQL avec PyMySQL

La connexion utilise cette configuration par défaut :

```bash
connection = pymysql.Connection(
    host="localhost",
    user="root",
    password="",
    port=3306,
    database="db_loganalyse",
)
```

Créer la base si elle n'existe pas :

```sql
CREATE DATABASE IF NOT EXISTS db_loganalyse
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Puis installer les dépendances et lancer l'import :

```bash
uv sync
uv run python main.py data --mysql
```

Le programme se connecte à MariaDB avec PyMySQL, crée la base si nécessaire, puis
crée la table `auth_events`, ses index et importe les événements avec insertion
idempotente (`INSERT IGNORE`). L'utilisateur MariaDB doit avoir les droits
`CREATE` sur la base et `INSERT` sur la table. Le schéma contient :
`event_time`, `host`, `process`, `pid`, `message`, `event_type`, `ip_address` et
`username`.

Pour analyser un fichier précis :

```bash
python main.py auth/auth.log
```

## Organisation

- `ingestion/raw.py` : lecture multi-fichiers et gzip.
- `process/extract_transforme.py` : parsing typé et classification.
- `storage/mysql.py` : schéma et persistance MySQL.
- `serving/dashboard.py` : dashboard natif Matplotlib avec statistiques et pays.
- `main.py` : point d'entrée CLI.