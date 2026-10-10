from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; OUT=ROOT/"visualizations"; OUT.mkdir(exist_ok=True)

orders=pd.read_csv(DATA/"orders.csv")
products=pd.read_csv(DATA/"products.csv")
customers=pd.read_csv(DATA/"customers.csv")
orders["payment_method"]=orders.payment_method.str.upper().str.strip()
key=["customer_id","product_id","order_date","quantity","discount_pct","payment_method","rating","returned"]
orders=orders.loc[~orders.duplicated(subset=key,keep="first")].copy()
orders["discount_pct"]=orders.discount_pct.fillna(0)
orders["rating"]=orders.rating.fillna(orders.rating.median())
df=orders.merge(products,on="product_id").merge(customers,on="customer_id")
df["order_value"]=df.quantity*df.price*(1-df.discount_pct/100)

rates=df.groupby("payment_method").returned.mean().mul(100).sort_values(ascending=False)
fig,ax=plt.subplots(figsize=(8,5))
bars=ax.bar(rates.index,rates.values)
ax.set_ylabel("Return rate (%)"); ax.set_xlabel("Payment method")
ax.set_title(f"COD Returns at {rates['COD']:.1f}% — {rates['COD']/rates['CARD']:.1f}x Card")
for bar,val in zip(bars,rates.values):
    ax.text(bar.get_x()+bar.get_width()/2,val+0.8,f"{val:.1f}%",ha="center")
fig.tight_layout(); fig.savefig(OUT/"return_rate_by_payment.png",dpi=150); plt.close(fig)

df["order_date"]=pd.to_datetime(df.order_date)
df["month"]=df.order_date.dt.to_period("M").astype(str)
q1=df.quantity.quantile(.25); q3=df.quantity.quantile(.75); iqr=q3-q1
df["is_outlier"]=~df.quantity.between(q1-1.5*iqr,q3+1.5*iqr)
monthly=df.loc[~df.is_outlier].groupby("month").order_value.sum()
peak=monthly.idxmax()
fig,ax=plt.subplots(figsize=(9,5))
ax.plot(monthly.index,monthly.values,marker="o")
ax.set_xlabel("Month"); ax.set_ylabel("Corrected revenue (INR)")
ax.set_title(f"Outlier-Corrected Monthly Revenue — True Peak: {peak}")
ax.tick_params(axis="x",rotation=45)
fig.tight_layout(); fig.savefig(OUT/"monthly_revenue_trend.png",dpi=150); plt.close(fig)
print("Created both required PNGs.")
