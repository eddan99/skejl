"""
Multi-Agent Debate System - Optimizes image settings through agent consensus.

Three agents debate to finalize image settings:
1. Data-Driven Optimizer - Advocates for ML predictions based on conversion data
2. Creative Differentiator - Proposes creative alternatives for brand differentiation
3. Moderator - Synthesizes consensus from both perspectives

Single-round debate: Optimizer → Creative → Moderator → Final decision
"""

import os
import json
from typing import Dict
from google import genai

DEFAULT_BRAND_IDENTITY = (
    "A modern, minimalist e-commerce brand. Clean, confident, and always "
    "doing references to breaking bad series"
)


def _run_optimizer_agent(ml_prediction: Dict) -> str:
    """
    Agent 1: Data-Driven Optimizer

    Advocates for ML-predicted settings based on historical performance data.

    Args:
        ml_prediction: Dict with image_settings, predicted_conversion_rate, reasoning

    Returns:
        Optimizer's argument as string
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    client = genai.Client(api_key=api_key)

    settings = ml_prediction['image_settings']
    conversion = ml_prediction['predicted_conversion_rate']
    confidence = ml_prediction.get('confidence', 0)

    prompt = f"""You are a data-driven optimizer for e-commerce product photography.

Your role: Advocate for proven, high-converting image settings based on ML analysis.

ML PREDICTION:
{json.dumps(settings, indent=2)}

EXPECTED CONVERSION RATE: {conversion*100:.2f}%
MODEL CONFIDENCE: {confidence*100:.1f}%

REASONING:
{ml_prediction.get('reasoning', 'Based on historical performance data')}

Make your case for following this data-driven approach. Be specific about:
1. Why these settings are predicted to perform well
2. What the data shows about similar products
3. The business value of optimizing for conversion

Keep your argument concise (2-3 paragraphs). Focus on facts and performance metrics.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text.strip()


def _run_creative_agent(
    ml_prediction: Dict,
    product_features: Dict,
    brand_identity: str = None
) -> str:
    """
    Agent 2: Creative Differentiator

    Proposes creative alternatives for brand differentiation and visual impact.

    Args:
        ml_prediction: ML prediction dict
        product_features: Product features (garment_type, color, fit, gender)
        brand_identity: Brand identity description

    Returns:
        Creative's argument as string
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    client = genai.Client(api_key=api_key)

    if brand_identity is None:
        brand_identity = DEFAULT_BRAND_IDENTITY

    settings = ml_prediction['image_settings']

    prompt = f"""You are a creative strategist for e-commerce product photography.

Your role: Balance data-driven decisions with creative brand differentiation.

BRAND IDENTITY:
{brand_identity}

PRODUCT:
{json.dumps(product_features, indent=2)}

ML RECOMMENDATION:
{json.dumps(settings, indent=2)}

While data shows these settings perform well, consider:
1. Does this align with our brand identity?
2. Are we differentiating from competitors or following generic trends?
3. Could creative alternatives create stronger brand recall?
4. What about visual storytelling and emotional connection?

Provide your perspective:
- If ML settings align with brand, acknowledge and suggest minor enhancements
- If they feel generic, propose creative alternatives that still consider performance
- Balance creativity with business goals

Keep your argument concise (2-3 paragraphs). Be constructive and specific.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text.strip()


def _run_moderator(
    optimizer_argument: str,
    creative_argument: str,
    ml_prediction: Dict,
    product_features: Dict
) -> Dict:
    """
    Agent 3: Moderator/Consensus Builder

    Synthesizes final decision from both perspectives.

    Args:
        optimizer_argument: Data-driven argument
        creative_argument: Creative alternative argument
        ml_prediction: Original ML prediction
        product_features: Product features

    Returns:
        Dict with final_image_settings and reasoning
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    client = genai.Client(api_key=api_key)

    ml_settings = ml_prediction['image_settings']

    prompt = f"""You are a moderator synthesizing the best decision from two perspectives.

PRODUCT FEATURES:
{json.dumps(product_features, indent=2)}

ML PREDICTION (Data-Driven):
{json.dumps(ml_settings, indent=2)}
Predicted conversion: {ml_prediction['predicted_conversion_rate']*100:.2f}%

OPTIMIZER'S ARGUMENT (Data-Driven):
{optimizer_argument}

CREATIVE'S ARGUMENT (Brand Differentiation):
{creative_argument}

Your task: Build consensus and decide final image settings.

Consider:
1. Both perspectives have merit - find the balanced approach
2. Can we keep high-performing settings while adding creative touches?
3. Which settings are most critical for conversion vs brand differentiation?

