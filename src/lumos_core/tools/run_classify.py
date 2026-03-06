import json
import sys
from collections import Counter
from lumos_core.tools.file_classifier import scan_folder

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python -m lumos_core.tools.run_classify <klasor_yolu>")
        sys.exit(1)

    folder = sys.argv[1]
    results = scan_folder(folder)

    counts = Counter([r.category for r in results])
    print("Kategori özeti:")
    for k, v in counts.most_common():
        print(f"- {k}: {v}")

    print("\nİlk 30 örnek:")
    for item in results[:30]:
        print(f"{item.category}\t{item.path}")

    out = [{"category": r.category, "path": r.path} for r in results]
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\nToplam: {len(results)} dosya (filtreli). output.json yazıldı.")

if __name__ == "__main__":
    main()
