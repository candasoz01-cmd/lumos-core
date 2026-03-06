"""Initialize device identity. Run: python -m lumos_core.scripts.init_identity"""
from getpass import getpass

from lumos_core.security.identity import DeviceIdentity
from lumos_core.security.keystore import FileKeyStore


def main() -> None:
    ks = FileKeyStore(base_dir="src/.lumos")
    if not ks.is_initialized():
        print("Keystore yok. Önce: python -m lumos_core.scripts.init_keystore")
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
