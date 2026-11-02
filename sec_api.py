"""Comunicación con la SEC (EDGAR)"""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv() # lee el archivo .env y carga SEC_EMAIL como variable de entorno

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


class ClienteSEC:
    """Hace peticiones a la SEC respertando sus reglas."""

    def __init__(self, email=None):
        email = email or os.getenv("SEC_EMAIL")
        if not email:
            raise ValueError("Falta SEC_EMAIL en el archivo .env")
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"SecInsiderCrawler {email}"

    def get_json(self, url):
        time.sleep(0.15) # máx. ~7 peticiones/seg (la SEC permite 10)
        respuesta = self.session.get(url, timeout=20)
        respuesta.raise_for_status() # si hubo error (404, 403...), lanza excepción 
        return respuesta.json()

def ticker_a_cik(cliente, ticker):
    """Convierte un ticker a su CIK correspondiente."""
    datos = cliente.get_json(TICKERS_URL)
    for empresa in datos.values():
        if empresa["ticker"].upper() == ticker.upper():
            return int(empresa["cik_str"]), empresa["title"]
    raise ValueError(f"No se encontró el ticker {ticker} en la SEC")

if __name__ == "__main__":
    # Esto solo corre si ejecutas este archivo directamente (prueba rápida)
    cliente = ClienteSEC()
    cik, nombre = ticker_a_cik(cliente, "PLTR")
    print(f"El CIK de PLTR es {cik} ({nombre})")
    
    