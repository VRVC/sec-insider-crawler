"""Genera un reporte HTML a partir del DataFrame de operaciones."""
import html
import math

COLORES_CODIGO = {"S": "venta", "P": "compra"}


def _vacio(x):
    """True si no hay dato (None o NaN, el 'vacío' de pandas)."""
    return x is None or (isinstance(x, float) and math.isnan(x))


def _dinero(x, decimales=0):
    return "" if _vacio(x) else f"${x:,.{decimales}f}"


def _entero(x):
    return "" if _vacio(x) else f"{x:,.0f}"


def _tarjetas(df):
    """Los indicadores principales (KPIs) de arriba del reporte."""
    ventas = df[df["codigo"] == "S"]
    compras = df[df["codigo"] == "P"]
    pct_plan = ventas["plan_10b5_1"].mean() if not ventas.empty else 0
    datos = [
        (len(df), "operaciones"),
        (df["insider"].nunique(), "insiders"),
        (_dinero(ventas["valor"].sum()), "vendido en mercado abierto"),
        (_dinero(compras["valor"].sum()), "comprado en mercado abierto"),
        (f"{pct_plan:.0%}", "de las ventas bajo plan 10b5-1"),
    ]
    return "".join(f'<div class="kpi"><b>{v}</b><span>{t}</span></div>' for v, t in datos)


def _barras_vendedores(df, n=5):
    """Top vendedores como barras horizontales hechas solo con CSS."""
    ventas = df[df["codigo"] == "S"]
    if ventas.empty:
        return "<p>Sin ventas en el periodo.</p>"
    top = ventas.groupby("insider")["valor"].sum().sort_values(ascending=False).head(n)
    maximo = top.max()
    filas = []
    for nombre, valor in top.items():
        ancho = valor / maximo * 100
        filas.append(
            f'<div class="barra"><span class="nombre">{html.escape(nombre)}</span>'
            f'<div class="pista"><div class="relleno" style="width:{ancho:.1f}%"></div></div>'
            f'<span class="monto">{_dinero(valor)}</span></div>'
        )
    return "".join(filas)


def _tabla(df):
    """Tabla con todas las operaciones; cada fecha lleva link al Form 4 original."""
    filas = []
    for r in df.itertuples():
        clase = COLORES_CODIGO.get(r.codigo, "")
        plan = '<span class="tag">10b5-1</span>' if r.plan_10b5_1 else ""
        filas.append(
            f"<tr><td><a href='{html.escape(r.url)}' target='_blank'>{r.fecha}</a></td>"
            f"<td>{html.escape(str(r.insider))}</td><td>{html.escape(str(r.cargo))}</td>"
            f"<td class='{clase}'>{r.codigo} · {html.escape(str(r.tipo))}</td>"
            f"<td class='num'>{_entero(r.acciones)}</td>"
            f"<td class='num'>{_dinero(r.precio, 2)}</td>"
            f"<td class='num'>{_dinero(r.valor)}</td>"
            f"<td class='num'>{_entero(r.acciones_despues)}</td>"
            f"<td>{r.propiedad or ''}</td><td>{plan}</td></tr>"
        )
    return "\n".join(filas)


def generar_html(df, ticker, empresa, ruta):
    """Escribe el reporte completo en `ruta`."""
    desde, hasta = df["fecha"].min(), df["fecha"].max()
    documento = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{ticker} · Reporte de insiders</title>
<style>
  body {{ background:#0b0d10; color:#e6e6e6; font-family:system-ui,sans-serif;
         margin:0 auto; padding:2rem; max-width:1200px; }}
  h1 {{ font-family:ui-monospace,monospace; margin-bottom:.2rem; }}
  .sub {{ color:#8b949e; margin-top:0; }}
  h2 {{ font-size:1rem; color:#8b949e; text-transform:uppercase; letter-spacing:.08em;
        margin-top:2.5rem; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:1rem; }}
  .kpi {{ background:#151a21; border:1px solid #222a33; padding:1rem 1.2rem; border-radius:10px; }}
  .kpi b {{ display:block; font-size:1.6rem; color:#5aa9ff; font-family:ui-monospace,monospace; }}
  .kpi span {{ color:#8b949e; font-size:.85rem; }}
  .barra {{ display:grid; grid-template-columns:220px 1fr 150px; align-items:center;
            gap:1rem; margin:.5rem 0; }}
  .pista {{ background:#151a21; border-radius:6px; height:14px; }}
  .relleno {{ background:#ff6b6b; height:100%; border-radius:6px; }}
  .monto {{ text-align:right; font-family:ui-monospace,monospace; }}
  table {{ border-collapse:collapse; width:100%; font-size:.85rem; }}
  th {{ text-align:left; color:#8b949e; font-weight:500; border-bottom:1px solid #30363d;
        padding:.5rem; position:sticky; top:0; background:#0b0d10; }}
  td {{ padding:.45rem .5rem; border-bottom:1px solid #1c2128; }}
  td.num {{ text-align:right; font-family:ui-monospace,monospace; }}
  td.venta {{ color:#ff6b6b; }}  td.compra {{ color:#4cd18a; font-weight:600; }}
  a {{ color:#5aa9ff; text-decoration:none; }}
  .tag {{ background:#1f2a37; color:#8fb8ff; padding:.1rem .45rem; border-radius:4px;
          font-size:.75rem; }}
  footer {{ color:#6e7681; font-size:.8rem; margin-top:2rem; }}
</style>
</head>
<body>
  <h1>{ticker} · Reporte de insiders</h1>
  <p class="sub">{html.escape(empresa)} · operaciones del {desde} al {hasta} · fuente: SEC Form 4</p>

  <div class="kpis">{_tarjetas(df)}</div>

  <h2>Mayores vendedores</h2>
  {_barras_vendedores(df)}

  <h2>Todas las operaciones</h2>
  <table>
    <tr><th>Fecha</th><th>Insider</th><th>Cargo</th><th>Tipo</th><th>Acciones</th>
        <th>Precio</th><th>Valor</th><th>Acciones después</th><th>D/I</th><th>Plan</th></tr>
    {_tabla(df)}
  </table>

  <footer>Generado con sec-insider-crawler. D = propiedad directa, I = indirecta
  (fideicomisos, fondos, familiares). Las ventas bajo plan 10b5-1 se programan con meses
  de anticipación.</footer>
</body>
</html>"""
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(documento)
