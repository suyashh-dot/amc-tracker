# AMC Portfolio Intelligence — Setup Guide

## What you're setting up

```
suyashh-dot/amc-tracker   ← the website (this repo)
suyashh-dot/amc-data       ← the data (separate repo)
```

The website fetches data from `amc-data` every time someone opens it.
To update data: run one Python command → done.

---

## One-time setup (do this once)

### Step 1 — Create the two GitHub repos

1. Go to github.com → New repository
2. Name it **amc-data** → Public → Create (no README)
3. Go to github.com → New repository  
4. Name it **amc-tracker** → Public → Create (no README)

### Step 2 — Upload data files to amc-data

```bash
cd amc-data/
git init
git remote add origin https://github.com/suyashh-dot/amc-data.git
git add .
git commit -m "Initial data upload"
git branch -M main
git push -u origin main
```

Then go to: github.com/suyashh-dot/amc-data → Settings → Pages
→ Source: Deploy from branch → Branch: main → / (root) → Save

### Step 3 — Upload dashboard to amc-tracker

```bash
cd amc-tracker/
git init
git remote add origin https://github.com/suyashh-dot/amc-tracker.git
git add .
git commit -m "Initial dashboard"
git branch -M main
git push -u origin main
```

Then go to: github.com/suyashh-dot/amc-tracker → Settings → Pages
→ Source: Deploy from branch → Branch: main → / (root) → Save

### Step 4 — Your website is live

URL: **https://suyashh-dot.github.io/amc-tracker**

Wait ~2 minutes for GitHub Pages to deploy, then open the URL.

Default login: **admin / admin123**

---

## Change the admin password

Edit `amc-data/users.json`:

```json
{
  "users": [
    {
      "username": "admin",
      "passwordHash": "YOUR_NEW_HASH_HERE",
      "role": "admin",
      "name": "Admin"
    }
  ]
}
```

To generate a hash for your new password, run:

```python
import hashlib
pw = "your_new_password"
print(hashlib.sha256(pw.encode()).hexdigest())
```

Paste the output as `passwordHash`, push to amc-data.

---

## Add more users

Add entries to `amc-data/users.json`:

```json
{
  "users": [
    { "username": "admin", "passwordHash": "...", "role": "admin", "name": "Admin" },
    { "username": "rahul", "passwordHash": "...", "role": "viewer", "name": "Rahul" },
    { "username": "priya", "passwordHash": "...", "role": "viewer", "name": "Priya" }
  ]
}
```

Push users.json to amc-data — new users can log in immediately.

---

## Monthly update workflow

### Every month when new data is ready:

1. Prepare your Excel file for the new month
   - Same format as before: instrument names in column A, fund names in row headers, weights in cells
   - One Excel per month (e.g. `Mar-26.xlsx`)

2. Run the update script:

```bash
cd amc-tracker/
python update.py "path/to/Mar-26.xlsx"
```

That's it. The script will:
- Parse the Excel
- Merge with existing data
- Recompute all signals, sectors, first mover
- Push to GitHub automatically
- Website updates within 60 seconds

### What the output looks like:

```
=======================================================
  AMC Tracker — Monthly Update
=======================================================

[1/7] Loading existing data...
  Existing instruments: 1523

[2/7] Parsing new Excel...
  Parsing: Mar-26.xlsx
  Funds: 80
  Months in file: ['Mar-26']
  Instruments parsed: 1486

[3/7] Merging data...
  Total instruments after merge: 1541

[4/7] Updating sector map...

[5/7] Rebuilding signals, sectors, first mover...

[6/7] Saving data files...
  ✓ compressed_data.json (2891 KB)
  ✓ fund_data.json (2834 KB)
  ✓ signals.json (348 KB)
  ✓ sector_rotation.json (24 KB)
  ✓ first_mover.json (441 KB)
  ✓ sector_map.json (69 KB)
  ✓ metadata.json (1 KB)

[7/7] Pushing to GitHub...
  ✓ Pushed to GitHub successfully

=======================================================
  ✓ Update complete! Mar-26 is now live.
  Website updates within 60 seconds.
=======================================================
```

---

## Excel format requirements

Your monthly Excel must follow this structure:

| Row | Content |
|-----|---------|
| Row 1 | Title / legend (ignored) |
| Row 2 | Fund names (merged across their month columns) |
| Row 3 | `Name of Instrument` in col A, then month labels per fund |
| Row 4+ | Instrument names in col A, weights as decimals in data cells |

Weights must be stored as decimals:
- 5.23% → store as `0.0523`
- 1.8% → store as `0.018`

The script auto-detects the month label from the column headers (e.g. `Mar-26`).

---

## Requirements

```bash
pip install pandas openpyxl
```

Python 3.8 or higher.

---

## Troubleshooting

**Login says "Could not reach auth server"**
→ Check that `amc-data` GitHub Pages is enabled and the URL resolves.
→ Wait 5 minutes after first deploy for GitHub CDN to warm up.

**Data not updating after push**  
→ GitHub Pages CDN can take 2–5 minutes. Hard refresh (Ctrl+Shift+R).
→ The fetch URL includes `?t=timestamp` to bust cache — should always be fresh.

**Update script git push fails**
→ Make sure you've set up git credentials: `git config --global user.email "you@example.com"`
→ You may need a GitHub Personal Access Token if using HTTPS. Set it with:
  `git remote set-url origin https://YOUR_TOKEN@github.com/suyashh-dot/amc-data.git`

**New instruments showing as "Other" sector**
→ Open `amc-data/sector_map.json`, find the instrument, change `"Other"` to the correct sector name.
→ Push the file. No rebuild needed — the dashboard reads it live.
