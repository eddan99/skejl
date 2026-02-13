"""
Multi-Agent Debate System - Optimizes image settings through agent consensus.

Three agents debate to finalize image settings:
1. Data-Driven Optimizer - Advocates for ML predictions based on conversion data
2. Creative Differentiator - Proposes creative alternatives for brand differentiation
3. Moderator - Synthesizes consensus from both perspectives

Single-round debate: Optimizer → Creative → Moderator → Final decision
"""

import json
from typing import Dict
from config.settings import settings
from tools.gemini_client import get_gemini_client, get_model_name
from tools.json_utils import parse_gemini_response
from tools.taxonomy import validate_image_settings
from tools.prompts import (
    build_optimizer_prompt,
    build_creative_prompt,
    build_moderator_prompt
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
    client = get_gemini_client()
    prompt = build_optimizer_prompt(ml_prediction)

    response = client.models.generate_content(
        model=get_model_name(),
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
    client = get_gemini_client()

    if brand_identity is None:
        brand_identity = settings.DEFAULT_BRAND_IDENTITY

    prompt = build_creative_prompt(ml_prediction, product_features, brand_identity)

    response = client.models.generate_content(
        model=get_model_name(),
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
    client = get_gemini_client()
    ml_settings = ml_prediction['image_settings']

    prompt = build_moderator_prompt(
        optimizer_argument,
        creative_argument,
        ml_prediction,
        product_features
    )

    response = client.models.generate_content(
        model=get_model_name(),
        contents=prompt
    )

    consensus = parse_gemini_response(response.text)

    if "error" in consensus:
        print(f"Warning: Moderator JSON parse failed. Using ML prediction.")
        return {
            "final_image_settings": ml_settings,
            "reasoning": "Defaulting to data-driven ML prediction due to consensus parsing issue.",
            "consensus_type": "fallback_to_ml"
        }

    try:
        validate_image_settings(consensus["final_image_settings"])
    except ValueError as e:
        print(f"Warning: Moderator returned invalid settings ({e}). Using ML prediction.")
        return {
            "final_image_settings": ml_settings,
            "reasoning": "Defaulting to data-driven ML prediction due to invalid consensus settings.",
            "consensus_type": "fallback_to_ml"
        }

    return consensus


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

    print("  Agent 1 (Optimizer): Analyzing ML prediction...")
    optimizer_response = _run_optimizer_agent(ml_prediction)

    print("  Agent 2 (Creative): Considering brand alignment...")
    creative_response = _run_creative_agent(
        ml_prediction,
        product_features,
        brand_identity
    )

    print("  Agent 3 (Moderator): Synthesizing consensus...")
    consensus = _run_moderator(
        optimizer_response,
        creative_response,
        ml_prediction,
        product_features
    )

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
    from dotenv import load_dotenv
    load_dotenv()

    print("Testing multi-agent debate system...\n")

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

    result = multi_agent_debate(
        mock_ml_prediction,
        mock_product_features
    )

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
