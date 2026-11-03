"""Convierte un Form 4 (XML) en una lista de operaciones."""
import xml.etree.ElementTree as ET

# Códigos de transacción más comunes del Form 4
CODIGOS = {
    "P": "Compra en mercado abierto",
    "S": "Venta en mercado abierto",
    "M": "Ejercicio de opciones/RSU",
    "A": "Otorgamiento (grant)",
    "F": "Pago de impuestos con acciones",
    "G": "Transferencia de acciones (gift)",
    "C": "Conversión de valores (convert)",
}


def _texto(nodo, ruta):
    """Lee el texto de una etiqueta, esté o no envuelta en <value>."""
    if nodo is None:
        return None
    elemento = nodo.find(ruta + "/value")
    if elemento is None:
        elemento = nodo.find(ruta)
    if elemento is None or elemento.text is None:
        return None
    return elemento.text.strip()


def _numero(texto):
    """Convierte texto a número; si no se puede, devuelve None."""
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def _es_verdadero(texto):
    """La SEC escribe 'sí' como 1 o true."""
    return (texto or "").lower() in ("1", "true")

def parsear_form4(xml_texto):
    """Devuelve una lista de diccionarios, uno por operación."""
    raiz = ET.fromstring(xml_texto)

    # 1. Datos del encabezado (iguales para todas las operaciones del reporte)
    ticker = _texto(raiz, "issuer/issuerTradingSymbol")

    dueno = raiz.find("reportingOwner")
    nombre = _texto(dueno, "reportingOwnerId/rptOwnerName")

    relacion = dueno.find("reportingOwnerRelationship") if dueno is not None else None
    cargos = []
    if _es_verdadero(_texto(relacion, "isDirector")):
        cargos.append("Director")
    if _es_verdadero(_texto(relacion, "isOfficer")):
        cargos.append(_texto(relacion, "officerTitle") or "Officer")
    if _es_verdadero(_texto(relacion, "isTenPercentOwner")):
        cargos.append("Dueño >10%")

    # 2. ¿Fue bajo un plan 10b5-1? Viene en <aff10b5One> o en las notas al pie
    notas = " ".join(nota.text or "" for nota in raiz.iter("footnote"))
    plan_10b5_1 = _es_verdadero(_texto(raiz, "aff10b5One")) or "10b5-1" in notas

    # 3. Una fila por cada operación con acciones comunes
    operaciones = []
    for op in raiz.iter("nonDerivativeTransaction"):
        codigo = _texto(op, "transactionCoding/transactionCode")
        acciones = _numero(_texto(op, "transactionAmounts/transactionShares"))
        precio = _numero(_texto(op, "transactionAmounts/transactionPricePerShare"))

        operaciones.append({
            "ticker": ticker,
            "insider": nombre,
            "cargo": ", ".join(cargos),
            "fecha": _texto(op, "transactionDate"),
            "codigo": codigo,
            "tipo": CODIGOS.get(codigo, codigo),
            "acciones": acciones,
            "precio": precio,
            "valor": round(acciones * precio, 2) if acciones and precio else None,
            "acciones_despues": _numero(_texto(op, "postTransactionAmounts/sharesOwnedFollowingTransaction")),
            "propiedad": _texto(op, "ownershipNature/directOrIndirectOwnership"),
            "plan_10b5_1": plan_10b5_1,
        })
    return operaciones


if __name__ == "__main__":
    # Prueba: descarga los 3 Form 4 más recientes de PLTR y muestra sus operaciones
    from sec_api import ClienteSEC, ticker_a_cik, listar_form4

    cliente = ClienteSEC()
    cik, _ = ticker_a_cik(cliente, "PLTR")

    for f in listar_form4(cliente, cik, max_filings=5):
        xml = cliente.get_texto(f["url_xml"])
        operaciones = parsear_form4(xml)
        print(f"\n{f['fecha_reporte']} ({len(operaciones)} operaciones)")
        for op in operaciones:
            print(f"  {op['insider']} | {op['codigo']} | {op['acciones']:,.0f} acc. "
                  f"@ ${op['precio'] or 0:,.2f} | 10b5-1: {op['plan_10b5_1']}")