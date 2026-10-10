from pathlib import Path
import json, os

ROOT=Path(__file__).resolve().parents[1]
FINDINGS=ROOT/"narrator/findings.json"
SAMPLE=ROOT/"narrator/sample_output.txt"

def generate_scr_narrative(findings:dict)->dict:
    try:
        from google import genai
        from google.genai import types
        key=os.getenv("GEMINI_API_KEY")
        if not key:
            return {"status":"error","narrative":None,"message":"GEMINI_API_KEY is not configured."}
        client=genai.Client(api_key=key)
        system_instruction=("You are a senior data analyst writing for Mamaearth's regional ops and finance heads. "
            "Write exactly three labeled sections: Situation, Complication, Resolution. "
            "Every number must come only from supplied findings and retain the same value. Do not invent statistics.")
        user_prompt=("Write a concise SCR business narrative using this verified findings JSON. "
            "Do not add any numbers not present in the JSON.\n\n"+json.dumps(findings,indent=2))
        # Temperature 0: deterministic because this is factual business reporting.
        response=client.models.generate_content(
            model="gemini-2.5-flash", contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0, max_output_tokens=500,
                http_options=types.HttpOptions(timeout=10000)))
        tokens=getattr(getattr(response,"usage_metadata",None),"total_token_count",None)
        return {"status":"success","narrative":response.text,"tokens":tokens}
    except Exception as err:
        return {"status":"error","narrative":None,"message":str(err)}

def generate_scr_narrative_offline(f:dict)->dict:
    cleaned=f["cleaned_total_revenue_inr"]; raw=f["raw_total_revenue_inr"]; delta=f["duplicate_reconciliation_delta_inr"]
    cod=f["return_rate_by_payment"]["COD"]; card=f["return_rate_by_payment"]["CARD"]; upi=f["return_rate_by_payment"]["UPI"]
    risk=f["highest_risk_segment"]; peak=f["true_peak_month"]; inflated=f["outlier_inflated_month"]
    text=f"""Situation
The cleaned analysis shows revenue of ₹{cleaned:,.2f} versus raw revenue of ₹{raw:,.2f}. COD has the highest payment-method return rate at {cod:.1f}%, compared with {card:.1f}% for CARD and {upi:.1f}% for UPI.

Complication
Five duplicate submissions create a reconciliation delta of ₹{delta:,.2f}. The highest-risk segment is {risk["payment_method"]} + Tier-{risk["city_tier"]}, with a {risk["return_rate_pct"]:.1f}% return rate. January's apparent revenue peak is inflated by the quantity outliers.

Resolution
After correcting the outliers, {peak["month"]} is the true peak month at ₹{peak["revenue_inr"]:,.2f}. Operations should prioritize the COD + Tier-{risk["city_tier"]} segment, while finance should report cleaned revenue and exclude duplicate submissions."""
    return {"status":"success","narrative":text,"tokens":None}

def check_numeric_accuracy(text:str)->bool:
    t=text.replace(",","")
    checks=[
        ("cleaned revenue","97358.3" in t),
        ("COD return rate","44.4" in t),
        ("highest-risk segment","54.5" in t),
        ("duplicate delta","2501.9" in t),
        ("March peak",("2026-03" in t or "March" in t) and "20318.9" in t)
    ]
    ok=True
    print("\nNUMERIC ACCURACY CHECK")
    for label,passed in checks:
        print(label,":","PASS" if passed else "FAIL"); ok &= passed
    return ok

if __name__=="__main__":
    findings=json.loads(FINDINGS.read_text())
    result=generate_scr_narrative(findings)
    if result["status"]=="error":
        print("Gemini unavailable:",result["message"])
        print("Using offline fallback.")
        result=generate_scr_narrative_offline(findings)
    print("\n"+result["narrative"])
    check_numeric_accuracy(result["narrative"])
    SAMPLE.write_text(result["narrative"]+"\n",encoding="utf-8")
    print("\nSaved:",SAMPLE)
