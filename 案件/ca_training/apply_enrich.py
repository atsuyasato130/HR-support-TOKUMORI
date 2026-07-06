#!/usr/bin/env python3
"""
ワークフロー(deepen-training-decks)の結果JSONを
 data_deck_enrich.json（スライド深掘り）と data_tests.json（難化テスト）へマージする。
使い方: python3 apply_enrich.py <wave_result.json>
wave_result.json = {"enrich": {...}, "tests": {...}, "count": N}
"""
import json
import os
import sys

BASE = "/Users/atsuyasato/Claude AI"


def load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    if len(sys.argv) < 2:
        print("usage: apply_enrich.py <wave_result.json>")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        wave = json.load(f)

    enr = load(os.path.join(BASE, "data_deck_enrich.json"))
    tst = load(os.path.join(BASE, "data_tests.json"))

    w_enr = wave.get("enrich", {})
    w_tst = wave.get("tests", {})
    enr.update(w_enr)
    tst.update(w_tst)

    with open(os.path.join(BASE, "data_deck_enrich.json"), "w", encoding="utf-8") as f:
        json.dump(enr, f, ensure_ascii=False, indent=1)
    with open(os.path.join(BASE, "data_tests.json"), "w", encoding="utf-8") as f:
        json.dump(tst, f, ensure_ascii=False, indent=1)

    print("merged enrich mids:", sorted(w_enr.keys()))
    print("merged tests  mids:", sorted(w_tst.keys()))
    print("total enrich:", len(enr), "total tests:", len(tst))


if __name__ == "__main__":
    main()
