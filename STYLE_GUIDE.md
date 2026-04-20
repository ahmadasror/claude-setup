# Slides — Global Style Guide

**Scope:** Semua deck HTML di folder `slides/` (per-deck subfolder, e.g. `deck-a/`, `deck-b/`)
**Last Updated:** 2026-04-15

> Dokumen ini adalah single source of truth untuk visual design system dan HTML/CSS patterns yang dipakai di semua slide deck workspace ini. Deck-specific content rules ada di masing-masing subfolder.

---

## 1. Palette

| CSS Token | Hex | Makna / Penggunaan |
|---|---|---|
| `--accent` | `#F58220` | Brand orange — primary product, happy path, action emphasis |
| `--accent-dark` | `#D57012` | Header border, chip label, Gantt bar text |
| `--brown` | `#7C6A55` | Frontend layer, alt-path node, status-deck header |
| `--info` | `#0369a1` | Satellite services, loop path, partner API, Gantt blue bars |
| `--success` | `#16a34a` | Done/closed state, Go Live, Dev ready |
| `--danger` | `#dc2626` | Error/overdue, critical state, Red indicator |
| `--yellow` | `#D9A400` | Benchmark chip, In Progress banner, Yellow indicator |
| `--text` | `#0F172A` | Body text utama |
| `--text-muted` | `#475569` | Secondary text, catatan |
| `--text-light` | `#94A3B8` | Tertiary, disabled |
| `--primary` | `#F9F8F4` | Slide background alt row |
| `--secondary` | `#FFF3EB` | Highlight background (current phase, active) |
| `--surface` | `#FFFFFF` | Card / slide surface |
| `--border` | `rgba(124,106,85,0.12)` | Divider, card border |
| `#7C3AED` | purple | Alternatif path khusus (e.g. accelerated/alt flow) |
| `#F0F9FF` | light blue | External system box fill (dashed border) |

---

## 2. Typography

| Elemen | Size | Weight | Notes |
|---|---|---|---|
| Deck title (cover H1) | 3.2–4rem | 800 | letter-spacing -2px |
| Action title | 1.1rem | 700 | Max 2 baris, BLUF style |
| Section tag | 0.68rem | 700 | Uppercase, letter-spacing 1px |
| Slide H2 | 1.4rem | 700 | |
| Slide H3 | 0.72rem | 700 | Uppercase, accent-dark |
| Body / list | 0.82–0.85rem | 400–500 | line-height 1.5–1.55 |
| Table cell | 0.7–0.78rem | 400–600 | |
| SVG node label | 11–13px | 700 | font-family Inter |
| SVG sub-text | 8–9px | 500 | fill text-muted |
| Chip / badge | 0.54–0.70rem | 700 | Uppercase, border-radius 8–14px |

**Font stack:** `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`
**Source:** Google Fonts — `Inter:wght@400;500;600;700;800`

---

## 3. Layout & Deck Spec

| Parameter | Value |
|---|---|
| Deck size | **1280 × 720** (16:9) |
| Best view | Laptop / MacBook Pro |
| Scaling | `scaleDeck()` — `Math.min(vw/1280, vh/720)` |
| Slide padding | 36px top · 56px sides · 48px bottom |
| Slide transition | opacity + translateX 0.4s ease |
| Navigation | Arrow keys · Space · PageUp/Down · Home/End · Swipe · Click zones (kiri 25% back, kanan 25% forward) |

---

## 4. Komponen — Patterns

### Cover Slide (`.cover-slide`)
- Full-bleed gradient: `linear-gradient(135deg, var(--primary) 0%, var(--secondary) 60%, #fff 100%)`
- Watermark teks raksasa di belakang (font-size 22rem, opacity 0.06)
- Structure: overline → H1 → subtitle → [status chips opsional] → meta grid 4 kolom bawah
- **Thank You variant:** judul besar + prepared-by info + status badge + meta grid ringkas; reuse `.cover-slide`

