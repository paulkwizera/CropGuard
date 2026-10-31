"""
Pick ONE final answer when the detector (YOLO) and Gemini have both looked at a photo.

Pure logic: no network and no database, so every rule here is covered by plain unit tests.

Who is trusted for what:
  * WHICH CROP the leaf is: Gemini. A detector only knows its own crop, so it can never say "not my crop".
    When Gemini sees another crop, the photo is checked again with THAT crop's detector, which still decides the disease.
  * WHICH DISEASE (same crop): the detector, because it was trained on this data, unless it is weak
    (below VERIFY_DETECTOR_TRUST, or found nothing) AND Gemini is highly certain.
  * NOT A MAIZE/CASSAVA LEAF (another plant, or no leaf at all): Gemini always intervenes, once it is at least
    moderately sure. The detectors cannot say "not my crop", so whatever they answered about such a photo is meaningless.
    (A "low" certainty answer never gets this far: it is treated as "unsure".)
  * A real problem the app has no name for ("Other problem"): if Gemini is highly certain and the detector is not,
    the answer becomes the disease name Gemini suggests (or "Other leaf problem (not <what the detector said>)" when
    it has no name): better than headlining a disease Gemini has just ruled out. Otherwise the detector's answer stays.
  * For disease questions, an answer Gemini is only moderately sure about never overrules the detector.
"""
from django.conf import settings

from apps.advisory.services import advisor


def summarize(results: list[dict]) -> tuple[str, dict | None]:
    """Pick the headline of a check. A disease always wins over a 'healthy' region of the same photo."""
    diseases = [r for r in results if not r.get("healthy")]
    healthy = [r for r in results if r.get("healthy")]
    if diseases:
        return "disease", diseases[0]
    if healthy:
        return "healthy", healthy[0]
    return "none", None


def _answer(crop: str, results: list[dict]) -> dict:
    status, top = summarize(results)
    return {
        "crop": crop,
        "status": status,
        "top_label": top["label"] if top else "",
        "top_confidence": top["confidence"] if top else None,
        "results": results,
    }


NOT_SUPPORTED_LABEL = "Not a maize or cassava leaf"
NO_LEAF_LABEL = "No leaf found in the photo"
OTHER_PROBLEM_LABEL = "Other leaf problem"


def _from_gemini(gemini: dict) -> dict:
    """Gemini's reading as a final answer. It has no percentage and no box, so those stay empty."""
    healthy = gemini["condition"].startswith("Healthy")
    return {
        "crop": gemini["crop"],
        "status": "healthy" if healthy else "disease",
        "top_label": gemini["condition"],
        "top_confidence": None,
        "results": [],
    }


def decide(detector: dict, gemini: dict, rerun) -> dict:
    """
    detector: the detector's answer {crop, status, top_label, top_confidence, results}
    gemini:   advisor.judge() output (verdict, crop, condition, certainty, ...)
    rerun:    rerun(crop) -> that crop's detections, [] if it finds nothing, None if it cannot be run

    Returns {"final": the answer to store and show, "resolution": what to tell the farmer about how it was chosen}.
    resolution = {winner: "detector"|"gemini", basis, crop_changed, detector: the detector's ORIGINAL answer}
    basis: confirmed | unconfirmed | detector_more_certain | gemini_more_certain | not_supported | not_a_leaf
    """
    trust = getattr(settings, "VERIFY_DETECTOR_TRUST", 0.80)
    original = {k: detector[k] for k in ("crop", "status", "top_label", "top_confidence")}

    def result(winner, basis, final, crop_changed=False):
        return {
            "final": final,
            "resolution": {"winner": winner, "basis": basis, "crop_changed": crop_changed, "detector": original},
        }

    keep = {k: detector[k] for k in ("crop", "status", "top_label", "top_confidence", "results")}
    verdict = gemini["verdict"]
    if verdict == "agree":
        return result("detector", "confirmed", keep)
    if verdict == "unsure":
        return result("detector", "unconfirmed", keep)
    if verdict in ("not_leaf", "other_crop"):
        no_leaf = verdict == "not_leaf"
        final = {"crop": "other", "status": "other", "top_label": NO_LEAF_LABEL if no_leaf else NOT_SUPPORTED_LABEL,
                 "top_confidence": None, "results": []}
        return result("gemini", "not_a_leaf" if no_leaf else "not_supported", final)

    # verdict == "disagree": Gemini reads the leaf differently from the detector.
    current, crop_changed = keep, False
    if gemini["crop"] != detector["crop"]:
        results = rerun(gemini["crop"])
        if results is not None:  # the right crop's detector now decides the disease
            current, crop_changed = _answer(gemini["crop"], results), True
            if advisor.agrees(current, gemini["crop"], gemini["condition"]):
                return result("detector", "confirmed", current, crop_changed)

    detector_is_sure = current["status"] != "none" and (current["top_confidence"] or 0) >= trust
    if gemini["condition"] == advisor.OTHER_PROBLEM:  # a real problem, but one the app has no name for
        if detector_is_sure:
            return result("detector", "detector_more_certain", current, crop_changed)
        if gemini["certainty"] == "high":  # do not headline a disease that Gemini has just ruled out
            ruled_out = current["top_label"] if current["status"] == "disease" else ""
            label = gemini.get("problem_name") or (f"{OTHER_PROBLEM_LABEL} (not {ruled_out})" if ruled_out else OTHER_PROBLEM_LABEL)
            final = {"crop": gemini["crop"], "status": "disease", "top_label": label, "top_confidence": None, "results": []}
            return result("gemini", "gemini_more_certain", final, crop_changed or gemini["crop"] != detector["crop"])
        return result("detector", "unconfirmed", current, crop_changed)
    if gemini["certainty"] == "high" and not detector_is_sure:
        return result("gemini", "gemini_more_certain", _from_gemini(gemini), crop_changed or gemini["crop"] != detector["crop"])
    return result("detector", "detector_more_certain" if detector_is_sure else "unconfirmed", current, crop_changed)
