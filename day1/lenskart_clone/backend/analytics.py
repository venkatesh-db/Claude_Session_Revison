import pandas as pd


def build_dataframe(products):
    return pd.DataFrame(products)


def summarize(products):
    df = build_dataframe(products)

    if df.empty:
        return {"count": 0}

    brand_breakdown = (
        df.groupby("brand")
        .agg(
            count=("id", "count"),
            avg_price=("price", "mean"),
            avg_rating=("rating", "mean"),
        )
        .round(2)
        .reset_index()
        .to_dict(orient="records")
    )

    price_bins = [0, 1500, 2000, 2500, float("inf")]
    price_labels = ["<1500", "1500-2000", "2000-2500", "2500+"]
    df["price_band"] = pd.cut(df["price"], bins=price_bins, labels=price_labels, right=False)
    price_distribution = (
        df["price_band"].value_counts().sort_index().to_dict()
    )

    top_rated = (
        df.sort_values("rating", ascending=False)
        .head(3)[["id", "brand", "name", "rating"]]
        .to_dict(orient="records")
    )

    best_discount = (
        df.sort_values("discount_pct", ascending=False)
        .head(3)[["id", "brand", "name", "discount_pct"]]
        .to_dict(orient="records")
    )

    return {
        "count": int(len(df)),
        "price": {
            "min": float(df["price"].min()),
            "max": float(df["price"].max()),
            "mean": round(float(df["price"].mean()), 2),
            "median": float(df["price"].median()),
        },
        "discount_pct": {
            "min": float(df["discount_pct"].min()),
            "max": float(df["discount_pct"].max()),
            "mean": round(float(df["discount_pct"].mean()), 2),
        },
        "rating": {
            "min": float(df["rating"].min()),
            "max": float(df["rating"].max()),
            "mean": round(float(df["rating"].mean()), 2),
        },
        "brand_breakdown": brand_breakdown,
        "price_distribution": {str(k): int(v) for k, v in price_distribution.items()},
        "top_rated": top_rated,
        "best_discount": best_discount,
    }
