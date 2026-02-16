# skejl

AI-driven fashion photography pipeline — from product image to published Shopify listing.

## How to use

1. **Enter your Gemini API key** if not already set in `.env`
2. **Set brand identity** — or press Skip to keep the current one
3. **Upload files** — drag in `products.json` + all product images at once
4. The pipeline runs automatically for each product:
   - Extracts features (garment type, color, fit, gender)
   - ML prediction → best image settings for CTR
   - 3-agent debate (Optimizer, Creative, Moderator)
   - Generates photorealistic fashion image
   - Validates + generates side/back variants
5. **Review the result** — write feedback to refine, or use the action buttons

## Commands

| Command | What it does |
|---|---|
| `/brand` | View and update the brand identity (affects descriptions and photography style) |
| `/retrain` | Retrain the CTR prediction model on the current dataset |
| `publish` | Publish the current product to Shopify (also works: `publicera`) |

## Tips

- If generation fails, describe what to change and the pipeline retries with your guidance
- Shopify credentials can be entered in the chat — no need to restart if they're missing from `.env`
- Upload more images at any time to continue processing