### Slide Header (McKinsey style)
- Border-bottom 3px `var(--accent)`
- Kiri: `.action-title` — satu kalimat BLUF yang menjawab "so what"
- Kanan: `.section-tag` — uppercase label konteks
- **Rule:** action title max 2 baris; hindari passive voice

### Chip / Badge
```css
/* Status chip */
padding: 2px 8px; border-radius: 10px; font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
/* Verdict badge */
padding: 2px 6px; border-radius: 4px; font-size: 0.68rem; font-weight: 700;
```

### Comparison Table (`.compare-table`)
- Verdict badges: `.vb-ok` (green) · `.vb-warn` (yellow/orange) · `.vb-bad` (red) · `.vb-na` (grey)
- Tone proposal: gunakan "Diusulkan" / "Tidak direkomendasikan", bukan "Terpilih" / "Tidak fit"

### SVG Diagrams — Rules
- **viewBox:** sesuaikan konten; umumnya `0 0 [width] [height]`
- **Connector:** elbow / polyline only — **tidak boleh diagonal**
- **Arrowhead:** `<polygon>` dengan 3 titik, arah sesuai aliran
- **External system:** dashed border (`stroke-dasharray="5,3"`) + lighter fill
- **Legend:** HTML flex row di **bawah** SVG (bukan di dalam SVG) supaya tidak tumpuk

### Lifecycle SVG (example: product lifecycle deck)
- viewBox `0 0 1100 160`
- Warna branch: orange=happy path · blue dashed=renewal · purple dashed=accelerated · red=overdue · brown=alternative/partner

### Architecture SVG
- viewBox `0 0 720 470`
- Layer: Frontend (brown) → Core (orange fill) → Satellite (blue outline) → Downstream (grey)
- Connector warna mengikuti target layer

### Phase Tracker
```
.phase-step.done    → border hijau, bg rgba(green,0.05), ps-num hijau
.phase-step.current → border orange, bg secondary, box-shadow orange
.phase-step.future  → border dashed, opacity 0.7
```
- Grid 4 kolom; phase-now banner: yellow border, chip badge

### Gantt Chart SVG
- viewBox `0 0 1060 168`
- Label col: 168px · Month cols: 225px each · Target col: 217px
- Bar: height 18px, rx 4, row height 27px
- Alternating row background: `#F9F8F4`
- Milestone: `<polygon>` diamond + dashed guide line
- Critical path: bar merah (`--danger`) + warning badge (stroke rect)

### Project Indicator (status-update decks)
| Warna | Class | Makna |
|---|---|---|
| Green | indicator-green | On-track |
| Yellow | indicator-yellow | At-risk |
| Red | indicator-red | Off-track / butuh keputusan |

---

## 5. Aturan Konten (cross-deck)

- **Tone proposal:** gunakan "diusulkan", "direkomendasikan" untuk hal yang belum final
- **No jargon teknis** tanpa terjemahan bisnis di slide yang audience-nya management
- **No emoji** kecuali diminta eksplisit
- **Angka konkret** — hindari "beberapa", "banyak"
- **Classification watermark:** `DOKUMEN INTERNAL` atau `DOKUMEN RAHASIA` di setiap slide

### Yang WAJIB di-hide dari Management (status-update decks)
- Epic ID (E-NNN), ADR ID, Jira ticket ID (ABC-NNN)
- Story point, sprint number, velocity
- Nama modul teknis internal → pakai terjemahan bisnis

---

## 6. Deck Index

> Daftar deck aktif di-maintain per-workspace. Template kolom:

| Deck | Folder | Audience | Source of Truth | Live URL |
|---|---|---|---|---|
| `<deck name>` | `slides/<slug>/` | `<audience>` | `<source file>` | `<url>` |

> Deck-specific content rules hidup di masing-masing subfolder (`slides/<slug>/content.md` atau `style-guide.md`).
