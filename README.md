# FURRA LUMI POS

A local web-based POS system for a bakery, built with a Python standard-library backend, SQLite, and a touch-friendly Albanian interface.

## Run Web Version

```powershell
python run.py
```

Open:

```text
http://127.0.0.1:8000
```

PIN access:

- `1` = Arkëtar
- `2` = Admin

The SQLite database is created automatically at `data/bakery_pos.db` on first run.

## Run Desktop Version

Install Node dependencies once:

```powershell
npm install
```

Start the Electron desktop app in development:

```powershell
npm start
```

For the desktop app, the SQLite database is stored in the Windows app data folder for `FURRA LUMI POS`, so client data stays on that computer.

## Build Windows Installer

Install PyInstaller once:

```powershell
python -m pip install pyinstaller
```

Create the Windows installer:

```powershell
npm run dist
```

The installer will be created in:

```text
release/
```

## GitHub Download For Client

The repository includes a GitHub Actions workflow at `.github/workflows/build-windows.yml`.

To create a downloadable installer from GitHub:

1. Push the code to GitHub.
2. Create a version tag, for example `v1.0.0`.
3. Push the tag.
4. GitHub Actions builds the Windows `.exe` installer automatically.
5. Open the GitHub Release and download `FURRA LUMI POS Setup ... .exe`.

Commands:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

At the client PC, download the `.exe` from GitHub Releases, run it, and the POS opens as a desktop application.

## Deploy Online Web Version

This project can also run online as a web application through Docker.

Build locally:

```powershell
docker build -t furra-lumi-pos .
```

Run locally through Docker:

```powershell
docker run --rm -p 8000:8000 -v furra-lumi-pos-data:/data furra-lumi-pos
```

Open:

```text
http://127.0.0.1:8000
```

For online hosting, use a Docker-capable host such as Render, Railway, Fly.io, or a VPS. Configure:

- Web service type: Docker
- Port: `8000`, or let the provider set `PORT`
- Persistent disk/volume mounted at `/data`
- Database path: `BAKERY_POS_DB=/data/bakery_pos.db`

Important: if the online host does not provide persistent storage, SQLite data can be lost after redeploys or restarts. For a real client installation, the desktop app is safer because the database stays on the client's PC.

Security note: do not expose the online admin panel publicly with simple demo PINs. Change authentication before using it as a public internet app.

## Features

- PIN login for cashier and admin roles.
- Cashier order table with product, quantity, unit price, and total.
- Quantity increase/decrease, delete selected item, clear order.
- Four seeded bakery categories: Bukë, Pastiçeri, Pica, Pije.
- 24 seeded products, 6 per category.
- Product search by name.
- Euro pricing and exact cent-based calculations.
- Payment calculator with total amount, amount received, change due, and insufficient-payment warning.
- Completed sales stored in SQLite with receipt number and line items.
- Receipt modal with print and TXT export.
- Admin product CRUD, price changes, category management.
- Daily sales report with revenue and transaction history.
- Responsive layout for desktop and tablet-style touch screens.

## Project Structure

```text
.
├── app/
│   ├── __init__.py
│   ├── database.py       # SQLite schema and seed data
│   ├── repositories.py   # Product, category, sale, report logic
│   └── server.py         # HTTP server, static files, JSON API
├── data/
│   └── bakery_pos.db     # Generated locally on first run
├── Dockerfile            # Online Docker deployment
├── electron/
│   └── main.js           # Electron desktop app launcher
├── static/
│   ├── index.html        # Login, cashier, admin screens
│   ├── styles.css        # Responsive touch POS styling
│   └── app.js            # Frontend state and API calls
├── run.py                # App entry point
├── package.json          # Electron build configuration
└── README.md
```

## API Summary

- `GET /api/categories`
- `POST /api/categories`
- `PUT /api/categories/{id}`
- `DELETE /api/categories/{id}`
- `GET /api/products`
- `POST /api/products`
- `PUT /api/products/{id}`
- `DELETE /api/products/{id}`
- `POST /api/sales`
- `GET /api/sales?date=YYYY-MM-DD`
- `GET /api/sales/{id}`
- `GET /api/reports/daily?date=YYYY-MM-DD`
- `GET /api/receipts/{id}.txt`
