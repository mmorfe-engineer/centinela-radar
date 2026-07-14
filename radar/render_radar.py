#!/usr/bin/env python3
"""
RADAR - Render HTML propio para GitHub Pages
=============================================
Genera el informe HTML visual y el mensaje corto para Telegram.
"""

from datetime import datetime
from typing import Any, Dict, List

_VERDE = "VERDE_con_cobertura"
_AMARILLO = "AMARILLO_sin_cobertura_certificado"
_ROJO = "ROJO_no_verificable"

# Importar normalización para contar hallazgos de Venezuela
from core.normalizacion import normalizar_titulo

_MESES_ES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
}


def _esc(text: str) -> str:
    """Escapar caracteres HTML básicos."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _tag(texto: str, cls: str) -> str:
    return f'<span class="tag tag-{cls}">{_esc(texto)}</span>'


def _render_medios_tablero(estados_medios: Dict[str, str], medios_config: List[Dict], errores_medios: Dict[str, str] = None) -> str:
    if not estados_medios or not medios_config:
        return '<p class="empty">Sin datos de tablero por medio</p>'

    chips = []
    errores_medios = errores_medios or {}
    
    for medio in medios_config:
        mid = medio.get("id", "")
        estado = estados_medios.get(mid, _ROJO)
        nombre = _esc(medio.get("nombre", mid))
        error_msg = errores_medios.get(mid, "")
        
        if estado == _VERDE:
            cls = "verde"
            tooltip = "Con cobertura"
        elif estado == _AMARILLO:
            cls = "amarillo"
            tooltip = "Sin cobertura certificada"
        else:
            cls = "rojo"
            tooltip = f"Error: {error_msg}" if error_msg else "No verificable"
        
        chips.append(
            f'<div class="medio-chip {cls}" title="{tooltip}">'
            f'<span class="dot"></span>'
            f'<span class="nombre">{nombre}</span>'
            f'</div>'
        )
    return "\n".join(chips)


def _render_top5(top5: List[Dict]) -> str:
    if not top5:
        return '<p class="empty">Sin hallazgos disponibles para este corte</p>'

    items = []
    for item in top5:
        rank = item.get("rank", "?")
        h = item.get("hallazgo", {})
        titulo = _esc(h.get("titulo", "Sin título"))
        medio_id = h.get("medio_id", "")
        valencia = h.get("valencia", "neutral") or "neutral"
        enfoque = h.get("enfoque_matriz", "pais_general") or "pais_general"
        prominencia = h.get("prominencia", "") or ""
        fuente_url = h.get("fuente_url") or h.get("url") or ""

        tags = []
        if medio_id:
            tags.append(_tag(medio_id.upper(), "medio"))
        if valencia != "neutral":
            tags.append(_tag(valencia, valencia))
        if enfoque != "pais_general":
            tags.append(_tag(enfoque.replace("_", " "), enfoque))
        if prominencia == "portada":
            tags.append(_tag("PORTADA", "portada"))

        link = ""
        if fuente_url and not fuente_url.startswith("synthetic://"):
            link = f'<a class="tag-fuente" href="{fuente_url}" target="_blank" rel="noopener">→ ver nota</a>'

        tags_html = " ".join(tags)
        items.append(f"""
        <div class="top-item">
            <div class="top-rank">{rank}</div>
            <div class="top-content">
                <div class="top-titulo">{titulo}</div>
                <div class="top-meta">{tags_html} {link}</div>
            </div>
        </div>""")

    return "\n".join(items)


def _render_top10(top10: List[Dict]) -> str:
    if not top10:
        return '<p class="empty">Sin datos de agenda global disponibles</p>'

    items = []
    for item in top10:
        rank = item.get("rank", "?")
        titulo = _esc(item.get("titulo_canonico", "Sin título"))
        n_medios = item.get("cuenta_medios", 0)
        regiones = item.get("regiones", [])
        es_venezolano = item.get("es_venezolano", False)
        titulares = item.get("titulares", [])

        # Extraer primera URL válida del grupo
        url = ""
        for t in titulares:
            candidate_url = t.get("url", "") or t.get("fuente_url", "")
            if candidate_url and not candidate_url.startswith("synthetic://"):
                url = candidate_url
                break

        cls = "global-item venezolano" if es_venezolano else "global-item"
        bandera = " 🇻🇪" if es_venezolano else ""
        stats = f"{n_medios} medios · {len(regiones)} regiones"

        link_html = ""
        if url:
            link_html = f' <a class="tag-fuente" href="{url}" target="_blank" rel="noopener">→ fuente</a>'

        items.append(
            f'<div class="{cls}">'
            f'<div class="global-rank">{rank}</div>'
            f'<div class="global-titulo">{titulo}{bandera}{link_html}</div>'
            f'<div class="global-stats">{stats}</div>'
            f'</div>'
        )

    return "\n".join(items)


def _tiene_url_real(h: dict) -> bool:
    url = h.get("url") or h.get("fuente_url") or ""
    return bool(url) and url.startswith(("http://", "https://")) and not url.startswith("synthetic://")


def _render_todos_hallazgos(hallazgos: List[Dict]) -> str:
    """Renderiza una lista completa de todos los hallazgos sobre Venezuela."""
    # Filtrar solo hallazgos que mencionan Venezuela
    hallazgos_venezuela = [
        h for h in hallazgos
        if "venezuela" in normalizar_titulo(h.get("titulo", "") or "")
        or any("venezuela" in normalizar_titulo(c or "") for c in h.get("conectores_activados", []))
    ]

    if not hallazgos_venezuela:
        return '<p class="empty">Sin hallazgos disponibles</p>'

    # Artículos con link verificable primero
    hallazgos_venezuela.sort(key=lambda h: 0 if _tiene_url_real(h) else 1)

    items = []
    for idx, hallazgo in enumerate(hallazgos_venezuela, 1):
        titulo = _esc(hallazgo.get("titulo", "Sin título"))
        medio_id = hallazgo.get("medio_id", "")
        valencia = hallazgo.get("valencia", "neutral") or "neutral"
        enfoque = hallazgo.get("enfoque_matriz", "pais_general") or "pais_general"
        prominencia = hallazgo.get("prominencia", "") or ""
        url = hallazgo.get("url", "") or hallazgo.get("fuente_url", "")

        tags = []
        if medio_id:
            tags.append(_tag(medio_id.upper(), "medio"))
        if valencia != "neutral":
            tags.append(_tag(valencia, valencia))
        if enfoque != "pais_general":
            tags.append(_tag(enfoque.replace("_", " "), enfoque))
        if prominencia == "portada":
            tags.append(_tag("PORTADA", "portada"))

        link = ""
        if url and not url.startswith("synthetic://"):
            link = f'<a class="tag-fuente" href="{url}" target="_blank" rel="noopener">→ ver nota</a>'

        tags_html = " ".join(tags)
        items.append(f"""
        <div class="hallazgo-item">
            <div class="hallazgo-rank">{idx}</div>
            <div class="hallazgo-content">
                <div class="hallazgo-titulo">{titulo}</div>
                <div class="hallazgo-meta">{tags_html} {link}</div>
            </div>
        </div>""")

    return "\n".join(items)


def render_html_radar(
    contrato: Dict[str, Any],
    url_pages: str = "",
    corte: str = "MATUTINO"
) -> str:
    """Genera HTML completo y responsivo para el informe RADAR."""

    nombre_visible = _esc(contrato.get("nombre_visible", "Centinela RADAR"))
    correlativo = _esc(contrato.get("correlativo", "RADAR"))
    tablero = contrato.get("tablero_certificacion", {})
    top5 = contrato.get("top5_venezuela", [])
    top10 = contrato.get("top10_global", [])
    hallazgos = contrato.get("hallazgos", [])
    panel = contrato.get("panel_calidad", {})
    estados_medios = contrato.get("estados_medios", {})
    errores_medios = contrato.get("errores_medios", {})
    medios_config = contrato.get("medios_config", [])

    verde = tablero.get(_VERDE, 0)
    amarillo = tablero.get(_AMARILLO, 0)
    rojo = tablero.get(_ROJO, 0)
    total = tablero.get("total", verde + amarillo + rojo)
    
    # CORRECCIÓN: Contar solo hallazgos que realmente mencionan Venezuela
    n_hallazgos = sum(
        1 for h in hallazgos
        if "venezuela" in normalizar_titulo(h.get("titulo", "") or "")
        or any("venezuela" in normalizar_titulo(c or "") for c in h.get("conectores_activados", []))
    )

    ahora = datetime.now()
    mes = _MESES_ES.get(ahora.month, str(ahora.month))
    fecha = f"{ahora.day:02d} {mes} {ahora.year} · {ahora.strftime('%H:%M')} VET"
    generado_en = f"Generado el {ahora.day} de {mes} de {ahora.year} a las {ahora.strftime('%H:%M')}"

    corte_lower = corte.lower()
    tiempo = panel.get("tiempo_ejecucion", "")
    tiempo_str = f" · {tiempo}s" if tiempo else ""

    medios_chips = _render_medios_tablero(estados_medios, medios_config, errores_medios)
    top5_html = _render_top5(top5)
    top10_html = _render_top10(top10)
    todos_hallazgos_html = _render_todos_hallazgos(hallazgos)

    link_footer = ""
    if url_pages:
        link_footer = f'<br><a href="{url_pages}">🔗 {url_pages}</a>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Sala Situacional de Medios Internacionales · Venezuela">
    <title>RADAR | {correlativo}</title>
    <style>
        :root {{
            --verde: #16A34A; --amarillo: #D97706; --rojo: #DC2626;
            --azul: #1D4ED8; --header: #0F172A; --bg: #F1F5F9;
            --card: #FFFFFF; --text: #1E293B; --muted: #64748B;
            --border: #E2E8F0;
            --font: system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
        }}
        *{{box-sizing:border-box;margin:0;padding:0}}
        body{{font-family:var(--font);background:var(--bg);color:var(--text);font-size:16px;line-height:1.5}}

        /* HEADER */
        .hdr{{background:var(--header);color:#F8FAFC;padding:28px 20px;text-align:center}}
        .hdr-logo{{font-size:11px;text-transform:uppercase;letter-spacing:3px;color:#64748B;margin-bottom:10px}}
        .hdr h1{{font-size:clamp(18px,5vw,26px);font-weight:700;margin-bottom:12px}}
        .hdr-meta{{font-size:13px;color:#94A3B8;display:flex;justify-content:center;align-items:center;gap:12px;flex-wrap:wrap}}
        .badge{{display:inline-block;padding:3px 12px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px}}
        .badge-matutino{{background:#1D4ED8;color:#fff}}
        .badge-vespertino{{background:#7C3AED;color:#fff}}

        /* LAYOUT */
        .container{{max-width:940px;margin:0 auto;padding:0 16px 56px}}

        /* SEMÁFORO */
        .semaforo{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:24px 0}}
        .sem-card{{background:var(--card);border-radius:12px;padding:20px 12px;text-align:center;
                   box-shadow:0 1px 4px rgba(0,0,0,.08);border-top:4px solid}}
        .sem-card.v{{border-color:var(--verde)}} .sem-card.a{{border-color:var(--amarillo)}} .sem-card.r{{border-color:var(--rojo)}}
        .sem-num{{font-size:clamp(28px,9vw,46px);font-weight:800;line-height:1;margin-bottom:6px}}
        .sem-card.v .sem-num{{color:var(--verde)}} .sem-card.a .sem-num{{color:var(--amarillo)}} .sem-card.r .sem-num{{color:var(--rojo)}}
        .sem-label{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}}
        .sem-sub{{font-size:10px;color:var(--muted);margin-top:4px}}

        /* SECTIONS */
        section{{margin:36px 0}}
        .sec-title{{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;
                    color:var(--muted);margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid var(--border)}}
        p.empty{{color:var(--muted);font-size:14px;font-style:italic;padding:16px;background:var(--card);border-radius:8px}}

        /* TABLERO MEDIOS */
        .tablero-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:8px}}
        .medio-chip{{display:flex;align-items:center;gap:8px;padding:10px 14px;background:var(--card);
                     border-radius:8px;font-size:13px;box-shadow:0 1px 2px rgba(0,0,0,.06);border-left:3px solid}}
        .medio-chip.verde{{border-color:var(--verde)}} .medio-chip.amarillo{{border-color:var(--amarillo)}} .medio-chip.rojo{{border-color:var(--rojo)}}
        .dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
        .medio-chip.verde .dot{{background:var(--verde)}} .medio-chip.amarillo .dot{{background:var(--amarillo)}} .medio-chip.rojo .dot{{background:var(--rojo)}}
        .nombre{{font-weight:500}}

        /* TOP 5 */
        .top-list{{display:flex;flex-direction:column;gap:12px}}
        .top-item{{background:var(--card);border-radius:12px;padding:16px 20px;
                   box-shadow:0 1px 3px rgba(0,0,0,.08);display:flex;gap:16px;align-items:flex-start}}
        .top-rank{{font-size:32px;font-weight:800;color:var(--border);line-height:1;min-width:40px}}
        .top-item:nth-child(1) .top-rank{{color:#F59E0B}}
        .top-item:nth-child(2) .top-rank{{color:#94A3B8}}
        .top-item:nth-child(3) .top-rank{{color:#B45309}}
        .top-content{{flex:1;min-width:0}}
        .top-titulo{{font-size:15px;font-weight:600;margin-bottom:8px;line-height:1.4}}
        .top-meta{{display:flex;flex-wrap:wrap;gap:6px;align-items:center}}
        .tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;
               text-transform:uppercase;letter-spacing:.3px}}
        .tag-medio{{background:#EEF2FF;color:#3730A3}}
        .tag-favorable{{background:#DCFCE7;color:#166534}}
        .tag-critica{{background:#FEE2E2;color:#991B1B}}
        .tag-neutral{{background:#F1F5F9;color:#475569}}
        .tag-mixta{{background:#FEF3C7;color:#92400E}}
        .tag-gobierno{{background:#FEF3C7;color:#78350F}}
        .tag-oposicion{{background:#EDE9FE;color:#4C1D95}}
        .tag-pais_general{{background:#F0FDF4;color:#166534}}
        .tag-portada{{background:#0F172A;color:#F8FAFC}}
        .tag-fuente{{color:var(--azul);font-size:12px;text-decoration:none;font-weight:500}}
        .tag-fuente:hover{{text-decoration:underline}}

        /* TOP 10 */
        .global-list{{display:flex;flex-direction:column;gap:8px}}
        .global-item{{background:var(--card);border-radius:8px;padding:14px 16px;
                      display:flex;gap:14px;align-items:center;box-shadow:0 1px 2px rgba(0,0,0,.06);
                      border-left:3px solid transparent}}
        .global-item.venezolano{{border-color:var(--rojo)}}
        .global-rank{{font-size:20px;font-weight:800;color:#CBD5E1;min-width:28px;text-align:center;line-height:1}}
        .global-titulo{{font-size:14px;font-weight:500;flex:1}}
        .global-stats{{font-size:12px;color:var(--muted);white-space:nowrap}}

        /* TODOS LOS HALLAZGOS */
        .hallazgo-list{{display:flex;flex-direction:column;gap:8px}}
        .hallazgo-item{{background:var(--card);border-radius:8px;padding:12px 16px;
                       box-shadow:0 1px 2px rgba(0,0,0,.06);display:flex;gap:12px;align-items:flex-start;
                       border-left:3px solid var(--azul)}}
        .hallazgo-rank{{font-size:18px;font-weight:700;color:var(--border);min-width:24px;text-align:center;line-height:1}}
        .hallazgo-content{{flex:1;min-width:0}}
        .hallazgo-titulo{{font-size:14px;font-weight:500;margin-bottom:6px;line-height:1.4}}
        .hallazgo-meta{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:11px}}

        /* FOOTER */
        footer{{background:var(--header);color:#475569;padding:28px 20px;text-align:center;font-size:12px;margin-top:48px;line-height:2}}
        footer strong{{color:#94A3B8}}
        footer a{{color:#60A5FA;text-decoration:none}}
        footer a:hover{{text-decoration:underline}}

        /* RESPONSIVE */
        @media(max-width:480px){{
            .sem-sub{{display:none}}
            .top-item{{padding:12px 14px;gap:10px}}
            .top-rank{{font-size:24px;min-width:30px}}
            .global-stats{{display:none}}
            .tablero-grid{{grid-template-columns:repeat(2,1fr)}}
            .hallazgo-item{{padding:10px 12px;gap:8px}}
            .hallazgo-rank{{font-size:16px;min-width:20px}}
            .hallazgo-titulo{{font-size:13px}}
            .hallazgo-meta{{font-size:10px}}
        }}
        @media print{{
            body{{background:#fff}}
            .sem-card{{box-shadow:none;border:1px solid var(--border);border-top:4px solid}}
        }}
    </style>
</head>
<body>

<header class="hdr">
    <div class="hdr-logo">Sala Situacional · Medios Internacionales</div>
    <h1>📡 {nombre_visible}</h1>
    <div class="hdr-meta">
        <span class="badge badge-{corte_lower}">{corte}</span>
        <span>{fecha}</span>
        <span>{total}/35 medios · {n_hallazgos} hallazgos Venezuela</span>
    </div>
</header>

<div class="container">

    <div class="semaforo">
        <div class="sem-card v">
            <div class="sem-num">{verde}</div>
            <div class="sem-label">🟢 Con cobertura</div>
            <div class="sem-sub">Venezuela en agenda</div>
        </div>
        <div class="sem-card a">
            <div class="sem-num">{amarillo}</div>
            <div class="sem-label">🟡 Sin cobertura</div>
            <div class="sem-sub">Certificado · sin Venezuela</div>
        </div>
        <div class="sem-card r">
            <div class="sem-num">{rojo}</div>
            <div class="sem-label">🔴 No verificable</div>
            <div class="sem-sub">Error · paywall · timeout</div>
        </div>
    </div>

    <section>
        <h2 class="sec-title">🗺️ Tablero de medios certificados</h2>
        <div class="tablero-grid">
{medios_chips}
        </div>
    </section>

    <section>
        <h2 class="sec-title">🔝 Top 5 Venezuela · cobertura más destacada</h2>
        <div class="top-list">
{top5_html}
        </div>
    </section>

    <section>
        <h2 class="sec-title">📋 Todos los hallazgos sobre Venezuela</h2>
        <div class="hallazgo-list">
{todos_hallazgos_html}
        </div>
    </section>

    <section>
        <h2 class="sec-title">🌐 Agenda global · Top 10</h2>
        <div class="global-list">
{top10_html}
        </div>
    </section>

</div>

<footer>
    <strong>CENTINELA RADAR</strong> · {correlativo}{tiempo_str}<br>
    Pipeline automatizado de monitoreo de prensa internacional<br>
    {generado_en}{link_footer}
</footer>

</body>
</html>"""


