"""
sheets_helper.py
-----------------
Se encarga de traer los datos de facturación desde Google Sheets y aplicar
filtros/agrupaciones. Usa el link de exportación a CSV de la planilla,
así que NO necesitás credenciales de Google Cloud ni service accounts.

Columnas reales de la planilla de Nicatel (hoja "Facturación"):
    SKU, Nombre, Qty, USD, Total, Mes, Trimestre, Categoría,
    Subcategoria 1, Subcategoria 2, Familia, Marca,
    Unidad de Negocio, Punto de venta

Nota importante: la planilla no tiene columna de Año. Todo lo cargado
hasta ahora es de 2026.
"""

import os
import pandas as pd
   import requests
   import io

COL_SKU = "SKU"
COL_NOMBRE = "Nombre"
COL_QTY = "Qty"
COL_USD = "USD"
COL_TOTAL = "Total"
COL_MES = "Mes"
COL_TRIMESTRE = "Trimestre"
COL_CATEGORIA = "Categoría"
COL_FAMILIA = "Familia"
COL_MARCA = "Marca"
COL_UNIDAD_NEGOCIO = "Unidad de Negocio"
COL_PUNTO_VENTA = "Punto de venta"

SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
SHEET_GID = os.environ.get("GOOGLE_SHEET_GID", "0")


def _build_csv_url() -> str:
    if not SHEET_ID:
        raise ValueError("Falta configurar GOOGLE_SHEET_ID en las variables de entorno.")
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"


def _parse_numero_uy(valor) -> float:
    if pd.isna(valor):
        return float("nan")
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if texto == "":
        return float("nan")
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return float("nan")


       def cargar_datos() -> pd.DataFrame:
       """Descarga la planilla completa como DataFrame."""
       url = _build_csv_url()
       headers = {"User-Agent": "Mozilla/5.0"}
       respuesta = requests.get(url, headers=headers, timeout=15)
       respuesta.raise_for_status()
       df = pd.read_csv(io.StringIO(respuesta.text), dtype=str)

def consultar_ventas(
    mes: str | None = None,
    trimestre: str | None = None,
    producto: str | None = None,
    categoria: str | None = None,
    familia: str | None = None,
    marca: str | None = None,
    punto_venta: str | None = None,
    agrupar_por: str | None = None,
) -> dict:
    df = cargar_datos()

    if mes and COL_MES in df.columns:
        df = df[df[COL_MES].str.contains(mes, case=False, na=False)]
    if trimestre and COL_TRIMESTRE in df.columns:
        df = df[df[COL_TRIMESTRE].str.contains(trimestre, case=False, na=False)]
    if producto:
        mask = pd.Series(False, index=df.index)
        if COL_NOMBRE in df.columns:
            mask |= df[COL_NOMBRE].str.contains(producto, case=False, na=False)
        if COL_SKU in df.columns:
            mask |= df[COL_SKU].astype(str).str.contains(producto, case=False, na=False)
        df = df[mask]
    if categoria and COL_CATEGORIA in df.columns:
        df = df[df[COL_CATEGORIA].str.contains(categoria, case=False, na=False)]
    if familia and COL_FAMILIA in df.columns:
        df = df[df[COL_FAMILIA].str.contains(familia, case=False, na=False)]
    if marca and COL_MARCA in df.columns:
        df = df[df[COL_MARCA].str.contains(marca, case=False, na=False)]
    if punto_venta and COL_PUNTO_VENTA in df.columns:
        df = df[df[COL_PUNTO_VENTA].str.contains(punto_venta, case=False, na=False)]

    resultado = {
        "filas_encontradas": int(len(df)),
        "unidades_totales": int(df[COL_QTY].sum()) if COL_QTY in df.columns else None,
        "facturacion_total_usd": round(float(df[COL_TOTAL].sum()), 2) if COL_TOTAL in df.columns else None,
    }

    col_map = {
        "categoria": COL_CATEGORIA,
        "familia": COL_FAMILIA,
        "marca": COL_MARCA,
        "punto_venta": COL_PUNTO_VENTA,
        "mes": COL_MES,
    }

    if agrupar_por and len(df) > 0:
        group_col = col_map.get(agrupar_por)
        if group_col and group_col in df.columns:
            agg_dict = {}
            if COL_QTY in df.columns:
                agg_dict[COL_QTY] = "sum"
            if COL_TOTAL in df.columns:
                agg_dict[COL_TOTAL] = "sum"
            agrupado = df.groupby(group_col).agg(agg_dict).reset_index()
            sort_col = COL_QTY if COL_QTY in agrupado.columns else group_col
            agrupado = agrupado.sort_values(by=sort_col, ascending=False)
            resultado["desglose"] = agrupado.to_dict(orient="records")

    return resultado
