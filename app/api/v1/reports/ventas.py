"""
Reporte de ventas — exportación CSV y PDF.
Filtros: rango de fechas, vendedor, estado de orden.
"""
import csv
import io
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.order import Order, OrderItem, OrderStatus
from app.models.client import Client
from app.models.user import User

router = APIRouter(prefix="/ventas", tags=["Reports - Ventas"])

# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

@router.get("", summary="Exportar ventas a CSV")
async def export_ventas_csv(
    date_from: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    salesperson_id: Optional[str] = Query(None, description="Filtrar por vendedor"),
    status: Optional[str] = Query(None, description="Estado: pending, confirmed, delivered, cancelled"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta el detalle de órdenes con sus ítems a CSV.
    Una fila por ítem de orden — incluye datos del cliente y vendedor.
    """
    orders = await _query_orders(
        tenant_id=current_user["tenant_id"],
        date_from=date_from,
        date_to=date_to,
        salesperson_id=salesperson_id,
        status=status,
        db=db,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # Encabezados
    writer.writerow([
        "orden_id", "numero_orden", "fecha_orden", "estado", "origen",
        "cliente", "telefono_cliente", "ciudad", "zona",
        "vendedor", "sku", "producto", "cantidad",
        "precio_unitario", "descuento_%", "total_item",
        "subtotal_orden", "descuento_orden", "total_orden",
    ])

    for order in orders:
        client_name  = order.client.business_name if order.client else ""
        client_phone = order.client.phone if order.client else ""
        client_city  = order.client.city if order.client else ""
        client_zone  = order.client.zone_name if order.client else ""
        seller_name  = order.salesperson.name if order.salesperson else "Agente IA"

        if not order.items:
            # Orden sin ítems — una fila con campos de producto vacíos
            writer.writerow([
                str(order.id), order.order_number or "", order.order_date,
                order.status.value, order.source.value,
                client_name, client_phone, client_city, client_zone,
                seller_name, "", "", "", "", "", "",
                _fmt(order.subtotal), _fmt(order.discount_amount), _fmt(order.total_amount),
            ])
        else:
            for item in order.items:
                product_name = item.product.name if item.product else str(item.product_id)
                sku          = item.product.sku  if item.product else ""
                writer.writerow([
                    str(order.id), order.order_number or "", order.order_date,
                    order.status.value, order.source.value,
                    client_name, client_phone, client_city, client_zone,
                    seller_name, sku, product_name,
                    _fmt(item.quantity), _fmt(item.unit_price),
                    _fmt(item.discount_percent), _fmt(item.total_price),
                    _fmt(order.subtotal), _fmt(order.discount_amount), _fmt(order.total_amount),
                ])

    output.seek(0)
    filename = _filename("ventas", date_from, date_to, "csv")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

@router.get("/pdf", summary="Exportar resumen de ventas a PDF")
async def export_ventas_pdf(
    date_from: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    salesperson_id: Optional[str] = Query(None, description="Filtrar por vendedor"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta un resumen ejecutivo de ventas a PDF.
    Incluye totales por vendedor y tabla de órdenes confirmadas/entregadas.
    """
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    orders = await _query_orders(
        tenant_id=current_user["tenant_id"],
        date_from=date_from,
        date_to=date_to,
        salesperson_id=salesperson_id,
        status=None,
        db=db,
    )

    # Filtrar solo confirmadas/entregadas para el resumen
    orders_resumen = [o for o in orders if o.status.value in ("confirmed", "delivered", "dispatched")]

    # Calcular totales por vendedor
    totales: dict[str, dict] = {}
    gran_total = 0.0
    for order in orders_resumen:
        seller = order.salesperson.name if order.salesperson else "Agente IA"
        if seller not in totales:
            totales[seller] = {"ordenes": 0, "total": 0.0}
        totales[seller]["ordenes"] += 1
        totales[seller]["total"] += order.total_amount
        gran_total += order.total_amount

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                            leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []

    # Título
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=16, spaceAfter=6)
    sub_style   = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9,
                                 textColor=colors.grey, spaceAfter=12)
    story.append(Paragraph("Reporte de Ventas", title_style))
    periodo = f"{date_from or 'Inicio'} — {date_to or date.today()}"
    story.append(Paragraph(f"Período: {periodo}  |  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))

    # Resumen por vendedor
    story.append(Paragraph("Resumen por vendedor", styles["Heading2"]))
    story.append(Spacer(1, 4))
    resumen_data = [["Vendedor", "Órdenes", "Total (COP)"]]
    for seller, d in sorted(totales.items(), key=lambda x: -x[1]["total"]):
        resumen_data.append([seller, str(d["ordenes"]), f"${d['total']:,.0f}"])
    resumen_data.append(["TOTAL", str(len(orders_resumen)), f"${gran_total:,.0f}"])

    resumen_table = Table(resumen_data, colWidths=[3*inch, 1.2*inch, 1.8*inch])
    resumen_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1E40AF")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ALIGN",         (1, 0), (-1, -1), "RIGHT"),
        ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#DBEAFE")),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(resumen_table)
    story.append(Spacer(1, 16))

    # Detalle de órdenes
    story.append(Paragraph(f"Detalle de órdenes ({len(orders_resumen)} registros)", styles["Heading2"]))
    story.append(Spacer(1, 4))

    detalle_data = [["Número", "Fecha", "Estado", "Cliente", "Ciudad", "Vendedor", "Total (COP)"]]
    for order in orders_resumen[:200]:   # máximo 200 filas en PDF
        detalle_data.append([
            order.order_number or str(order.id)[:8],
            str(order.order_date),
            order.status.value,
            (order.client.business_name if order.client else "")[:30],
            (order.client.city if order.client else "")[:15],
            (order.salesperson.name if order.salesperson else "Agente IA")[:20],
            f"${order.total_amount:,.0f}",
        ])

    col_w = [1.2*inch, 0.9*inch, 0.9*inch, 2.8*inch, 1.2*inch, 1.8*inch, 1.2*inch]
    detalle_table = Table(detalle_data, colWidths=col_w, repeatRows=1)
    detalle_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1E40AF")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ALIGN",         (6, 0), (6, -1),  "RIGHT"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(detalle_table)

    if len(orders_resumen) > 200:
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"* Mostrando 200 de {len(orders_resumen)} órdenes. Descarga el CSV para el listado completo.",
            ParagraphStyle("note", parent=styles["Normal"], fontSize=7, textColor=colors.grey),
        ))

    doc.build(story)
    buffer.seek(0)
    filename = _filename("ventas", date_from, date_to, "pdf")
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _query_orders(
    tenant_id: str,
    date_from: Optional[date],
    date_to: Optional[date],
    salesperson_id: Optional[str],
    status: Optional[str],
    db: AsyncSession,
) -> list[Order]:
    filters = [Order.tenant_id == tenant_id]
    if date_from:
        filters.append(Order.order_date >= date_from)
    if date_to:
        filters.append(Order.order_date <= date_to)
    if salesperson_id:
        filters.append(Order.salesperson_id == salesperson_id)
    if status:
        try:
            filters.append(Order.status == OrderStatus(status))
        except ValueError:
            pass  # estado inválido → ignorar filtro

    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.client),
            selectinload(Order.salesperson),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
        .where(and_(*filters))
        .order_by(Order.order_date.desc())
    )
    return result.scalars().all()


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _filename(report: str, date_from, date_to, ext: str) -> str:
    d_from = str(date_from or "inicio").replace("-", "")
    d_to   = str(date_to or date.today()).replace("-", "")
    return f"{report}_{d_from}_{d_to}.{ext}"