Respond with JSON in this exact format:
{{
  "final_image_settings": {{
    "style": "chosen_style",
    "lighting": "chosen_lighting",
    "background": "chosen_background",
    "pose": "chosen_pose",
    "expression": "chosen_expression",
    "angle": "chosen_angle"
  }},
  "reasoning": "2-3 sentence explanation of your synthesis",
  "consensus_type": "full_agreement" | "hybrid_approach" | "creative_override"
}}

CRITICAL: Respond with ONLY valid JSON. No markdown code fences, no extra text.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    # Parse response
    response_text = response.text.strip()

    # Remove markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    try:
        consensus = json.loads(response_text)
        return consensus
    except json.JSONDecodeError as e:
        # Fallback: use optimizer (data-driven) choice
        print(f"Warning: Moderator JSON parse failed ({e}). Using ML prediction.")
        return {
            "final_image_settings": ml_settings,
            "reasoning": "Defaulting to data-driven ML prediction due to consensus parsing issue.",
            "consensus_type": "fallback_to_ml"
        }


def multi_agent_debate(
    ml_prediction: Dict,
    product_features: Dict,
    brand_identity: str = None
) -> Dict:
    """
    Run multi-agent debate to finalize image settings.

    Single-round debate:
    1. Optimizer presents data-driven case for ML prediction
    2. Creative presents alternative perspective considering brand
    3. Moderator synthesizes consensus

    Args:
        ml_prediction: Dict from predict_image_settings() with:
            - image_settings: ML-predicted settings
            - predicted_conversion_rate: Expected conversion
            - confidence: Model confidence
            - reasoning: ML reasoning
        product_features: Dict with garment_type, color, fit, gender
        brand_identity: Optional brand identity description

    Returns:
        Dict with:
            - final_image_settings: Consensus image settings
            - reasoning: Moderator's reasoning
            - debate_log: Full debate transcript
            - consensus_type: Type of consensus reached
    """
    print("Starting multi-agent debate...")

    # Agent 1: Data-driven optimizer
    print("  Agent 1 (Optimizer): Analyzing ML prediction...")
    optimizer_response = _run_optimizer_agent(ml_prediction)

    # Agent 2: Creative differentiator
    print("  Agent 2 (Creative): Considering brand alignment...")
    creative_response = _run_creative_agent(
        ml_prediction,
        product_features,
        brand_identity
    )

    # Agent 3: Moderator
    print("  Agent 3 (Moderator): Synthesizing consensus...")
    consensus = _run_moderator(
        optimizer_response,
        creative_response,
        ml_prediction,
        product_features
    )

    # Build result
    result = {
        "final_image_settings": consensus["final_image_settings"],
        "reasoning": consensus["reasoning"],
        "consensus_type": consensus.get("consensus_type", "unknown"),
        "debate_log": {
            "ml_prediction": ml_prediction,
            "optimizer_argument": optimizer_response,
            "creative_argument": creative_response,
            "moderator_decision": consensus
        }
    }

    print(f"  Consensus reached: {result['consensus_type']}")

    return result


if __name__ == "__main__":
    # Load environment variables for testing
    from dotenv import load_dotenv
    load_dotenv()

    # Test the debate system
    print("Testing multi-agent debate system...\n")

    # Mock ML prediction
    mock_ml_prediction = {
        "image_settings": {
            "style": "urban_outdoor",
            "lighting": "golden_hour",
            "background": "graffiti_wall",
            "pose": "walking",
            "expression": "confident",
            "angle": "front"
        },
        "predicted_conversion_rate": 0.042,
        "confidence": 0.85,
        "reasoning": "Based on 150 similar dark hoodies with 1000+ impressions"
    }

    mock_product_features = {
        "garment_type": "hoodie",
        "color": "dark",
        "fit": "loose",
        "gender": "male"
    }

    # Run debate
    result = multi_agent_debate(
        mock_ml_prediction,
        mock_product_features
    )

    # Print results
    print("\n" + "="*60)
    print("DEBATE RESULTS")
    print("="*60)
    print(f"\nFinal Image Settings:")
    print(json.dumps(result['final_image_settings'], indent=2))
    print(f"\nReasoning: {result['reasoning']}")
    print(f"\nConsensus Type: {result['consensus_type']}")

    print("\n" + "="*60)
    print("FULL DEBATE TRANSCRIPT")
    print("="*60)

    print("\nOPTIMIZER:")
    print(result['debate_log']['optimizer_argument'])

    print("\nCREATIVE:")
    print(result['debate_log']['creative_argument'])

    print("\nMODERATOR DECISION:")
    print(json.dumps(result['debate_log']['moderator_decision'], indent=2))
