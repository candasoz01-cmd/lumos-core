# GitHub: default branch ve branch koruma

**Default branch nerede:** Repo **Settings** → **General** → en altta **Default branch** (Branches sayfası değil). Dropdown’dan varsayılan branch’i (örn. `kando/main` veya `main`) seçip **Update** ile kaydedin.

**Silme engelleme:** **Settings** → **Branches** → **Branch protection rules** → kural ekleyin veya düzenleyin; **Allow deletions** kapalı olsun. Böylece korumalı branch’ler silinmez. (Kural yoksa “Add rule” ile oluşturun.)

**“Not enforced” uyarısı:** Private repo’da organizasyon/plan ayarına göre bazı korumalar “Not enforced” gösterebilir. Bu durumda silmeyi engellemek için yerel disiplin ve PR akışı kullanın: default/main branch’e doğrudan force-push veya silme yapmayın; değişiklikleri PR ile getirip merge edin.
