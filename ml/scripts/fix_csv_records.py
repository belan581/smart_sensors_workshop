"""
Script to complete missing activity labels in raw CSV files
"""

import pandas as pd


def fix_drinking_csv():
    """Fix drinking_2.csv by adding missing activity labels"""
    df = pd.read_csv("data/raw/drinking_2.csv")
    # Fill missing activity values with 'drinking'
    df["activity"] = df["activity"].fillna("drinking")
    # Also handle rows where activity might be empty string
    df.loc[df["activity"] == "", "activity"] = "drinking"
    df.to_csv("data/raw/drinking_2.csv", index=False)
    print(f"✓ Fixed drinking_2.csv: {len(df)} records")


def fix_driving_csv():
    """Fix driving_2.csv by adding activity column"""
    df = pd.read_csv("data/raw/driving_2.csv")
    df["activity"] = "driving"
    df.to_csv("data/raw/driving_2.csv", index=False)
    print(f"✓ Fixed driving_2.csv: {len(df)} records")


def fix_throwing_csv():
    """Fix throwing_2.csv by adding activity column"""
    df = pd.read_csv("data/raw/throwing_2.csv")
    df["activity"] = "throwing"
    df.to_csv("data/raw/throwing_2.csv", index=False)
    print(f"✓ Fixed throwing_2.csv: {len(df)} records")


if __name__ == "__main__":
    print("Completing CSV records...")
    fix_drinking_csv()
    fix_driving_csv()
    fix_throwing_csv()
    print("\n✓ All records completed successfully!")
