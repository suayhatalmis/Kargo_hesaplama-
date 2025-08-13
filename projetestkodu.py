#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 11 10:27:05 2025

@author: suayhatalmis
"""

import sys
import pandas as pd

# =========================
# 1) İL MESAFE TABLOSUNU OKU
#   - Sütun başlıkları (iller): 2. satır, 3. sütundan itibaren (C2→)
#   - Satır başlıkları (iller): 3. satırdan itibaren, 2. sütun (B3↓)
#   - Mesafeler: 3. satır 3. sütundan itibaren (C3→, 3. satır ↓)
# =========================
ILMESAFE_DOSYA = "ilmesafe.xlsx"

df = pd.read_excel(ILMESAFE_DOSYA, header=None)  # başlıkları otomatik alma
iller_sutun = df.iloc[1, 2:].astype(str).str.strip().str.upper().values   # C2..→
iller_satir = df.iloc[2:, 1].astype(str).str.strip().str.upper().values   # B3..↓
mesafe_df = df.iloc[2:, 2:]                                               # C3..→, 3. satır↓
mesafe_df.index = iller_satir
mesafe_df.columns = iller_sutun
mesafe_df = mesafe_df.apply(pd.to_numeric, errors='coerce').fillna(0)

def mesafe_bul(kaynak: str, hedef: str):
    kaynak = str(kaynak).strip().upper()
    hedef  = str(hedef).strip().upper()
    try:
        return mesafe_df.loc[kaynak, hedef]
    except KeyError:
        return None

def hat_belirle(mesafe: float) -> str:
    if mesafe < 1:
        return "Local Line"
    elif mesafe <= 200:
        return "Near Line"
    elif mesafe <= 600:
        return "Short Line"
    elif mesafe <= 1000:
        return "Middle Line"
    else:
        return "Long Line"

# =========================
# 2) GİRDİLER
# =========================
nereden = input("Nereden taşıma yapılacak?: ")
nereye  = input("Nereye taşıma yapılacak?: ")

mesafe = mesafe_bul(nereden, nereye)
if mesafe is None or pd.isna(mesafe):
    print("❌ Mesafe bulunamadı! Lütfen il adlarını kontrol edin.")
    sys.exit(0)

hat = hat_belirle(mesafe)
print(f"{nereden} → {nereye} mesafe: {mesafe} km, Hat türü: {hat}")

tasima_turu = input("Taşıma türü (Dosya / Paket/Koli): ").strip().lower()

# Firma → fiyat tablosu dosyası
FIYAT_DOSYALAR = {
    "Yurtiçi Kargo": "yk_for_kg.xlsx",
    "Aras Kargo"   : "Aras_for_kg.xlsx",
    "DHL"          : "DHL_for_kg.xlsx",
    "Sürat Kargo"  : "Sürat_for_kg.xlsx",
}

# Telefon/SMS ek hizmet dosyaları
EK_HIZMET_DOSYALAR = {
    "Yurtiçi Kargo": "call_service_yk.xlsx",
    "Aras Kargo"   : "call_service_a.xlsx",
    "DHL"          : "info_dhl.xlsx",
    "Sürat Kargo"  : "call_service_s.xlsx",
}

# =========================
# 3) TAŞIMA DEĞERİ (KG/DESİ) HESABI
#   - Paket/Koli: çoklu kargo (max 5), her kargo için ölçüler alınıp
#                 toplam desi ve toplam ağırlık hesaplanır.
#   - Dosya: kg/desi = 0
# =========================
if tasima_turu in ["paket", "koli", "paket/koli"]:
    try:
        kargo_sayisi = int(input("Kaç kargo göndereceksiniz? (max 5): "))
    except:
        print("❌ Geçersiz sayı!")
        sys.exit(0)

    if not (1 <= kargo_sayisi <= 5):
        print("❌ Geçersiz sayı! 1 ile 5 arasında olmalı.")
        sys.exit(0)

    toplam_desi = 0.0
    toplam_agirlik = 0.0

    for i in range(kargo_sayisi):
        print(f"\n📦 {i+1}. Kargo bilgileri:")
        en = float(input("En (cm): "))
        boy = float(input("Boy (cm): "))
        yukseklik = float(input("Yükseklik (cm): "))
        agirlik = float(input("Ağırlık (kg): "))

        desi = en * boy * yukseklik / 3000
        toplam_desi += desi
        toplam_agirlik += agirlik

    tasima_degeri = int(max(toplam_desi, toplam_agirlik))
    deger_turu = "ağırlık" if toplam_agirlik >= toplam_desi else "desi"

    print(f"\n📊 Toplam Desi: {toplam_desi:.2f}")
    print(f"📊 Toplam Ağırlık: {toplam_agirlik:.2f}")
    print(f"✅ Taşıma değeri: {tasima_degeri} ({deger_turu})")

elif tasima_turu == "dosya":
    tasima_degeri = 0
    deger_turu = "ağırlık"  # dosya için 0 kg kabul edip posta vergisi kuralı bu şekilde işler
else:
    print("❌ Geçersiz taşıma türü!")
    sys.exit(0)

# =========================
# 4) STANDART TAŞIMA BEDELİ (EK HİZMET VE VERGİ ÖNCESİ)
#   - Fiyat tablosundan hat sütunu ve kg/desi satırı ile çekilir.
#   - Ağır taşıma kuralları (firma bazlı) bu aşamada eklenir.
# =========================
def oku_fiyat(dosya):
    dfp = pd.read_excel(dosya)
    dfp = dfp.dropna(axis=1, how="all").dropna(axis=0, how="all")
    dfp.columns = dfp.columns.astype(str).str.strip().str.lower()
    return dfp

def standard_bedel_bul(firma, hat_adi, kg_desi_deger, deger_turu_local):
    """
    Tablo fiyatı + ağır taşıma varsa ekler → 'standart taşıma bedeli' döner.
    """
    dfp = oku_fiyat(FIYAT_DOSYALAR[firma])
    hat_col = hat_adi.strip().lower()
    if "kg/desi" not in dfp.columns:
        raise KeyError(f"{firma} tablosunda 'kg/desi' sütunu yok!")

    if hat_col not in dfp.columns:
        raise KeyError(f"{firma} tablosunda '{hat_adi}' (sütun='{hat_col}') yok!")

    # Tablo fiyatı
    mask = (dfp["kg/desi"] == kg_desi_deger)
    if not mask.any():
        raise IndexError(f"{firma}: kg/desi={kg_desi_deger} için satır bulunamadı.")

    price = float(dfp.loc[mask, hat_col].values[0])

    # Ağır taşıma kuralları
    if deger_turu_local == "ağırlık":
        if firma == "Aras Kargo" and kg_desi_deger > 100:
            price += 5120
        elif firma == "Yurtiçi Kargo" and kg_desi_deger > 100:
            price += 3950
        elif firma == "Sürat Kargo" and kg_desi_deger > 100:
            price += 3500
        elif firma == "DHL" and kg_desi_deger > 30:
            price += (kg_desi_deger - 30) * 74.99
    else:  # desi
        if firma == "DHL" and kg_desi_deger > 50:
            ekstra_desi = kg_desi_deger - 50
            price += (ekstra_desi // 3) * 74.99

    return price

# Tüm firmalar için standart bedeller
standart_bedeller = {}
for firma in FIYAT_DOSYALAR.keys():
    try:
        standart_bedeller[firma] = standard_bedel_bul(
            firma, hat, tasima_degeri, deger_turu
        )
    except Exception as e:
        print(f"⚠ {firma} standart bedel hesaplanamadı: {e}")

# =========================
# 5) EK HİZMETLER
#   - AA, AT, Sigorta: firma fiyat tablolarındaki sütunlardan (kg/desi satırına göre)
#   - Telefon, SMS: ayrı dosyalardan sabit/tekil satır okunur
# =========================
secim = input(
    "Ek hizmetler (virgülle ayırın, örn: AA,AT,Sigorta,Telefon,SMS) \
veya boş bırakın: "
).strip()
ek_hizmetler = []
if secim:
    ek_hizmetler = [h.strip().lower() for h in secim.split(",") if h.strip()]

def ek_hizmet_bedelleri(firma, kg_desi_deger):
    """
    Seçilen ek hizmetlere göre bedelleri toplar ve kalem kalem döndürür.
    {'aa': x, 'at': y, 'sigorta': z, 'telefon': t, 'sms': s}
    """
    kalemler = {"aa": 0.0, "at": 0.0, "sigorta": 0.0, "telefon": 0.0, "sms": 0.0}

    if not ek_hizmetler:
        return kalemler  # hiçbiri seçilmediyse 0'lar

    # AA/AT/Sigorta fiyatları firma fiyat tablosundan
    if any(h in ek_hizmetler for h in ["aa", "at", "sigorta"]):
        try:
            dfp = oku_fiyat(FIYAT_DOSYALAR[firma])
            if "kg/desi" not in dfp.columns:
                raise KeyError("kg/desi sütunu yok!")
            row = dfp.loc[dfp["kg/desi"] == kg_desi_deger]
            if not row.empty:
                row = row.iloc[0]
                for hcol in ["aa", "at", "sigorta"]:
                    if hcol in ek_hizmetler and hcol in row.index:
                        try:
                            kalemler[hcol] = float(row[hcol])
                        except:
                            pass
        except Exception as e:
            print(f"⚠ {firma} AA/AT/Sigorta okuma hatası: {e}")

    # Telefon/SMS ek hizmetleri ayrı dosyalardan
    if any(h in ek_hizmetler for h in ["telefon", "sms"]):
        try:
            ekdf = pd.read_excel(EK_HIZMET_DOSYALAR[firma])
            ekdf = ekdf.dropna(axis=1, how="all").dropna(axis=0, how="all")
            ekdf.columns = ekdf.columns.astype(str).str.strip().str.lower()
            # varsayılan ilk satırdan oku
            for hcol in ["telefon", "sms"]:
                if hcol in ek_hizmetler and hcol in ekdf.columns:
                    try:
                        kalemler[hcol] = float(ekdf.loc[ekdf.index[0], hcol])
                    except:
                        pass
        except Exception as e:
            print(f"⚠ {firma} Telefon/SMS okuma hatası: {e}")

    return kalemler

# =========================
# 6) VERGİLER
#   - KDV: %20 (her durumda)
#   - Posta Vergisi: %2,35
#       * deger_turu == 'ağırlık' ve tasima_degeri <= 30 (30 dahil)
#       * deger_turu == 'desi'    ve tasima_degeri <= 100 (100 dahil)
#   - Vergiler, (standart + ek hizmetler) üzerinden hesaplanır.
# =========================
def vergileri_hesapla(ara_toplam, deger_turu_local, kg_desi_deger):
    kdv = ara_toplam * 0.20
    posta = 0.0
    if deger_turu_local == "ağırlık" and kg_desi_deger <= 30:
        posta = ara_toplam * 0.0235
    elif deger_turu_local == "desi" and kg_desi_deger <= 100:
        posta = ara_toplam * 0.0235
    return kdv, posta

# =========================
# 7) ÖZET ÇIKTI (Firma firma)
#   - Standart bedel
#   - Ek hizmetler (kalem kalem + toplam)
#   - Vergiler (KDV, Posta ve toplam)
#   - GENEL TOPLAM
# =========================
print("\n=== Fiyat Özeti ===")
for firma, standart_bedel in standart_bedeller.items():
    # Ek hizmet kalemleri ve toplamı
    kalemler = ek_hizmet_bedelleri(firma, tasima_degeri)
    ek_hizmet_toplam = sum(kalemler.values())

    # Vergiler, (standart + ek hizmet) üzerinden
    ara_toplam = standart_bedel + ek_hizmet_toplam
    kdv, posta_vergisi = vergileri_hesapla(ara_toplam, deger_turu, tasima_degeri)
    toplam_vergiler = kdv + posta_vergisi

    genel_toplam = ara_toplam + toplam_vergiler

    # Yazdır
    print(f"\n--- {firma} ---")
    print(f"Standart Taşıma Bedeli: {standart_bedel:.2f} TL")

    # Ek hizmet kalemlerini sadece seçildiyse göster
    if ek_hizmetler:
        print("Ek Hizmetler:")
        if kalemler["aa"] or "aa" in ek_hizmetler:
            print(f"  AA: {kalemler['aa']:.2f} TL")
        if kalemler["at"] or "at" in ek_hizmetler:
            print(f"  AT: {kalemler['at']:.2f} TL")
        if kalemler["sigorta"] or "sigorta" in ek_hizmetler:
            print(f"  Sigorta: {kalemler['sigorta']:.2f} TL")
        if kalemler["telefon"] or "telefon" in ek_hizmetler:
            print(f"  Telefon İhbar Hizmeti: {kalemler['telefon']:.2f} TL")
        if kalemler["sms"] or "sms" in ek_hizmetler:
            print(f"  SMS: {kalemler['sms']:.2f} TL")
        print(f"Ek Hizmetler Toplamı: {ek_hizmet_toplam:.2f} TL")
    else:
        print("Ek Hizmetler: Seçilmedi (0.00 TL)")

    print("Vergiler:")
    print(f"  KDV: {kdv:.2f} TL")
    print(f"  Posta Vergisi: {posta_vergisi:.2f} TL")
    print(f"  Toplam Vergiler: {toplam_vergiler:.2f} TL")

    print(f"GENEL TOPLAM: {genel_toplam:.2f} TL")