def generar_mensaje_telegram(
    contrato: Dict[str, Any],
    url_pages: str = "",
    corte: str = "MATUTINO"
) -> str:
    """Genera el mensaje corto HTML para Telegram con el link al informe."""

    nombre_visible = contrato.get("nombre_visible", "Centinela RADAR")
    tablero = contrato.get("tablero_certificacion", {})
    top5 = contrato.get("top5_venezuela", [])
    hallazgos = contrato.get("hallazgos", [])

    verde = tablero.get(_VERDE, 0)
    amarillo = tablero.get(_AMARILLO, 0)
    rojo = tablero.get(_ROJO, 0)
    total = tablero.get("total", verde + amarillo + rojo)
    
    # CORRECCIÓN: Contar solo hallazgos que realmente mencionan Venezuela
    n_hallazgos = sum(
        1 for h in hallazgos
        if "venezuela" in normalizar_titulo(h.get("titulo", "") or "")
        or any("venezuela" in normalizar_titulo(c or "") for c in h.get("conectores_activados", []))
    )

    ahora = datetime.now()
    mes = _MESES_ES.get(ahora.month, str(ahora.month))
    fecha = f"{ahora.day:02d} {mes} {ahora.year} · {ahora.strftime('%H:%M')} VET"

    # Top 3 de Venezuela
    top_lines = []
    for item in top5[:3]:
        h = item.get("hallazgo", {})
        titulo = h.get("titulo", "Sin título")
        medio = h.get("medio_id", "")
        titulo_corto = (titulo[:65] + "…") if len(titulo) > 65 else titulo
        medio_str = f" <i>— {medio.upper()}</i>" if medio else ""
        top_lines.append(f"{item.get('rank', '?')}. {_esc(titulo_corto)}{medio_str}")

    top_block = "\n".join(top_lines) if top_lines else "Sin hallazgos destacados"

    link_block = ""
    if url_pages:
        link_block = f'\n\n🔗 <a href="{url_pages}">Ver informe completo →</a>'

    return (
        f'📡 <b>{_esc(nombre_visible)}</b> | <b>{corte}</b>\n'
        f'{fecha}\n'
        f'\n'
        f'📊 <b>{total}/35</b> medios certificados\n'
        f'🟢 {verde} con cobertura  🟡 {amarillo} sin cobertura  🔴 {rojo} no verificable\n'
        f'📰 {n_hallazgos} hallazgos Venezuela detectados\n'
        f'\n'
        f'📌 <b>Top Venezuela:</b>\n'
        f'{top_block}'
        f'{link_block}'
    )
