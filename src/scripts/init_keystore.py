from getpass import getpass
from security.keystore import FileKeyStore

def main():
    ks = FileKeyStore(base_dir="src/.lumos")
    if ks.is_initialized():
        print("Keystore zaten var. (OK)")
        return
    p1 = getpass("Lumos passphrase belirle: ")
    p2 = getpass("Tekrar: ")
    if p1 != p2 or not p1:
        print("Hata: passphrase uyuşmuyor ya da boş.")
        return
    ks.init(p1)
    print("OK: Keystore oluşturuldu (src/.lumos/keystore.json)")

if __name__ == "__main__":
    main()
