# Hotel Saiprasad Management System

A complete **offline** Hotel Management Web Application built with:
- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Storage**: Excel files (openpyxl) — `inventory.xlsx` & `finance.xlsx`
- **Packaging**: PyInstaller-compatible Windows EXE

---

## 🚀 Quick Start

### Method 1 — Run with Python

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Browser opens automatically at http://127.0.0.1:5000
```

### Method 2 — Build Windows EXE

```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller hotel_saiprasad.spec

# EXE will be at: dist/HotelSaiprasad.exe
# Copy inventory.xlsx and finance.xlsx to same folder as EXE (created automatically on first run)
```

---

## 📁 Project Structure

```
hotel_saiprasad/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── hotel_saiprasad.spec    # PyInstaller build spec
├── inventory.xlsx          # Auto-created on first run
├── finance.xlsx            # Auto-created on first run
├── templates/
│   ├── base.html           # Base layout + sidebar
│   ├── dashboard.html      # Main dashboard
│   ├── inventory.html      # Inventory list
│   ├── inventory_form.html # Add/Edit inventory item
│   ├── finance.html        # Finance list + stats
│   └── finance_form.html   # Add/Edit transaction
└── static/                 # CSS, JS, images
```

---

## 📦 Modules

### Dashboard
- Inventory summary (total, low stock, out of stock, categories)
- Finance summary (today's & monthly revenue/expenses/profit-loss)
- Recent inventory & transaction activity
- Low stock & out-of-stock alerts

### Inventory Management
- Full CRUD (Add/Edit/Delete items)
- Auto-generated Item IDs (INV-0001, INV-0002, …)
- Auto-calculated status (Available / Low Stock / Out of Stock)
- Search by name, ID, or supplier
- Filter by category and status
- Export to Excel

### Finance / Profit-Loss
- Full CRUD for Revenue and Expense transactions
- Auto-generated Transaction IDs (TXN-0001, …)
- Today's & monthly profit/loss calculations
- Revenue categories: Room Booking, Restaurant, Event Booking, Other Income
- Expense categories: Maintenance, Housekeeping, Food Purchase, Electricity, Water, Staff Salary, Miscellaneous
- Filter by type, category, date
- Export to Excel

---

## 💾 Data Storage

All data is stored locally in Excel files:
- `inventory.xlsx` — All inventory items
- `finance.xlsx` — All financial transactions

Files are created automatically on first launch. No internet or database required.

---

## 🔧 Notes for EXE Distribution

When distributing the EXE:
1. The EXE is self-contained (Flask + templates embedded)
2. `inventory.xlsx` and `finance.xlsx` are created in the **same folder** as the EXE on first run
3. To backup data, simply copy the two `.xlsx` files

---

*Hotel Saiprasad Management System v1.0 — Offline Edition*
