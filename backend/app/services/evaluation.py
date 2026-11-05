from pydantic import BaseModel, Field
from typing import Any
from .evidence import find_evidence

EVIDENCE_KEYWORDS = {
  "structured_thinking": ["structure", "break", "separate", "segment", "channel", "first", "then"],
  "hypothesis_development": ["hypothesis", "assume", "because", "test whether", "could be"],
  "quantitative_reasoning": ["calculate", "margin", "percent", "%", "growth", "per store", "average"],
  "business_judgment": ["customer", "competitor", "pricing", "retention", "operations", "market"],
  "prioritization": ["prioritize", "impact", "likely", "most important", "first"],
  "communication": [],
  "synthesis": ["recommend", "therefore", "so i would", "next step", "conclude"],
}
DIMENSIONS = ["structured_thinking", "hypothesis_development", "quantitative_reasoning", "business_judgment", "prioritization", "communication", "synthesis"]

class DimensionResult(BaseModel):
    dimension: str
    score: float = Field(ge=1, le=5)
    confidence: float = Field(ge=0, le=1)
    rationale: str
    evidence: list[dict[str, Any]] = []
    weakness: str = ""
    improvement: str = ""

class EvaluationResult(BaseModel):
    overall_score: float
    dimensions: list[DimensionResult]
    summary: str
    next_exercise: str
    mode: str = "deterministic_baseline"

def evaluate_text(text: str) -> EvaluationResult:
    """Transparent baseline rubric. Replace/augment with calibrated LLM evaluation later."""
    t = text.lower()
    words = len(text.split())
    signals = {
      "structured_thinking": (any(x in t for x in ["revenue", "cost", "customer", "market", "segment", "channel"]) and any(x in t for x in ["first", "then", "structure", "break", "analyze", "separate"])),
      "hypothesis_development": any(x in t for x in ["hypothesis", "assume", "because", "test whether", "could be"]),
      "quantitative_reasoning": any(x in t for x in ["calculate", "margin", "percent", "%", "growth", "per store", "average"]),
      "business_judgment": any(x in t for x in ["customer", "competitor", "pricing", "retention", "operations", "market"]),
      "prioritization": any(x in t for x in ["prioritize", "impact", "likely", "most important", "first"]),
      "communication": words >= 35 and words <= 350,
      "synthesis": any(x in t for x in ["recommend", "therefore", "so i would", "next step", "conclude"]),
    }
    results=[]
    for d in DIMENSIONS:
      ok=signals[d]
      score=3.5 if ok else (2.5 if words > 15 else 1.5)
      rationale = ("Your response contains an observable signal for this skill." if ok else "This response provides limited observable evidence for this skill; that is not proof you lack it.")
      results.append(DimensionResult(dimension=d, score=score, confidence=0.35, rationale=rationale,
        evidence=find_evidence(text, EVIDENCE_KEYWORDS[d]) if ok else [],
        weakness="Make the reasoning explicit and support it with case evidence." if not ok else "Develop the point with a clearer explanation and evidence.",
        improvement={"structured_thinking":"Separate the problem into non-overlapping drivers before investigating.","hypothesis_development":"State a testable hypothesis and identify what evidence would confirm or reject it.","quantitative_reasoning":"Show the formula, inputs, units and interpretation.","business_judgment":"Connect analysis to customer behavior, competitive dynamics and operational feasibility.","prioritization":"Rank issues by expected impact and ease or speed of testing.","communication":"Lead with the point, then explain the logic in concise signposted steps.","synthesis":"End with a recommendation, supporting reasons, risks and next steps."}[d]))
    overall=round(sum(x.score for x in results)/len(results),2)
    return EvaluationResult(overall_score=overall, dimensions=results,
      summary="This is an initial rule-based diagnostic, not a validated interview score. Use the dimension feedback as practice guidance, and treat low-confidence findings cautiously.",
      next_exercise="Re-answer the case in four parts: objective, issue tree, first hypothesis, and the evidence you would request.")
