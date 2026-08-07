---
name: database-diagram
description: Use whenever Django models or the database schema are modified.
---

# Database Diagram

The project database diagram is generated automatically from the Django models.

Whenever a Django model or database schema changes, regenerate the diagram by running:

```bash
python manage.py generate_diagram