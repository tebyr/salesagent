"""
Reporte de clientes — exportación CSV.
Incluye datos de contacto, segmentación y métricas de compra.
"""
import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.client import Client
from app.models.user import User

router = APIRouter(prefix="/clientes", tags=["Reports - Clientes"])


@router.get("", summary="Exportar clientes a CSV")
async def export_clientes_csv(
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    salesperson_id: Optional[str] = Query(None, description="Filtrar por vendedor asignado"),
    zone_name: Optional[str] = Query(None, description="Filtrar por zona (texto)"),
    segment: Optional[str] = Query(None, description="Filtrar por segmento: A, B, C"),
    whatsapp_opt_in: Optional[bool] = Query(None, description="Filtrar por opt-in WhatsApp"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta el directorio completo de clientes con sus métricas de compra.
    Útil para análisis de cartera, segmentación y campañas.
    """
    filters = [Client.tenant_id == current_user["tenant_id"]]
    if is_active is not None:
        filters.append(Client.is_active == is_active)
    if salesperson_id:
        filters.append(Client.salesperson_id == salesperson_id)
    if zone_name:
        filters.append(Client.zone_name == zone_name)
    if segment:
        filters.append(Client.segment == segment)
    if whatsapp_opt_in is not None:
        filters.append(Client.whatsapp_opt_in == whatsapp_opt_in)

    result = await db.execute(
        select(Client)
        .options(selectinload(Client.zone))
        .where(and_(*filters))
        .order_by(Client.business_name)
    )
    clients = result.scalars().all()

    # Cargar vendedores en una sola query para evitar N+1
    salesperson_ids = list({str(c.salesperson_id) for c in clients if c.salesperson_id})
    sellers: dict[str, str] = {}
    if salesperson_ids:
        sellers_result = await db.execute(
            select(User.id, User.name).where(User.id.in_(salesperson_ids))
        )
        sellers = {str(row.id): row.name for row in sellers_result.all()}

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id", "nombre_negocio", "propietario", "nit_cc",
        "telefono", "email", "direccion", "ciudad", "barrio", "zona",
        "segmento", "canal", "activo", "whatsapp_opt_in",
        "vendedor_asignado",
        "ultima_compra", "frecuencia_dias", "ticket_promedio_cop",
        "total_compras", "total_monto_cop",
        "external_id", "external_source",
        "etiquetas", "categorias_preferidas", "notas",
    ])

    for c in clients:
        zone_display = c.zone.name if c.zone else (c.zone_name or "")
        seller_name  = sellers.get(str(c.salesperson_id), "") if c.salesperson_id else ""
        writer.writerow([
            str(c.id), c.business_name, c.owner_name or "", c.nit_cc or "",
            c.phone, c.email or "", c.address or "", c.city or "",
            c.neighborhood or "", zone_display,
            c.segment or "", c.channel_type or "", c.is_active, c.whatsapp_opt_in,
            seller_name,
            c.last_purchase_date or "", c.avg_purchase_frequency_days or "",
            f"{c.avg_ticket_amount:.0f}" if c.avg_ticket_amount else "",
            c.total_purchases_count or 0,
            f"{c.total_purchases_amount:.0f}" if c.total_purchases_amount else "",
            c.external_id or "", c.external_source or "",
            "|".join(c.tags or []),
            "|".join(c.preferred_categories or []),
            (c.notes or "").replace("\n", " "),
        ])

    output.seek(0)
    today = date.today().strftime("%Y%m%d")
    filename = f"clientes_{today}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
