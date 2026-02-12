# MongoDB Atlas Setup Guide

This guide shows how to set up MongoDB Atlas (cloud) and migrate your data from JSON.

---

## Step 1: Create MongoDB Atlas Account

1. Go to [https://www.mongodb.com/cloud/atlas/register](https://www.mongodb.com/cloud/atlas/register)
2. Sign up (free tier available - 512MB)
3. Verify your email

---

## Step 2: Create a Cluster

1. Click **"Build a Database"**
2. Select **M0 Free** tier
3. Choose a cloud provider (AWS recommended)
4. Select region closest to you (e.g., Stockholm for EU)
5. Click **"Create"**
6. Wait 1-3 minutes for cluster to deploy

---

## Step 3: Create Database User

1. Go to **"Database Access"** (left sidebar)
2. Click **"Add New Database User"**
3. Choose **"Password"** authentication
4. Username: `skejl_user` (or your choice)
5. Password: Generate strong password (save it!)
6. Database User Privileges: **"Read and write to any database"**
7. Click **"Add User"**

---

## Step 4: Whitelist Your IP

1. Go to **"Network Access"** (left sidebar)
2. Click **"Add IP Address"**
3. Choose **"Allow Access from Anywhere"** (for development)
   - Or add your specific IP for security
4. Click **"Confirm"**

---

## Step 5: Get Connection String

1. Go to **"Database"** (left sidebar)
2. Click **"Connect"** on your cluster
3. Select **"Drivers"**
4. Select **Python** and version **3.12 or later**
5. Copy the connection string (looks like):
   ```
   mongodb+srv://skejl_user:<password>@cluster0.xxxxx.mongodb.net/
   ```
6. Replace `<password>` with your actual password from Step 3

---

## Step 6: Configure Your Project

1. Open `.env` file
2. Update these lines:
   ```env
   # Change from json to mongodb
   DATABASE_TYPE=mongodb

   # Add your connection string
   MONGODB_URI=mongodb+srv://skejl_user:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/
   ```

3. Save `.env`

---

## Step 7: Install Dependencies

```bash
pip install pymongo
```

Or use requirements.txt:
```bash
pip install -r requirements.txt
```

---

## Step 8: Migrate Data from JSON to MongoDB

Run this Python script:

```python
# tools/migrate_to_mongodb.py
from dotenv import load_dotenv
load_dotenv()

import os
os.environ["DATABASE_TYPE"] = "mongodb"  # Force MongoDB mode

from tools.database.json_db import JSONDatabase
from tools.database.mongo_db import MongoDatabase

# Load from JSON
json_db = JSONDatabase()
data = json_db._load_data()
products = data.get("products", [])

# Save to MongoDB
mongo_db = MongoDatabase()

print(f"Migrating {len(products)} products to MongoDB...")
for product in products:
    mongo_db.add_product(product)

print("Migration complete!")
print(f"Total products in MongoDB: {mongo_db.get_total_products()}")
```

Run it:
```bash
python -c "from tools.migrate_to_mongodb import *"
```

Or create the file and run:
```bash
python tools/migrate_to_mongodb.py
```

---

## Step 9: Test MongoDB Connection

```bash
python tools/performance_lookup.py
```

You should see:
```
Testing Performance Lookup with MONGODB database...
Total products: 200
Found 5 dark hoodies with 1000+ impressions
...
```

---

## Step 10: Switch Between JSON and MongoDB

Simply change `.env`:

**Development (JSON):**
```env
DATABASE_TYPE=json
```

**Production (MongoDB):**
```env
DATABASE_TYPE=mongodb
MONGODB_URI=mongodb+srv://...
```

No code changes needed!

---

## Troubleshooting

### Error: "Failed to connect to MongoDB"
- Check MONGODB_URI is correct
- Check password has no special characters (or URL encode them)
- Check IP is whitelisted in Network Access

### Error: "pymongo is required"
- Run: `pip install pymongo`

### Error: "Authentication failed"
- Check username/password in connection string
- Verify database user exists in Database Access

---

## MongoDB Atlas Dashboard

View your data:
1. Go to **"Database"** → **"Browse Collections"**
2. You'll see database: `skejl_db`
3. Collection: `products`
4. Click to browse all 200 products

---

## Free Tier Limits

MongoDB Atlas M0 Free:
- 512 MB storage
- Shared RAM
- Shared vCPU
- Perfect for development and thesis projects!

Your 200 products use ~500KB, so plenty of space for testing.

---

## Next Steps

Once MongoDB is set up, you can:
1. Toggle between JSON (development) and MongoDB (production)
2. Add more products without file size concerns
3. Leverage MongoDB's powerful querying
4. Show scalability in your thesis report
