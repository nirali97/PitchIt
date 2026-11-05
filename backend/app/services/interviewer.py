"""Deterministic interviewer state: progressive fact reveal + stage-aware fallback
questions. Pure Python (no DB/LLM) so it is cheap and unit-testable."""
import re


def fact_texts(case: dict, idxs: list[int]) -> list[str]:
    pool = case.get("fact_pool", [])
    return [pool[i]["text"] for i in sorted(set(idxs)) if 0 <= i < len(pool)]


def update_reveals(case: dict, message: str, revealed: list[int]) -> tuple[list[int], list[int]]:
    """Reveal gated facts whose topic words appear in the candidate's message.
    Returns (all_revealed, newly_revealed)."""
    words = set(re.findall(r"[a-z]+", message.lower()))
    have, new = set(revealed), []
    for i, f in enumerate(case.get("fact_pool", [])):
        if i in have or not f["tags"]:
            continue
        if any(t in words or (len(t) > 4 and t in message.lower()) for t in f["tags"]):
            new.append(i)
            have.add(i)
    return sorted(have), new


def stage_question(candidate_msgs: list[str], prior_questions: list[str]) -> str:
    text = " ".join(candidate_msgs).lower()
    has_hyp = any(w in text for w in ("hypothesis", "i think", "likely", "because", "suspect"))
    has_num = bool(re.search(r"\d", text))
    has_rec = any(w in text for w in ("recommend", "therefore", "conclude", "i would advise"))
    ladder = []
    if not has_hyp:
        ladder.append("What is your initial hypothesis, and what evidence would prove it wrong?")
    if not has_num:
        ladder.append("Can you quantify that? Walk me through the calculation and your assumptions.")
    if not has_rec:
        ladder.append("Given what we have discussed, what would you recommend and why?")
    ladder += [
        "What is the biggest risk to your recommendation, and how would you test it?",
        "Which single next analysis would change your mind, and what would you expect to see?",
    ]
    for q in ladder:
        if q not in prior_questions:
            return q
    return "What would you do differently if your key assumption turned out to be wrong?"
