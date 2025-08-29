import io
import re
from typing import Iterable, Dict, Any, Optional

import pandas as pd

# 12–14 dígitos = UPC/EAN
RE_UPC_EAN = re.compile(r"^\d{12,14}$")

# Usa EXACTAMENTE estos nombres en /admin al crear cada Supplier.
# id => columna de identificador, price => precio, stock => existencias
SUPPLIER_COLUMN_MAP: Dict[str, Dict[str, str]] = {
    "Proveedor A": {"id": "sku",     "price": "precio", "stock": "existencia"},
    "Proveedor B": {"id": "upc/ean", "price": "precio", "stock": "existencia"},
    "Proveedor C": {"id": "modelo",  "price": "precio", "stock": "existencia"},
}

def infer_id_type(raw: str) -> str:
    from catalogo.models import ProductIdentifier
    val = str(raw).strip()
    if RE_UPC_EAN.match(val):
        return ProductIdentifier.UPC_EAN
    if re.search(r"[A-Za-z\-]", val):
        return ProductIdentifier.MPN
    return ProductIdentifier.SKU_ALT

def normalize_header(col: str) -> str:
    return str(col).strip().lower().replace(" ", "_")

def _pick_value(row, col_name: Optional[str]):
    if not col_name:
        return None
    if col_name not in row.index:
        return None
    v = row[col_name]
    if pd.isna(v):
        return None
    return v

def parse_catalog_xlsx(supplier_name: str, file_bytes: bytes) -> Iterable[Dict[str, Any]]:
    """
    Devuelve dicts con:
      'identifier_value': str
      'price': float
      'stock': int

    • SOLO LECTURA: no modifica el archivo del proveedor.
    • Usa SUPPLIER_COLUMN_MAP si hay mapeo; si no, autodetecta encabezados comunes.
    """
    xls = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)

    supplier_key = supplier_name.strip().lower()
    explicit_map = None
    for k, v in SUPPLIER_COLUMN_MAP.items():
        if k.strip().lower() == supplier_key:
            explicit_map = {kk: normalize_header(vv) for kk, vv in v.items()}
            break

    ID_CANDS = {"mpn","sku","part","clave","modelo","upc","ean","codigo","identificador","upc/ean"}
    PRICE_CANDS = {"price","precio","unit_price","p_publico","p_mayoreo","costo","cost","p_lista"}
    STOCK_CANDS = {"stock","existencia","qty","inventario","cantidad","existencias","disponible","availability"}

    for sheet_name, df in xls.items():
        if df is None or df.empty:
            continue
        df.columns = [normalize_header(c) for c in df.columns]

        if explicit_map:
            id_col = explicit_map.get("id")
            price_col = explicit_map.get("price")
            stock_col = explicit_map.get("stock")
        else:
            id_col = next((c for c in df.columns if c in ID_CANDS), None)
            price_col = next((c for c in df.columns if c in PRICE_CANDS), None)
            stock_col = next((c for c in df.columns if c in STOCK_CANDS), None)

        if not id_col:
            # Si no encontramos columna de ID, pasa a la siguiente hoja (no se modifica nada)
            continue

        for _, row in df.iterrows():
            raw_id = _pick_value(row, id_col)
            if raw_id is None:
                continue
            ident = str(raw_id).strip()
            if not ident or ident.lower() in ("nan","none"):
                continue

            price_val = _pick_value(row, price_col)
            try:
                price = float(price_val) if price_val is not None else 0.0
            except Exception:
                price = 0.0

            stock_val = _pick_value(row, stock_col)
            try:
                stock = int(stock_val) if stock_val is not None else 0
            except Exception:
                try:
                    stock = int(float(stock_val)) if stock_val is not None else 0
                except Exception:
                    stock = 0

            yield {
                "identifier_value": ident,
                "price": round(price, 2),
                "stock": stock,
            }
