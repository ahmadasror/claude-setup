---
name: diskusi
description: "Memandu diskusi PRD topik-per-topik dengan tracking pemahaman terpisah. Use saat user invoke /diskusi prd <module> — agent menyajikan satu topik, mengajukan pertanyaan konfirmasi, lalu update file comprehension-{module}.md. Cocok untuk member tim yang kesulitan baca PRD utuh."
---

# /diskusi — PRD Comprehension Helper

Helper untuk membahas PRD satu topik per sesi, dengan tracker pemahaman tim member yang persistent antar sesi.

## Invocation

```
/diskusi prd <module>          # auto-pick topik berikutnya
/diskusi prd <module> <topik>  # diskusi topik spesifik
/diskusi status <module>       # tampilkan progress saja, tanpa diskusi
```

Contoh: `/diskusi prd VA`, `/diskusi prd payroll inquiry`, `/diskusi status VA`.

## Flow

### Step 1 — Load context

1. Resolve PRD folder: cari `docs/prd/{module}/` (case-insensitive). Kalau tidak ada, tampilkan daftar module yang ada di `docs/prd/` dan minta user pilih.
2. Baca `docs/prd/{module}/index.md` untuk daftar workflow/topik.
3. Baca semua `docs/prd/{module}/*.md` untuk dapatkan judul topik (heading H1/H2 utama).
4. Baca tracker: `docs/prd/{module}/comprehension.md`. Kalau belum ada, **jangan bikin dulu** — bikin nanti setelah sesi pertama selesai.

### Step 2 — Pilih topik

Prioritas auto-pick:
1. Topik dengan `status: belum_dibahas`
2. Topik dengan `confidence < 2`
3. Topik dengan `open_questions` belum closed
4. Topik dengan `last_discussed` paling lama (refresh)

Kalau user kasih nama topik eksplisit, pakai itu (fuzzy match nama file/heading).

Kalau user invoke `/diskusi status <module>`, skip ke Step 6.

### Step 3 — Sajikan topik (BAHASA SEDERHANA)

Format presentasi (jangan copy-paste PRD mentah):

```
📖 Topik: <nama topik>
   (X dari Y topik di PRD <module>)

🎯 Tujuan: <1 kalimat — kenapa fitur ini ada>

👤 Aktor: <siapa yang pakai>

🔄 Flow utama:
   1. <step 1 dalam bahasa awam>
   2. <step 2>
   3. ...

📏 Aturan kunci:
   - <business rule penting 1>
   - <business rule penting 2>

⚠️  Edge case yang perlu diperhatikan:
   - <case 1>
```

**JANGAN tampilkan**: endpoint, request/response shape, SQL, kode error teknis, struktur DB. Itu domain `docs/fr/` dan `docs/architecture/`, bukan PRD.

Kalau topik panjang (>500 kata di PRD), tetap rangkum jadi format di atas. Tujuannya tim member paham *konsep*, bukan hafal detail.

### Step 4 — Pertanyaan konfirmasi

Ajukan **2-3 pertanyaan** untuk cek pemahaman. Jenis pertanyaan:

1. **Skenario** — "Kalau user X di kondisi Y, apa yang seharusnya terjadi?"
2. **Trade-off** — "Kenapa kita pilih cara A, bukan B?"
3. **Boundary** — "Apa yang TIDAK ditangani fitur ini?"

Hindari pertanyaan factual recall ("apa nama endpoint-nya?"). Tujuannya cek *paham*, bukan *hafal*.

Tunggu jawaban user. Setelah dijawab:
- Kalau benar/cukup → konfirmasi singkat, lanjut pertanyaan berikutnya
- Kalau ragu/salah → klarifikasi dengan referensi ke bagian PRD relevan, JANGAN langsung lanjut
- Kalau user bilang "tidak tahu" / "skip" → catat sebagai `open_question`

### Step 5 — Update tracker

Setelah semua pertanyaan dijawab (atau user explicitly close sesi), update `docs/prd/{module}/comprehension.md`.

**Format file** (Markdown dengan frontmatter YAML per topik):

```markdown
# Comprehension Tracker — PRD <Module>

> Auto-maintained by `/diskusi`. Boleh diedit manual — tetap valid asal struktur per-topik tetap.

**Last updated**: 2026-05-05
**Overall progress**: 3/8 topik dibahas, avg confidence 2.3/3

---

## <Nama Topik 1>

- **status**: didiskusikan          # belum_dibahas | dibaca | didiskusikan
- **confidence**: 3                  # 1=ragu, 2=paham dasar, 3=paham + bisa jelaskan ke orang lain
- **last_discussed**: 2026-05-05
- **discussant**: <nama tim member kalau user sebutkan, atau "-">
- **open_questions**:
  - (kosong kalau tidak ada)
- **notes**:
  - Sempat bingung soal X, sudah diklarifikasi.

---

## <Nama Topik 2>

- **status**: belum_dibahas
- **confidence**: -
- **last_discussed**: -
- **open_questions**: -
- **notes**: -
```

Aturan update:
- **status**: set `didiskusikan` kalau user jawab >=1 pertanyaan. Set `dibaca` kalau user cuma minta dipresentasikan tanpa diskusi.
- **confidence**: nilai dari kualitas jawaban (1=banyak salah/ragu, 2=paham flow tapi lemah di edge case, 3=jawab benar termasuk skenario tricky).
- **open_questions**: append, jangan overwrite. Hapus hanya kalau user explicit bilang "sudah jelas".
- **notes**: ringkas (<2 baris per sesi). Jangan transcript lengkap.

### Step 6 — Tutup sesi & tampilkan progress

```
✅ Sesi selesai untuk topik: <nama>
   Confidence: 2/3 — paham flow utama, masih ragu di edge case expired VA.
   Open question: 1 (akan dibahas di sesi berikutnya)

📊 Progress PRD <module>:
   ▓▓▓░░░░░  3/8 topik (37%)
   Avg confidence: 2.3/3

➡️  Topik berikutnya yang disarankan: <nama topik>
   Invoke: /diskusi prd <module>
```

## Re-invocation behavior

Skill harus **idempotent dan resumable**:
- Kalau dipanggil lagi pada module yang sama → otomatis lanjut dari topik berikutnya berdasarkan prioritas Step 2.
- Kalau tracker sudah lengkap (semua topik confidence >= 2, no open questions) → kasih tau user "PRD ini sudah cukup dipahami" dan tawarkan refresh sesi (re-discuss topik tertua).

## Boundaries

- **Jangan** bikin file baru selain `comprehension.md` di folder PRD.
- **Jangan** edit PRD itu sendiri. Skill ini read-only terhadap `docs/prd/{module}/*.md` (kecuali `comprehension.md`).
- **Jangan** sentuh `docs/fr/`, `docs/architecture/`, atau `docs/test-scenarios/`.
- Kalau PRD update (file mtime > `last_discussed` topik) → flag topik itu `status: stale` dan saran re-discuss, jangan auto-reset.

## Anti-pattern yang harus dihindari

- ❌ Dump seluruh PRD ke chat — defeats the purpose.
- ❌ Quiz hafalan ("apa kode error-nya?") — itu tugas /tester-explorer, bukan diskusi PRD.
- ❌ Auto-mark topik `didiskusikan` tanpa benar-benar nanya — tracker harus jujur.
- ❌ Bikin `comprehension.md` di root project — selalu di `docs/prd/{module}/`.
