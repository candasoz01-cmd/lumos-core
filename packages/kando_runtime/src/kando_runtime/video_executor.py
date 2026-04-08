def run(task_ctx):
    """Gerçek video dosyası üretilmedikçe sahte URL veya örnek medya dönülmez."""
    _ = task_ctx  # İleride gerçek üretim bağlandığında kullanılacak.
    return {
        "status": "done",
        "output": {
            "type": "text",
            "value": (
                "Gerçek bir video dosyası üretilmedi: "
                "video oluşturma bu ortamda bağlı değil veya henüz çalıştırılmadı. "
                "Sahte veya örnek video adresi gösterilmiyor."
            ),
        },
    }
