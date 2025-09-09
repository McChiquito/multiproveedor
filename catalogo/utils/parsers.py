import io
import re
from typing import Iterable, Dict, Any, Optional

import pandas as pd
import pdfplumber

# ========= Reglas y utilidades =========
RE_UPC_EAN = re.compile(r"^\d{12,14}$")   # 12–14 dígitos = UPC/EAN
NUM_RE = re.compile(r"[^0-9.,-]")         # limpia caracteres no numéricos
PDF_HEADER_KEYS = ("modelo", "precio", "existencia", "disponible", "stock", "descripcion", "descripción")


def normalize_header(col: str) -> str:
    """Normaliza encabezados: minúsculas y guiones bajos."""
    return str(col).strip().lower().replace(" ", "_")


def to_float_safe(val) -> float:
    """Convierte a float limpiando $, comas y espacios."""
    if val is None:
        return 0.0
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none"):
        return 0.0
    s = NUM_RE.sub("", s)     # "$13,513.19" -> "13,513.19"
    s = s.replace(",", "")    # "13,513.19" -> "13513.19"
    try:
        return float(s)
    except Exception:
        return 0.0


def to_int_safe(val) -> int:
    """Convierte a int redondeando."""
    f = to_float_safe(val)
    try:
        return int(round(f))
    except Exception:
        return 0


def _pick_value(row, col_name: Optional[str]):
    """Obtiene valor de columna si existe y no es NaN."""
    if not col_name:
        return None
    if col_name not in row.index:
        return None
    v = row[col_name]
    if pd.isna(v):
        return None
    return v


def infer_id_type(raw: str) -> str:
    """Clasifica el identificador por patrón."""
    from catalogo.models import ProductIdentifier
    val = str(raw).strip()
    if RE_UPC_EAN.match(val):
        return ProductIdentifier.UPC_EAN
    if re.search(r"[A-Za-z\-]", val):
        return ProductIdentifier.MPN
    return ProductIdentifier.SKU_ALT

# -- Reemplaza esta utilidad --
def convert_price(price_value: float, currency: Optional[str], usd_mxn_rate: float) -> float:
    """
    Convierte a MXN solo si la moneda es USD (acepta variantes).
    Si es MXN u otra, deja el precio tal cual.
    """
    cur = (str(currency or "")).strip().upper()

    USD_ALIASES = {"USD", "US$", "DOLARES", "DÓLARES", "DOLARES USD", "DÓLARES USD"}
    MXN_ALIASES = {"MXN", "MEX", "PESOS", "PESOS MXN", "MN"}

    if cur in USD_ALIASES:
        return round(float(price_value) * float(usd_mxn_rate), 2)
    # Si explícitamente es MXN (o cualquier otra cosa), no convertir
    return round(float(price_value), 2)

# ========= Mapeo por proveedor =========
SUPPLIER_COLUMN_MAP: Dict[str, Dict[str, str]] = {
    # Proveedor A: FILTRADO PROCESADORES INTEL Y AMD 28 JULIO (Excel)
    "Proveedor A": {
        "id": "sku",      # SKU / Cód. fabricante
        "stock": "inventario",
        "price": "precios_pesos_netos",   # en MXN
        # "price": "precios_oferta_usd_+_iva",  # alternativa en USD
    },
    # Proveedor B: Lista Especial 010825 (Excel)
    "Proveedor B": {
        "id": "upc/ean",
        "price": "precio final",             # ¡ojo! no "precio final"
        "stock": "cen",                # o "cedis"/"gdl"
    },
    # Proveedor C: ListaDePreciosTM (PDF)
    "Proveedor C": {
        "id": "modelo",
        "price": "precio",
        "stock": "existencia",
    },
}


