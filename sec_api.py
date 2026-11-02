"""Comunicación con la SEC (EDGAR)"""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv() # lee el archivo .env y carga SEC_EMAIL como variable de entorno

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVO_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"


class ClienteSEC:
    """Hace peticiones a la SEC respertando sus reglas."""

    def __init__(self, email=None):
        email = email or os.getenv("SEC_EMAIL")
        if not email:
            raise ValueError("Falta SEC_EMAIL en el archivo .env")
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"SecInsiderCrawler {email}"

    def _get(self, url):
        time.sleep(0.15) # máx. ~7 peticiones/seg (la SEC permite 10)
        respuesta = self.session.get(url, timeout=20)
        respuesta.raise_for_status() # si hubo error (404, 403...), lanza excepción 
        return respuesta

    def get_json(self, url):
        return self._get(url).json()

    def get_texto(self, url):
        return self._get(url).text


def ticker_a_cik(cliente, ticker):
    """Convierte un ticker a su CIK correspondiente."""
    datos = cliente.get_json(TICKERS_URL)
    for empresa in datos.values():
        if empresa["ticker"].upper() == ticker.upper():
            return int(empresa["cik_str"]), empresa["title"]
    raise ValueError(f"No se encontró el ticker {ticker} en la SEC")


def listar_form4(cliente, cik, max_filings=40):
    """Devuelve los Form 4 más recientes de una empresa"""
    datos = cliente.get_json(SUBMISSIONS_URL.format(cik=cik))
    recientes = datos["filings"]["recent"]

    filings = []
    for form, acc, fecha, doc in zip(recientes["form"],
                                    recientes["accessionNumber"],
                                    recientes["filingDate"],
                                    recientes["primaryDocument"]):
        if form != "4": # solo Form 4 (ignora 8-K, 10-Q, enmiendas 4/A, etc.)
            continue

        carpeta = acc.replace("-", "") # la carpeta usa el folio sin guines
        doc_xml = doc.split("/")[-1] # quita el prefijo 'xslF345X05/'

        filings.append({
            "accession": acc,
            "fecha_reporte": fecha,
            "url_xml": ARCHIVO_URL.format(cik=cik, acc=carpeta, doc=doc_xml),
            "url_html": ARCHIVO_URL.format(cik=cik, acc=carpeta, doc=doc),
        })
        if len(filings) >= max_filings:
            break

    return filings


if __name__ == "__main__":
    # Esto solo corre si ejecutas este archivo directamente (prueba rápida)
    cliente = ClienteSEC()
    cik, nombre = ticker_a_cik(cliente, "PLTR")
    print(f"El CIK de PLTR es {cik} ({nombre})")

    filings = listar_form4(cliente, cik, max_filings=5)
    print(f"\nÚltimos {len(filings)} Form 4:")
    for f in filings:
        print(f" {f['fecha_reporte']} {f['accession']}")
        print(f" {f['url_html']}")


    