# skejl

AI-driven fashion photography pipeline — from product image to published Shopify listing.

## How to use

1. **Open settings** — set your Gemini API key and brand identity
2. **Upload files** — drag in `products.json` + all product images at once
3. The pipeline runs automatically for each product:
   - Extracts features (garment type, color, fit, gender)
   - ML prediction → best image settings for CTR
   - 3-agent debate (Optimizer, Creative, Moderator)
   - Generates photorealistic fashion image
   - Validates + generates side/back variants
4. **Review the result** — write feedback to refine, or use the action buttons

## Settings

| Field                | Description                                |
| -------------------- | ------------------------------------------ |
| Gemini API Key       | Required for all AI features               |
| Brand Identity       | Affects descriptions and photography style |
| Shopify Shop Name    | Subdomain only, e.g. `my-store`            |
| Shopify Access Token | Admin API token (`shpat_...`)              |

## Commands

| Command    | What it does                                            |
| ---------- | ------------------------------------------------------- |
| `/retrain` | Retrain the CTR prediction model on the current dataset |

## Tips

- If generation fails, describe what to change and the pipeline retries with your guidance
- Write feedback in the chat when reviewing an image to refine it, e.g. _"more urban feel"_
- Upload more images at any time to continue processing
