from openai import OpenAI
import base64
import mimetypes
from pathlib import Path

from PIL import Image

client = OpenAI()


def encode_image(path: str | Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def split_image(image_path: str | Path) -> list[Path]:
    image_path = Path(image_path)
    img = Image.open(image_path)
    w, h = img.size

    coords = [
        (0, 0, w // 2, h // 2),
        (w // 2, 0, w, h // 2),
        (0, h // 2, w // 2, h),
        (w // 2, h // 2, w, h),
    ]

    out_dir = image_path.parent
    stem = image_path.stem
    paths: list[Path] = []

    for i, (x1, y1, x2, y2) in enumerate(coords):
        part = img.crop((x1, y1, x2, y2))
        path = out_dir / f"{stem}_part_{i}.jpg"
        part.save(path, format="JPEG")
        paths.append(path)

    return paths


def analyze(image_path: str | Path, text: str) -> str:
    image_path = Path(image_path)
    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"

    base64_image = encode_image(image_path)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """
Sen bir elektronik tamir ustasısın.

Kurallar:
- Genel konuşma YASAK
- Maksimum 3 ihtimal ver
- Her ihtimalde spesifik bölge söyle
- Görselde gördüğünü açıkça referans ver
- Emin değilsen açıkça söyle
""".strip(),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                        },
                    },
                ],
            },
        ],
        max_tokens=300,
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    image = "test.jpg"

    print("\n--- GENEL ANALİZ ---\n")
    general = analyze(image, "Bu kart çalışmıyor, spesifik arıza noktalarını söyle")
    print(general)

    print("\n--- PARÇA ANALİZLERİ ---\n")
    parts = split_image(image)

    all_parts: list[str] = []
    for i, part in enumerate(parts):
        result = analyze(part, f"Bu kartın {i}. bölgesi. Sorunlu yer var mı?")
        print(f"\n[PARÇA {i}]")
        print(result)
        all_parts.append(result)

    print("\n--- BİRLEŞİK SONUÇ ---\n")

    combined_input = general + "\n\n" + "\n\n".join(all_parts)

    final = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """
Tüm analizleri birleştir.
En kritik 3 arıza ihtimalini ver.
Her biri için net bölge belirt.
""".strip(),
            },
            {
                "role": "user",
                "content": combined_input,
            },
        ],
        max_tokens=400,
    )

    print(final.choices[0].message.content)