# ========= Excel: lectura inteligente de encabezados =========
def read_with_smart_header(file_bytes, sheet_name, try_rows=15):
    """
    Intenta leer la hoja probando varias filas como encabezado y también header de 2 filas.
    Devuelve (df, header_row_usado) o (None, None) si no logra encontrar algo útil.
    """
    buf = io.BytesIO(file_bytes)

    # 1) primero, sin header para mirar contenido
    df0 = pd.read_excel(buf, sheet_name=sheet_name, header=None)
    if df0 is None or df0.empty:
        return None, None

    # Palabras que deberían existir en algún header válido
    must_keywords = ("upc", "ean", "precio", "existencia", "inventario", "modelo", "sku", "cód. fabricante", "codigo", "clave de artículo")

    def cols_ok(cols_norm):
        s = " | ".join(cols_norm)
        return any(k in s for k in ("upc/ean", "precio", "inventario", "existencia", "modelo", "sku",
                                    "cód._fabricante", "clave_de_artículo", "codigo", "cedis", "cen", "gdl"))

    # 2) probar header de 1 fila
    max_try = min(try_rows, len(df0))
    for r in range(max_try):
        buf.seek(0)
        df = pd.read_excel(buf, sheet_name=sheet_name, header=r)
        if df is None or df.empty:
            continue
        cols_norm = [normalize_header(c) for c in df.columns]
        unnamed_ratio = sum(col.startswith("unnamed") for col in cols_norm) / max(1, len(cols_norm))
        if unnamed_ratio > 0.6:
            continue
        if cols_ok(cols_norm):
            df.columns = cols_norm
            return df, r

    # 3) probar header compuesto de 2 filas (multilínea)
    for r in range(max_try - 1):
        buf.seek(0)
        df = pd.read_excel(buf, sheet_name=sheet_name, header=[r, r + 1])
        if df is None or df.empty:
            continue
        cols = []
        for c in df.columns:
            if isinstance(c, tuple):
                cols.append(" ".join([str(x) for x in c if str(x) != "None"]))
            else:
                cols.append(str(c))
        cols_norm = [normalize_header(c) for c in cols]
        unnamed_ratio = sum(col.startswith("unnamed") for col in cols_norm) / max(1, len(cols_norm))
        if unnamed_ratio > 0.6:
            continue
        if cols_ok(cols_norm):
            df.columns = cols_norm
            return df, r

    # 4) último intento: detectar por palabras clave escaneando filas y leer header en r
    for r in range(max_try):
        row_text = " | ".join([str(x) for x in df0.iloc[r].values])
        if any(k.lower() in row_text.lower() for k in must_keywords) and r + 1 < len(df0):
            buf.seek(0)
            df = pd.read_excel(buf, sheet_name=sheet_name, header=r)
            if df is None or df.empty:
                continue
            cols_norm = [normalize_header(c) for c in df.columns]
            if cols_ok(cols_norm):
                df.columns = cols_norm
                return df, r

    return None, None


# ========= Parser XLSX (A/B y genérico) =========
def parse_catalog_xlsx(supplier_name: str, file_bytes: bytes, *, usd_mxn_rate: float = 18.5) -> Iterable[Dict[str, Any]]:
    """
    Devuelve dicts:
      {'identifier_value': str, 'price': float, 'stock': int}
    """
    xls_raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, header=None)

    supplier_key = supplier_name.strip().lower()
    explicit_map = None
    for k, v in SUPPLIER_COLUMN_MAP.items():
        if k.strip().lower() == supplier_key:
            explicit_map = {kk: normalize_header(vv) for kk, vv in v.items()}
            break

    ID_CANDS = {"mpn", "sku", "part", "clave", "modelo", "upc", "ean", "codigo",
                "identificador", "upc/ean", "cód._fabricante"}
    PRICE_CANDS = {"price", "precio", "unit_price", "p_publico", "p_mayoreo", "costo",
                   "cost", "p_lista", "precios_pesos_netos"}
    STOCK_CANDS = {"stock", "existencia", "qty", "inventario", "cantidad", "existencias",
                   "disponible", "availability", "cedis", "cen", "gdl"}
    CURRENCY_CANDS = {"moneda", "currency"}

    for sheet_name, df0 in xls_raw.items():
        try:
            if df0 is None or df0.empty:
                continue

            df, header_row = read_with_smart_header(file_bytes, sheet_name, try_rows=20)
            if df is None or df.empty:
                print(f"⚠️  No se pudo encontrar encabezado útil en '{sheet_name}'")
                continue

            print(f"[{supplier_name} / {sheet_name}] header_row={header_row}")
            print("Columnas detectadas:", list(df.columns))

            if explicit_map:
                id_col = explicit_map.get("id")
                price_col = explicit_map.get("price")
                stock_col = explicit_map.get("stock")
                currency_col = next((c for c in df.columns if c in CURRENCY_CANDS), None)
            else:
                cols = list(df.columns)
                id_col = next((c for c in cols if c in ID_CANDS), None)
                price_col = next((c for c in cols if c in PRICE_CANDS), None)
                stock_col = next((c for c in cols if c in STOCK_CANDS), None)
                currency_col = next((c for c in cols if c in CURRENCY_CANDS), None)

            if not id_col:
                print(f"⚠️  No se encontró columna de identificador en {sheet_name} (cols={df.columns.tolist()})")
                continue

            for _, row in df.iterrows():
                raw_id = _pick_value(row, id_col)
                if raw_id is None:
                    continue
                ident = str(raw_id).strip()
                if not ident or ident.lower() in ("nan", "none"):
                    continue

                price_val = to_float_safe(_pick_value(row, price_col)) if price_col else 0.0
                currency = _pick_value(row, currency_col) if currency_col else None
                price = convert_price(price_val, currency, usd_mxn_rate)

                stock = to_int_safe(_pick_value(row, stock_col)) if stock_col else 0

                yield {"identifier_value": ident, "price": price, "stock": stock}

        except Exception as e:
            print(f"❌ Error procesando hoja '{sheet_name}': {e}")
            continue


# ========= PDF (Proveedor C) =========
def extract_tables_from_pdf(file_bytes: bytes):
    """Extrae tablas crudas de cada página con pdfplumber."""
    dfs = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            for tbl in tables or []:
                if not tbl or len(tbl) < 2:
                    continue
                df = pd.DataFrame(tbl)
                dfs.append(df)
    return dfs


