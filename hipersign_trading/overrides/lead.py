from hipersign_trading.constants import LEAD_PROBABILITY


def validate(doc, method=None):
	stage = doc.get("hs_pipeline_stage") or "New"
	doc.hs_pipeline_stage = stage
	doc.hs_probability = LEAD_PROBABILITY.get(stage, 0)
	if stage in ("Won", "Lost"):
		doc.hs_next_follow_up = None
	if stage == "Won" and doc.status not in ("Converted", "Quotation", "Opportunity"):
		doc.status = "Interested"
