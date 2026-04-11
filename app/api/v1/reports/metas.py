"""
Reporte de metas — exportación CSV y PDF.
Incluye meta, avance real y proyección al cierre del período.
"""
import csv
import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.goal import SalesGoal, GoalProgress, GoalPeriodType
from app.models.user import User

router = APIRouter(prefix="/metas", tags=["Reports - Metas"])


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

@router.get("", summary="Exportar metas y avance a CSV")
async def export_metas_csv(
    period_type: Optional[str] = Query(None, description="Tipo: daily, weekly, monthly, quarterly"),
    date_from: Optional[date] = Query(None, description="Período desde (period_start >= date_from)"),
    date_to: Optional[date] = Query(None, description="Período hasta (period_start <= date_to)"),
    salesperson_id: Optional[str] = Query(None, description="Filtrar por vendedor"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta metas de ventas con el último snapshot de avance disponible.
    Incluye porcentajes de cumplimiento y proyección al cierre.
    """
    goals = await _query_goals(
        tenant_id=current_user["tenant_id"],
        period_type=period_type,
        date_from=date_from,
        date_to=date_to,
        salesperson_id=salesperson_id,
        db=db,
    )

    # Cargar último snapshot de progreso por meta
    goal_ids = [g.id for g in goals]
    progress_map: dict = {}
    if goal_ids:
        # Subconsulta: max snapshot_date por goal_id
        from sqlalchemy import func
        subq = (
            select(GoalProgress.goal_id, func.max(GoalProgress.snapshot_date).label("max_date"))
            .where(GoalProgress.goal_id.in_(goal_ids))
            .group_by(GoalProgress.goal_id)
            .subquery()
        )
        prog_result = await db.execute(
            select(GoalProgress).join(
                subq,
                and_(
                    GoalProgress.goal_id == subq.c.goal_id,
                    GoalProgress.snapshot_date == subq.c.max_date,
                ),
            )
        )
        for p in prog_result.scalars().all():
            progress_map[str(p.goal_id)] = p

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "meta_id", "vendedor", "tipo_periodo", "inicio_periodo", "fin_periodo",
        "meta_monto_cop", "meta_visitas", "meta_visitas_efectivas",
        "meta_clientes_activos", "meta_clientes_nuevos",
        "avance_monto_cop", "avance_visitas", "avance_visitas_efectivas",
        "avance_clientes_activos",
        "pct_monto", "pct_visitas",
        "proyeccion_monto_cop", "proyeccion_pct",
        "dias_transcurridos", "dias_restantes",
        "snapshot_fecha", "notas",
    ])

    for goal in goals:
        seller_name = goal.salesperson.name if goal.salesperson else str(goal.salesperson_id)
        prog = progress_map.get(str(goal.id))
        writer.writerow([
            str(goal.id), seller_name,
            goal.period_type.value, goal.period_start, goal.period_end,
            _fmt(goal.target_amount), goal.target_visits or "",
            goal.target_effective_visits or "", goal.target_active_clients or "",
            goal.target_new_clients or "",
            # Avance (del último snapshot)
            _fmt(prog.actual_amount)          if prog else "",
            prog.actual_visits               if prog else "",
            prog.actual_effective_visits     if prog else "",
            prog.actual_active_clients       if prog else "",
            f"{prog.pct_amount:.1f}%"        if prog else "",
            f"{prog.pct_visits:.1f}%"        if prog else "",
            _fmt(prog.projected_amount)      if prog else "",
            f"{prog.projected_pct:.1f}%"     if (prog and prog.projected_pct) else "",
            prog.days_elapsed                if prog else "",
            prog.days_remaining              if prog else "",
            prog.snapshot_date               if prog else "",
            goal.notes or "",
        ])

    output.seek(0)
    today = date.today().strftime("%Y%m%d")
    filename = f"metas_{today}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

@router.get("/pdf", summary="Exportar resumen de metas a PDF")
async def export_metas_pdf(
    period_type: Optional[str] = Query("monthly", description="Tipo: daily, weekly, monthly, quarterly"),
    date_from: Optional[date] = Query(None, description="Período desde"),
    date_to: Optional[date] = Query(None, description="Período hasta"),
    salesperson_id: Optional[str] = Query(None, description="Filtrar por vendedor"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exporta un resumen visual de metas vs avance a PDF.
    Diseñado para ser compartido con la gerencia.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.graphics.shapes import Drawing, Rect, String as RLString
    from reportlab.graphics.charts.barcharts import VerticalBarChart

    goals = await _query_goals(
        tenant_id=current_user["tenant_id"],
        period_type=period_type,
        date_from=date_from,
        date_to=date_to,
        salesperson_id=salesperson_id,
        db=db,
    )

    # Cargar último snapshot de progreso
    goal_ids = [g.id for g in goals]
    progress_map: dict = {}
    if goal_ids:
        from sqlalchemy import func
        subq = (
            select(GoalProgress.goal_id, func.max(GoalProgress.snapshot_date).label("max_date"))
            .where(GoalProgress.goal_id.in_(goal_ids))
            .group_by(GoalProgress.goal_id)
            .subquery()
        )
        prog_result = await db.execute(
            select(GoalProgress).join(
                subq,
                and_(
                    GoalProgress.goal_id == subq.c.goal_id,
                    GoalProgress.snapshot_date == subq.c.max_date,
                ),
            )
        )
        for p in prog_result.scalars().all():
            progress_map[str(p.goal_id)] = p

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=0.6*inch, rightMargin=0.6*inch,
                            topMargin=0.6*inch, bottomMargin=0.6*inch)
    styles = getSampleStyleSheet()
    story = []

    # Título
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=15, spaceAfter=4)
    sub_style   = ParagraphStyle("sub", parent=styles["Normal"], fontSize=8,
                                 textColor=colors.grey, spaceAfter=14)
    story.append(Paragraph("Reporte de Metas de Ventas", title_style))
    periodo_label = f"{date_from or 'Inicio'} — {date_to or date.today()}"
    story.append(Paragraph(
        f"Período: {periodo_label}  |  Tipo: {period_type or 'todos'}  |  "
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style,
    ))

    if not goals:
        story.append(Paragraph("No hay metas para el período seleccionado.", styles["Normal"]))
    else:
        # Tabla principal
        header = [
            "Vendedor", "Período", "Meta\n(COP)", "Avance\n(COP)", "% Monto",
            "Visitas\nmeta/real", "Proyección\n(COP)", "% Proy.",
        ]
        table_data = [header]

        for goal in goals:
            prog = progress_map.get(str(goal.id))
            seller_name  = (goal.salesperson.name if goal.salesperson else "—")[:22]
            periodo_str  = f"{goal.period_start}\n{goal.period_end}"
            meta_monto   = f"${goal.target_amount:,.0f}" if goal.target_amount else "—"
            avance_monto = f"${prog.actual_amount:,.0f}" if prog else "—"
            pct_monto    = f"{prog.pct_amount:.0f}%" if prog else "—"
            visitas      = (f"{goal.target_visits or '—'} / {prog.actual_visits if prog else '—'}")
            proyeccion   = f"${prog.projected_amount:,.0f}" if (prog and prog.projected_amount) else "—"
            pct_proy     = f"{prog.projected_pct:.0f}%" if (prog and prog.projected_pct) else "—"

            row = [seller_name, periodo_str, meta_monto, avance_monto,
                   pct_monto, visitas, proyeccion, pct_proy]

            # Color de fila según cumplimiento
            table_data.append(row)

        col_widths = [1.6*inch, 0.9*inch, 1.0*inch, 1.0*inch, 0.6*inch, 0.85*inch, 1.0*inch, 0.6*inch]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Estilos base
        ts = [
            ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#1E40AF")),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("ALIGN",        (2, 0), (-1, -1), "RIGHT"),
            ("ALIGN",        (0, 0), (1, -1),  "LEFT"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]

        # Colorear celdas de % monto según desempeño
        for i, goal in enumerate(goals, start=1):
            prog = progress_map.get(str(goal.id))
            if prog:
                pct = prog.pct_amount
                cell_color = (
                    colors.HexColor("#DCFCE7") if pct >= 90 else   # verde
                    colors.HexColor("#FEF9C3") if pct >= 60 else   # amarillo
                    colors.HexColor("#FEE2E2")                       # rojo
                )
                ts.append(("BACKGROUND", (4, i), (4, i), cell_color))

        table.setStyle(TableStyle(ts))
        story.append(table)

        # Nota al pie
        story.append(Spacer(1, 10))
        note_style = ParagraphStyle("note", parent=styles["Normal"], fontSize=7, textColor=colors.grey)
        story.append(Paragraph(
            "🟢 ≥ 90%  🟡 60–89%  🔴 < 60%  |  "
            "Avance calculado al último snapshot disponible. "
            "Para datos en tiempo real descarga el CSV.",
            note_style,
        ))

    doc.build(story)
    buffer.seek(0)
    today = date.today().strftime("%Y%m%d")
    filename = f"metas_{today}.pdf"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _query_goals(
    tenant_id: str,
    period_type: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
    salesperson_id: Optional[str],
    db: AsyncSession,
) -> list[SalesGoal]:
    filters = [SalesGoal.tenant_id == tenant_id, SalesGoal.is_active == True]
    if period_type:
        try:
            filters.append(SalesGoal.period_type == GoalPeriodType(period_type))
        except ValueError:
            pass
    if date_from:
        filters.append(SalesGoal.period_start >= date_from)
    if date_to:
        filters.append(SalesGoal.period_start <= date_to)
    if salesperson_id:
        filters.append(SalesGoal.salesperson_id == salesperson_id)

    result = await db.execute(
        select(SalesGoal)
        .options(selectinload(SalesGoal.salesperson))
        .where(and_(*filters))
        .order_by(SalesGoal.period_start.desc(), SalesGoal.salesperson_id)
    )
    return result.scalars().all()


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
