#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 13 10:16:17 2025

@author: suayhatalmis
"""

import streamlit as st 
import pandas as pd

# =========================
# 1) İL MESAFE TABLOSUNU OKU
# =========================
ILMESAFE_DOSYA = "ilmesafe.xlsx"

df = pd.read_excel(ILMESAFE_DOSYA, header=None)
iller_sutun = df.iloc[1, 2:].astype(str).str.strip().str.upper().values
iller_satir = df.iloc[2:, 1].astype(str).str.strip().str.upper().values
mesafe_df = df.iloc[2:, 2:]
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

def oku_fiyat(dosya):
    dfp = pd.read_excel(dosya)
    dfp = dfp.dropna(axis=1, how="all").dropna(axis=0, how="all")
    dfp.columns = dfp.columns.astype(str).str.strip().str.lower()
    return dfp

def standard_bedel_bul(firma, hat_adi, kg_desi_deger, deger_turu_local):
    dfp = oku_fiyat(FIYAT_DOSYALAR[firma])
    hat_col = hat_adi.strip().lower()
    mask = (dfp["kg/desi"] == kg_desi_deger)
    price = float(dfp.loc[mask, hat_col].values[0])

    if deger_turu_local == "ağırlık":
        if firma == "Aras Kargo" and kg_desi_deger > 100:
            price += 5120
        elif firma == "Yurtiçi Kargo" and kg_desi_deger > 100:
            price += 3950
        elif firma == "Sürat Kargo" and kg_desi_deger > 100:
            price += 3500
        elif firma == "DHL" and kg_desi_deger > 30:
            price += (kg_desi_deger - 30) * 74.99
    else:
        if firma == "DHL" and kg_desi_deger > 50:
            ekstra_desi = kg_desi_deger - 50
            price += (ekstra_desi // 3) * 74.99

    return price

def ek_hizmet_bedelleri(firma, kg_desi_deger, ek_hizmetler):
    kalemler = {"aa": 0.0, "at": 0.0, "sigorta": 0.0, "telefon": 0.0, "sms": 0.0}
    if not ek_hizmetler:
        return kalemler

    if any(h in ek_hizmetler for h in ["aa", "at", "sigorta"]):
        dfp = oku_fiyat(FIYAT_DOSYALAR[firma])
        row = dfp.loc[dfp["kg/desi"] == kg_desi_deger].iloc[0]
        for hcol in ["aa", "at", "sigorta"]:
            if hcol in ek_hizmetler and hcol in row.index:
                kalemler[hcol] = float(row[hcol])

    if any(h in ek_hizmetler for h in ["telefon", "sms"]):
        ekdf = pd.read_excel(EK_HIZMET_DOSYALAR[firma])
        ekdf = ekdf.dropna(axis=1, how="all").dropna(axis=0, how="all")
        ekdf.columns = ekdf.columns.astype(str).str.strip().str.lower()
        for hcol in ["telefon", "sms"]:
            if hcol in ek_hizmetler and hcol in ekdf.columns:
                kalemler[hcol] = float(ekdf.loc[ekdf.index[0], hcol])
    return kalemler

def vergileri_hesapla(ara_toplam, deger_turu_local, kg_desi_deger):
    kdv = ara_toplam * 0.20
    posta = 0.0
    if deger_turu_local == "ağırlık" and kg_desi_deger <= 30:
        posta = ara_toplam * 0.0235
    elif deger_turu_local == "desi" and kg_desi_deger <= 100:
        posta = ara_toplam * 0.0235
    return kdv, posta

# =========================
# STREAMLIT ARAYÜZ
# =========================
st.title("📦 Kargo Fiyat Hesaplama")

nereden = st.selectbox("Nereden:", sorted(iller_satir))
nereye = st.selectbox("Nereye:", sorted(iller_sutun))

mesafe = mesafe_bul(nereden, nereye)
if mesafe:
    hat = hat_belirle(mesafe)
    st.info(f"Mesafe: {mesafe} km | Hat türü: {hat}")
else:
    st.error("Mesafe bulunamadı!")

tasima_turu = st.selectbox("Taşıma türü:", ["Dosya", "Paket/Koli"])
tasima_degeri = 0
deger_turu = "ağırlık"

if tasima_turu.lower() in ["paket/koli", "paket", "koli"]:
    kargo_sayisi = st.number_input("Kaç kargo göndereceksiniz? (max 5)", 1, 5, 1)
    toplam_desi = 0.0
    toplam_agirlik = 0.0
    for i in range(int(kargo_sayisi)):
        st.subheader(f"{i+1}. Kargo")
        en = st.number_input(f"{i+1}. En (cm)", 0.0, step=1.0)
        boy = st.number_input(f"{i+1}. Boy (cm)", 0.0, step=1.0)
        yukseklik = st.number_input(f"{i+1}. Yükseklik (cm)", 0.0, step=1.0)
        agirlik = st.number_input(f"{i+1}. Ağırlık (kg)", 0.0, step=0.1)
        desi = en * boy * yukseklik / 3000
        toplam_desi += desi
        toplam_agirlik += agirlik
    tasima_degeri = int(max(toplam_desi, toplam_agirlik))
    deger_turu = "ağırlık" if toplam_agirlik >= toplam_desi else "desi"
    st.write(f"Toplam Desi: {toplam_desi:.2f}, Toplam Ağırlık: {toplam_agirlik:.2f}")
    st.success(f"Taşıma değeri: {tasima_degeri} ({deger_turu})")
else:
    tasima_degeri = 0
    deger_turu = "ağırlık"

ek_hizmetler = st.multiselect(
    "Ek hizmetler:",
    ["aa", "at", "sigorta", "telefon", "sms"]
)

if st.button("Hesapla"):
    standart_bedeller = {}
    for firma in FIYAT_DOSYALAR.keys():
        try:
            standart_bedeller[firma] = standard_bedel_bul(
                firma, hat, tasima_degeri, deger_turu
            )
        except Exception as e:
            st.warning(f"{firma} fiyat hesaplanamadı: {e}")

    for firma, standart_bedel in standart_bedeller.items():
        kalemler = ek_hizmet_bedelleri(firma, tasima_degeri, ek_hizmetler)
        ek_hizmet_toplam = sum(kalemler.values())
        ara_toplam = standart_bedel + ek_hizmet_toplam
        kdv, posta = vergileri_hesapla(ara_toplam, deger_turu, tasima_degeri)
        genel_toplam = ara_toplam + kdv + posta

        with st.expander(f"📌 {firma}"):
            st.write(f"**Standart Bedel:** {standart_bedel:.2f} TL")
            if ek_hizmetler:
                st.write("**Ek Hizmetler:**")
                for h, v in kalemler.items():
                    if h in ek_hizmetler:
                        st.write(f"- {h.upper()}: {v:.2f} TL")
                st.write(f"**Ek Hizmetler Toplamı:** {ek_hizmet_toplam:.2f} TL")
            else:
                st.write("Ek hizmet seçilmedi.")
            st.write("**Vergiler:**")
            st.write(f"- KDV: {kdv:.2f} TL")
            st.write(f"- Posta Vergisi: {posta:.2f} TL")
            st.write(f"**GENEL TOPLAM:** {genel_toplam:.2f} TL")


