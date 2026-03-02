from getpass import getpass

from src.security.keystore import FileKeyStore
from src.security.identity import DeviceIdentity

def main():
    ks = FileKeyStore(base_dir="src/.lumos")
    if not ks.is_initialized():
        print("Keystore yok. Önce: python -m src.scripts.init_keystore")
        return

    p = getpass("Passphrase: ")
    try:
        root_key = ks.load_root_key(p)
    except Exception:
        print("Hata: passphrase yanlış ya da keystore bozuk.")
        return

    ident = DeviceIdentity(base_dir="src/.lumos")
    if ident.is_initialized():
        print("Identity zaten var. (OK)")
        return

    ident.init(root_key)
    print("OK: Identity oluşturuldu (src/.lumos/identity.json)")

if __name__ == "__main__":
    main()