def find_header_row_in_df(df_raw: pd.DataFrame, max_try: int = 5):
    """Busca la fila de encabezados en los primeros renglones del DF crudo."""
    n = min(max_try, len(df_raw))
    for r in range(n):
        row_vals = [str(x) for x in df_raw.iloc[r].values]
        joined = " | ".join(row_vals).lower()
        if any(k in joined for k in PDF_HEADER_KEYS):
            return r
    return 0


def normalize_pdf_table(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Convierte tabla cruda del PDF a DF con encabezados normalizados."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    header_row = find_header_row_in_df(df_raw, max_try=8)
    headers = df_raw.iloc[header_row].tolist()
    body = df_raw.iloc[header_row + 1:].reset_index(drop=True)

    if len(body.columns) != len(headers):
        min_cols = min(len(body.columns), len(headers))
        body = body.iloc[:, :min_cols]
        headers = headers[:min_cols]

    body.columns = [normalize_header(h) for h in headers]
    good_cols = [c for c in body.columns if c and not str(c).startswith("unnamed")]
    body = body[good_cols].copy()
    return body


def parse_catalog_pdf_tm(supplier_name: str, file_bytes: bytes, *, usd_mxn_rate: float = 18.5) -> Iterable[Dict[str, Any]]:
    """
    Parser para Proveedor C (PDF).
    - ID = 'modelo'
    - Precio = 'precio c/desc.' si existe y es numérico; si no, 'precio'
    - Convierte USD→MXN según la columna 'moneda' (si falta, asume USD por defecto).
      * Si prefieres asumir MXN cuando no haya columna, cambia el 'default_currency' más abajo.
    """
    raw_tables = extract_tables_from_pdf(file_bytes)
    if not raw_tables:
        return

    # Candidatos
    ID_COLS         = ["modelo", "clave", "codigo", "código", "mpn"]
    PRICE_COL_DISC  = ["precio_c/desc.", "precio\nc/desc."]
    PRICE_COL_BASE  = ["precio", "precio_neto", "precio_publico", "precio_público", "precio_mxn"]
    STOCK_COLS      = ["existencia", "disponible", "stock", "existencias"]
    CURRENCY_COLS   = ["moneda", "currency"]

    # Cambia este default si quieres asumir MXN cuando no haya columna de moneda
    default_currency = "USD"

    def pick_first(cols, candidates):
        for c in candidates:
            if c in cols:
                return c
        return None

    for t in raw_tables:
        df = normalize_pdf_table(t)
        if df is None or df.empty:
            continue

        cols = list(df.columns)

        id_col         = pick_first(cols, ["modelo"] + ID_COLS)
        price_disc_col = pick_first(cols, PRICE_COL_DISC)
        price_base_col = pick_first(cols, PRICE_COL_BASE)
        stock_col      = pick_first(cols, STOCK_COLS)
        currency_col   = pick_first(cols, CURRENCY_COLS)

        if not id_col:
            continue

        for _, row in df.iterrows():
            ident = _pick_value(row, id_col)
            if ident is None:
                continue

            ident = str(ident).strip()
            if not ident or ident.lower() in ("nan", "none"):
                continue

            # Evita filas de secciones (títulos)
            if len(ident) > 40 or (ident.isupper() and " " in ident):
                continue

            # Lee ambos precios
            disc_raw  = _pick_value(row, price_disc_col) if price_disc_col else None
            base_raw  = _pick_value(row, price_base_col) if price_base_col else None
            price_disc = to_float_safe(disc_raw)
            price_base = to_float_safe(base_raw)

            # Elige mejor precio
            price_val = price_disc if price_disc > 0 else price_base

            # Moneda
            currency  = _pick_value(row, currency_col) if currency_col else default_currency
            price_mxn = convert_price(price_val, currency, usd_mxn_rate)

            # Stock
            stock = to_int_safe(_pick_value(row, stock_col)) if stock_col else 0

            yield {
                "identifier_value": ident,
                "price": price_mxn,
                "stock": stock,
            }
        print("cols:", cols)
        print("id:", id_col, "price_disc:", price_disc_col, "price_base:", price_base_col, "curr:", currency_col)


# ========= Router (PDF/XLSX) =========
def parse_catalog_auto(supplier_name: str, file_name: str, file_bytes: bytes, *, usd_mxn_rate: float = 18.5) -> Iterable[Dict[str, Any]]:
    """
    Enruta según extensión y proveedor.
    - Proveedor C + .pdf -> parse_catalog_pdf_tm
    - Si es .xlsx/.xls -> parse_catalog_xlsx
    - Fallback: intenta Excel
    """
    name_lower = (file_name or "").lower()
    if name_lower.endswith(".pdf") and supplier_name.strip().lower() == "proveedor c":
        return parse_catalog_pdf_tm(supplier_name, file_bytes, usd_mxn_rate=usd_mxn_rate)
    return parse_catalog_xlsx(supplier_name, file_bytes, usd_mxn_rate=usd_mxn_rate)
