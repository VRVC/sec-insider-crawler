"""Punto de entrada: descarga los Form 4 de un ticker y guarda un CSV."""
import argparse
import webbrowser
from pathlib import Path

import pandas as pd

from parser_form4 import parsear_form4
from reporte import generar_html
from sec_api import ClienteSEC, listar_form4, ticker_a_cik

CARPETA_SALIDA = Path("output")


def recolectar(ticker, max_filings):
    """Descarga y parsea los Form 4; devuelve un DataFrame con todas las operaciones."""
    cliente = ClienteSEC()
    cik, empresa = ticker_a_cik(cliente, ticker)
    print(f"{ticker} → CIK {cik} ({empresa})")

    filings = listar_form4(cliente, cik, max_filings)
    todas = []
    for i, f in enumerate(filings, start=1):
        try:
            operaciones =  parsear_form4(cliente.get_texto(f["url_xml"]))
        except Exception as error:
            print(f"  [{i}/{len(filings)}] error en {f['accession']}: {error}")
            continue
        
        for op in operaciones: # agrega a cada operación de qué reporte salió
            op["fecha_reporte"] = f["fecha_reporte"]
            op["accession"] = f["accession"]
            op["url"] = f["url_html"]
        todas.extend(operaciones)
        print(f"  [{i}/{len(filings)}] {f['fecha_reporte']}: {len(operaciones)} operaciones")

    return pd.DataFrame(todas), empresa


def resumen(df):
    """Imprime un resumen rápido en la terminal"""
    print(f"\nTotal: {len(df)} operaciones de {df['insider'].nunique()} insiders")
    print("\nOperaciones por tipo:")
    print(df["tipo"].value_counts().to_string())

    ventas = df[df["codigo"] == "S"]
    if not ventas.empty:
        print(f"\nVendido en mercado abierto: ${ventas['valor'].sum():,.0f}")
        print(f"  de eso, bajo plan 10b5-1: {ventas['plan_10b5_1'].mean():.0%}")
        print("\nMayores vendedores:")
        top = ventas.groupby("insider")["valor"].sum().sort_values(ascending=False).head(5)
        for nombre, valor in top.items():
            print(f"  {nombre:<30} ${valor:>15,.0f}")

    compras = df[df["codigo"] == "P"]
    print(f"\nComprado en mercado abierto: ${compras['valor'].sum():,.0f} "
          f"({len(compras)} operaciones)")


def main():
    ap = argparse.ArgumentParser(description="Crawler de Form 4 de la SEC")
    ap.add_argument("ticker", help="Ticker de la empresa, ej. PLTR")
    ap.add_argument("--max-filings", type=int, default=40,
                    help="Cuántos Form 4 recientes descargar (default: 40)")
    args = ap.parse_args()
    ticker = args.ticker.upper()

    df, empresa = recolectar(ticker, args.max_filings)
    if df.empty:
        print("No se encontraron operaciones")
        return

    df = df.sort_values(["fecha", "insider"], ascending=[False, True])

    CARPETA_SALIDA.mkdir(exist_ok=True)
    ruta = CARPETA_SALIDA / f"insiders_{ticker}.csv"
    df.to_csv(ruta, index=False, encoding="utf-8-sig")

    ruta_html = CARPETA_SALIDA / f"reporte_{ticker}.html"
    generar_html(df, ticker, empresa, ruta_html)

    resumen(df)
    print(f"\nGuardado en {ruta} y {ruta_html}")

    webbrowser.open(ruta_html.resolve().as_uri())


if __name__ == "__main__":
    main()