=>> Log Analyser

Log Analyser est un  projet  qui étudie des journaux de connexions SSH .

Le pipeline lit les fichiers (auth.log), y compris les archives compressées, puis extrait les événements utiles.
Les connexions réussies, les mots de passe refusés et les utilisateurs invalides sont enregistrés dans PostgreSQL.
Les adresses IP sont ensuite associées à leur pays grâce à une API de géolocalisation.
Les données sont regroupées avec des vues SQL pour obtenir les statistiques par pays et par utilisateur.
Enfin, une dashboard Matplotlib présente les résultats sous forme de graphiques simples.
Le projet utilise principalement Python, (requests) pour l'API, (psql) pour PostgreSQL et (matplotlib) pour l'affichage.
