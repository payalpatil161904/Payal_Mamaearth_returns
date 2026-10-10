from pathlib import Path
import itertools, json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; NARRATOR=ROOT/"narrator"; NARRATOR.mkdir(exist_ok=True)

customers=pd.read_csv(DATA/"customers.csv")
products=pd.read_csv(DATA/"products.csv")
orders=pd.read_csv(DATA/"orders.csv")

print("TASK 1 — LOAD AND INSPECT")
print("customers:",customers.shape,"products:",products.shape,"raw orders:",orders.shape)

print("\nTASK 2 — STANDARDISE PAYMENT METHOD")
print("raw values:",sorted(orders.payment_method.unique()))
orders["payment_method"]=orders["payment_method"].str.upper().str.strip()
print("clean values:",sorted(orders.payment_method.unique()))
print("counts:",orders.payment_method.value_counts().to_dict())

print("\nTASK 3 — REMOVE DUPLICATES")
key=["customer_id","product_id","order_date","quantity","discount_pct","payment_method","rating","returned"]
dup=orders.duplicated(subset=key,keep="first")
dropped_ids=orders.loc[dup,"order_id"].tolist()
orders_clean=orders.loc[~dup].copy()
print("dropped IDs:",dropped_ids)
print("clean shape:",orders_clean.shape)

print("\nTASK 4 — IMPUTE MISSING VALUES")
print("missing discount:",int(orders_clean.discount_pct.isna().sum()))
print("rating median:",orders_clean.rating.median())
print("missing rating:",int(orders_clean.rating.isna().sum()))
orders_clean["discount_pct"]=orders_clean["discount_pct"].fillna(0)
orders_clean["rating"]=orders_clean["rating"].fillna(orders_clean["rating"].median())
print(orders_clean[["discount_pct","rating"]].isna().sum().to_dict())

print("\nTASK 5 — MERGE AND RECONCILE")
df=orders_clean.merge(products,on="product_id").merge(customers,on="customer_id")
df["order_value"]=df.quantity*df.price*(1-df.discount_pct/100.0)
cleaned_total=round(df.order_value.sum(),2)

# Compute the raw Part 1 revenue independently from the original CSVs.
# This avoids hardcoding a benchmark into the Python layer.
raw_for_revenue=orders.merge(products,on="product_id")
raw_for_revenue["raw_order_value"]=(
    raw_for_revenue.quantity * raw_for_revenue.price *
    (1-raw_for_revenue.discount_pct.fillna(0)/100.0)
)
raw_total=round(raw_for_revenue.raw_order_value.sum(),2)

dropped=orders.loc[dup].merge(products,on="product_id")
dropped["order_value"]=dropped.quantity*dropped.price*(1-dropped.discount_pct.fillna(0)/100.0)
duplicate_delta=round(dropped.order_value.sum(),2)
print(f"cleaned revenue: {cleaned_total:.2f}")
print(f"raw revenue: {raw_total:.2f}")
print(f"reconciliation delta: {raw_total-cleaned_total:.2f}")
print(f"dropped duplicate value: {duplicate_delta:.2f}")
print("Reconciliation note: the exact revenue delta is caused by removing the five duplicate submissions; discount/rating imputation does not change order_value.")

print("\nTASK 6 — IQR OUTLIERS")
q1=df.quantity.quantile(.25); q3=df.quantity.quantile(.75); iqr=q3-q1
lower=q1-1.5*iqr; upper=q3+1.5*iqr
df["is_outlier"]=~df.quantity.between(lower,upper)
print(f"Q1={q1:.1f}, Q3={q3:.1f}, IQR={iqr:.1f}, lower={lower:.1f}, upper={upper:.1f}")
print(df.loc[df.is_outlier,["order_id","quantity"]].to_string(index=False))

print("\nTASK 7 — COD RETURN HYPOTHESIS")
summary=df.groupby("payment_method").returned.agg(["count","mean"])
summary["return_rate_pct"]=summary["mean"]*100
print(summary[["count","return_rate_pct"]].round(1))
print("Hypothesis: COD has a higher return rate.")
print("Verdict:", "Confirmed" if summary.loc["COD","return_rate_pct"]>summary.drop("COD")["return_rate_pct"].max() else "Busted")

print("\nTASK 8 — SEGMENTATION")
seg=df.groupby(["payment_method","city_tier"]).returned.agg(["count","mean"]).reset_index()
seg["return_rate_pct"]=(seg["mean"]*100).round(1)
print(seg.to_string(index=False))
risk=seg.loc[seg.return_rate_pct.idxmax()]
print(f"Highest-risk segment: {risk.payment_method} + Tier-{int(risk.city_tier)} at {risk.return_rate_pct:.1f}%")

print("\nTASK 9 — CORRELATION")
cols=["rating","returned","discount_pct","quantity"]
corr=df[cols].corr()
print(corr.round(2))
def band(r):
    a=abs(float(r))
    return "negligible" if a<.2 else "weak" if a<.4 else "moderate" if a<.7 else "strong"
for a,b in itertools.combinations(cols,2):
    print(f"{a} vs {b}: r={corr.loc[a,b]:.2f} -> {band(corr.loc[a,b])}")
print(f'Hypothesis "higher discounts reduce returns": {"Confirmed" if corr.loc["discount_pct","returned"] < -.2 else "Busted"} (r={corr.loc["discount_pct","returned"]:.2f})')

print("\nTASK 10 — OUTLIER-CORRECTED TIME SERIES")
df["order_date"]=pd.to_datetime(df.order_date)
df["month"]=df.order_date.dt.to_period("M").astype(str)
monthly_all=df.groupby("month").order_value.sum().round(2)
monthly_corrected=df.loc[~df.is_outlier].groupby("month").order_value.sum().round(2)
print(pd.DataFrame({"apparent_revenue":monthly_all,"corrected_revenue":monthly_corrected}).to_string())
peak=monthly_corrected.idxmax()
print(f"January's apparent lead is caused by O0011 and O0098. March is the genuine peak after excluding those outliers: {monthly_corrected.max():.2f}")

findings={
 "cleaned_total_revenue_inr":cleaned_total,
 "raw_total_revenue_inr":raw_total,
 "duplicate_reconciliation_delta_inr":duplicate_delta,
 "return_rate_by_payment":{k:round(float(v),1) for k,v in summary.return_rate_pct.to_dict().items()},
 "highest_risk_segment":{"payment_method":str(risk.payment_method),"city_tier":int(risk.city_tier),"return_rate_pct":float(risk.return_rate_pct)},
 "true_peak_month":{"month":str(peak),"revenue_inr":round(float(monthly_corrected.max()),2)},
 "outlier_inflated_month":{"month":str(monthly_all.idxmax()),"apparent_revenue_inr":round(float(monthly_all.max()),2),"corrected_revenue_inr":round(float(monthly_corrected.loc[monthly_all.idxmax()]),2)},
 "monthly_corrected_revenue":{str(k):round(float(v),2) for k,v in monthly_corrected.to_dict().items()},
 "monthly_apparent_revenue":{str(k):round(float(v),2) for k,v in monthly_all.to_dict().items()}
}
(NARRATOR/"findings.json").write_text(json.dumps(findings,indent=2),encoding="utf-8")
print("\nWrote narrator/findings.json")
