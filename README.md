# skejl

AI-driven fashion photography pipeline. Extracts product features from a reference image, runs an ML-backed multi-agent debate to choose optimal photography settings, generates a photorealistic fashion image, validates it, and publishes to Shopify.

---

## Quick start

```bash
chainlit run ui/app.py
```

Open `http://localhost:8000` in your browser.

---

## Setup

### 1. Environment variables

Create a `.env` file in the project root:

```env
# Required
GEMINI_API_KEY=your_key_here

# Optional — can also be entered in the chat on first run
SHOPIFY_SHOP_NAME=your-store          # subdomain only, e.g. my-store
SHOPIFY_ACCESS_TOKEN=shpat_xxx

# Optional overrides
BRAND_IDENTITY="Your brand voice and style description"
GEMINI_MODEL_NAME=gemini-2.5-flash    # default
```

### 2. `data/input/products.json`

Each product image needs a matching entry:

```json
[
  {
    "image": "jacket.jpg",
    "art_nr": "1234-5678",
    "title": "My Jacket"
  }
]
```

---

## Chat flow

```
1. Enter Gemini API key          (skipped if GEMINI_API_KEY is in .env)
2. Set brand identity            (or press Skip to keep current)
3. Upload products.json + images (drag all files at once)
4. Pipeline runs automatically per image:
     → Extract features  (garment type, color, fit, gender)
     → ML prediction     (best image settings for CTR)
     → Agent debate      (Optimizer + Creative + Moderator)
     → Generate image    (up to 2 attempts)
     → Validate
     → Generate variants (side + back views)
5. Review generated images
     → Write feedback to refine, e.g. "more urban feel"
     → or press Publish / Regenerate / Skip
```

If generation fails after 2 attempts, describe what to change and the pipeline retries with your guidance.

---

## Commands

| Command | Description |
|---|---|
| `/brand` | View and update the brand identity used for descriptions and photography style |
| `/retrain` | Retrain the CTR prediction model on the current dataset |
| `publish` or `publicera` | Shortcut to publish the current product to Shopify |

---

## Shopify credentials

If `SHOPIFY_SHOP_NAME` or `SHOPIFY_ACCESS_TOKEN` are not in `.env`, the chat will ask for them the first time you press **Publish to Shopify**. They are stored in the session for the duration of the chat.

---

## Project structure

```
ui/
  app.py              Chainlit chat interface
  pipeline.py         Full pipeline orchestration

tools/
  vision_tool.py      Gemini vision — extract product features
  image_gen_tool.py   Gemini image generation
  validation.py       Validate generated image against reference
  scenario_generator.py  Build photography scenario from ML settings
  shopify_tool.py     Shopify Admin API
  prompts.py          All prompt builders
  taxonomy.py         Valid values + normalization for all fields
  feedback_loop.py    Append training samples + retrain model

  ml/
    ml_predictor.py         Predict best image settings (RandomForest)
    generate_ctr_dataset.py Regenerate synthetic training data

logic/
  agent.py            Multi-agent debate (Optimizer / Creative / Moderator)

config/
  settings.py         All configurable settings + env loading
  paths.py            All file paths

data/
  input/
    products.json     Product metadata
    ctr_dataset.json  Training data for CTR model
  output/             Generated images + analysis JSON
  models/             Trained RandomForest model
```
