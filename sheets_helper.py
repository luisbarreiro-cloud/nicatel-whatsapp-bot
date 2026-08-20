"""
sheets_helper.py
-----------------
Se encarga de traer los datos de ventas desde Google Sheets y aplicar
filtros/agrupaciones. Usa el link de exportación a CSV de la planilla,
así que NO necesitás credenciales de Google Cloud ni service accounts.

Requisito en tu Google Sheet:
- Columnas esperadas (podés tener más, estas son las que usa el bot):
    Fecha        -> formato YYYY-MM-DD o DD/MM/YYYY
    Producto     -> texto libre (ej: "TV Samsung 55 QLED")
    Categoria    -> texto libre (ej: "TV", "Celular", "Electrodomestico")
    Cantidad     -> número entero
    PrecioUnitario -> número (opcional, para calcular facturación)
    Canal        -> texto libre (ej: "Tienda", "MercadoLibre", "Interior")

- La planilla tiene que estar compartida como
  "Cualquier persona con el enlace puede ver" (Ver > no hace falta editar).
"""

import os
import pandas as pd
from datetime import datetime

# ID de tu Google Sheet (lo sacás de la URL:
# https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit)
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")

# GID de la pestaña específica (0 = primera pestaña). Lo sacás de la URL
# cuando estás parado en esa pestaña: .../edit#gid=ESTE_NUMERO
SHEET_GID = os.environ.get("GOOGLE_SHEET_GID", "0")


def _build_csv_url() -> str:
    if not SHEET_ID:
        raise ValueError(
            "Falta configurar GOOGLE_SHEET_ID en las variables de entorno."
        )
    return (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/export?format=csv&gid={SHEET_GID}"
    )


def cargar_datos() -> pd.DataFrame:
    """Descarga la planilla completa como DataFrame, cacheada por request."""
    url = _build_csv_url()
    df = pd.read_csv(url)

    # Normalizar nombres de columnas (sin tildes/espacios raros)
    df.columns = [c.strip() for c in df.columns]

    # Parsear fecha de forma flexible
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")

    # Asegurar tipos numéricos
    for col in ["Cantidad", "PrecioUnitario"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Cantidad" in df.columns and "PrecioUnitario" in df.columns:
        df["Total"] = df["Cantidad"] * df["PrecioUnitario"]

    return df


def consultar_ventas(
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    producto: str | None = None,
    categoria: str | None = None,
    canal: str | None = None,
    agrupar_por: str | None = None,
) -> dict:
    """
    Filtra el DataFrame de ventas según los parámetros dados y devuelve
    un resumen. Todos los parámetros son opcionales.

    agrupar_por: "producto" | "categoria" | "canal" | "mes" | None
    """
    df = cargar_datos()

    if fecha_inicio and "Fecha" in df.columns:
        df = df[df["Fecha"] >= pd.to_datetime(fecha_inicio)]
    if fecha_fin and "Fecha" in df.columns:
        df = df[df["Fecha"] <= pd.to_datetime(fecha_fin)]
    if producto and "Producto" in df.columns:
        df = df[df["Producto"].str.contains(producto, case=False, na=False)]
    if categoria and "Categoria" in df.columns:
        df = df[df["Categoria"].str.contains(categoria, case=False, na=False)]
    if canal and "Canal" in df.columns:
        df = df[df["Canal"].str.contains(canal, case=False, na=False)]

    resultado = {
        "filas_encontradas": int(len(df)),
        "unidades_totales": int(df["Cantidad"].sum()) if "Cantidad" in df.columns else None,
        "facturacion_total": float(df["Total"].sum()) if "Total" in df.columns else None,
    }

    if agrupar_por and len(df) > 0:
        col_map = {
            "producto": "Producto",
            "categoria": "Categoria",
            "canal": "Canal",
        }
        if agrupar_por == "mes" and "Fecha" in df.columns:
            df["Mes"] = df["Fecha"].dt.to_period("M").astype(str)
            group_col = "Mes"
        else:
            group_col = col_map.get(agrupar_por)

        if group_col and group_col in df.columns:
            agg_dict = {}
            if "Cantidad" in df.columns:
                agg_dict["Cantidad"] = "sum"
            if "Total" in df.columns:
                agg_dict["Total"] = "sum"
            agrupado = df.groupby(group_col).agg(agg_dict).reset_index()
            agrupado = agrupado.sort_values(
                by="Cantidad" if "Cantidad" in agrupado.columns else group_col,
                ascending=False,
            )
            resultado["desglose"] = agrupado.to_dict(orient="records")

    return resultado
