# order-backend

A small Flask + Ariadne GraphQL backend for the `order` project.

Quickstart

1. Create a virtual environment (recommended):

```powershell
python -m venv venv; .\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the server:

```powershell
python app.py
```

GraphQL playground will be available at http://127.0.0.1:5000/graphql

REST API
--------

In addition to GraphQL, a small REST API has been added for quick local testing (in-memory storage):

- GET /health - health check
- GET /orders - list orders
- GET /orders/<id> - get order by id
- POST /orders - create order (JSON: {"item": "name", "quantity": number})
- PUT /orders/<id> - update order
- DELETE /orders/<id> - delete order

Example (PowerShell):

```powershell
# create venv and activate
python -m venv venv; .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py

# in another terminal - health
curl http://127.0.0.1:5000/health

# create an order
curl -X POST http://127.0.0.1:5000/orders -H "Content-Type: application/json" -d '{"item":"apple","quantity":3}'

# list orders
curl http://127.0.0.1:5000/orders
```

Notes
-----

This REST store is intentionally ephemeral (kept in memory) for development. For production use, replace with a database-backed storage.
"# order-backend" 
