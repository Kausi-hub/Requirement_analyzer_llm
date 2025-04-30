import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
HARD_RULES = [
    rule.strip() for rule in os.getenv("HARD_RULES", "").split("|") if rule.strip()
]
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo-0125")
MAX_TURNS = int(os.getenv("MAX_TURNS", "5"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

SYSTEM_PROMPT_B = f"""
You are LLM_B (Meta-Agent), an internal critic and stakeholder requirement reviewer. You:
- Detect weak logic, vague claims, contradictions, inconsistencies, or hallucinations
- Flag vague qualifiers like 'maybe', 'can', 'likely', 'possibly'
- Suggest improvements for clarity, logic, and factual consistency
- Rate satisfaction with the input requirements and reasoning (0-1)

Hard Rules:
{chr(10).join(f'- {rule}' for rule in HARD_RULES)}
"""

class ReasoningState:
    def __init__(self):
        self.memory: List[str] = []
        self.satisfaction_level: float = 0.0
        self.issues: Dict[str, List[str]] = {
            "contradictions": [],
            "inconsistencies": [],
            "vagueness": [],
            "incompleteness": []
        }


def call_llm(prompt: str, system_prompt: str = SYSTEM_PROMPT_B, model: str = DEFAULT_MODEL) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM error: {e}")
        raise


def analyze_requirements(requirements: List[str]) -> Dict:
    prompt = """Analyze the following user requirements. Identify and report:
1. Contradictions
2. Inconsistencies
3. Vagueness
4. Incompleteness

List issues with reasoning. Provide a satisfaction score (0-1).

Requirements:\n""" + "\n".join(f"- {req}" for req in requirements)

    critique = call_llm(prompt)

    result = {
        "satisfaction": 0.0,
        "issues": {
            "contradictions": [],
            "inconsistencies": [],
            "vagueness": [],
            "incompleteness": []
        },
        "raw_output": critique
    }

    try:
        satisfaction_line = [line for line in critique.splitlines() if "satisfaction score" in line.lower()]
        if satisfaction_line:
            result["satisfaction"] = float(satisfaction_line[0].split(":")[-1].strip())

        for category in result["issues"].keys():
            if category in critique.lower():
                section = critique.lower().split(category)[1].split("\n\n")[0]
                result["issues"][category] = [line.strip("- ") for line in section.split("\n") if line.strip().startswith("-")]
    except Exception as e:
        logger.warning(f"Error parsing critique: {e}")

    return result


# CLI usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python metagent.py '<requirement1>|<requirement2>|...'")
        sys.exit(1)

    requirements = sys.argv[1].split("|")
    result = analyze_requirements(requirements)
    print(json.dumps(result, indent=2))
