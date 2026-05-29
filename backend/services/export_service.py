"""Service d'export des données."""

import json
import csv
from datetime import datetime
from io import StringIO, BytesIO
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from ..models.analysis import Analysis
from ..models.alert import Alert


class ExportService:
    """Service d'export des données d'analyse."""

    @staticmethod
    def export_to_csv(analysis_id: str) -> dict:
        """Exporte les alertes d'une analyse en CSV."""
        try:
            analysis = Analysis.objects.get(id=analysis_id)
            alerts = Alert.objects(analysis=analysis).order_by('created_at')

            # Créer le CSV
            output = StringIO()
            writer = csv.writer(output)

            # En-têtes
            writer.writerow([
                'Alert ID', 'Event Type', 'Risk Level', 'Frame ID',
                'Timestamp (s)', 'Status', 'Created At'
            ])

            # Données
            for alert in alerts:
                writer.writerow([
                    alert.id,
                    alert.event_type,
                    alert.risk_level,
                    alert.frame_id or '',
                    alert.timestamp or '',
                    alert.status,
                    alert.created_at.isoformat(),
                ])

            csv_content = output.getvalue()
            return {
                'content': csv_content,
                'filename': "analysis_{analysis.id}_export.csv",
                'code': 200
            }
        except Analysis.DoesNotExist:
            return {'error': 'Analysis not found', 'code': 404}

    @staticmethod
    def export_to_json(analysis_id: str) -> dict:
        """Exporte les alertes d'une analyse en JSON."""
        try:
            analysis = Analysis.objects.get(id=analysis_id)
            alerts = Alert.objects(analysis=analysis)

            export_data = {
                'analysis': analysis.to_dict(),
                'video': analysis.video.to_dict(),
                'alerts': [a.to_dict() for a in alerts],
                'export_timestamp': datetime.utcnow().isoformat(),
            }

            json_content = json.dumps(export_data, indent=2, default=str)
            return {
                'content': json_content,
                'filename': "analysis_{analysis.id}_export.json",
                'code': 200
            }
        except Analysis.DoesNotExist:
            return {'error': 'Analysis not found', 'code': 404}

    @staticmethod
    def export_to_pdf(analysis_id: str) -> dict:
        """Exporte les résultats d'une analyse en PDF."""
        try:
            analysis = Analysis.objects.get(id=analysis_id)
            alerts = Alert.objects(analysis=analysis)

            # Créer le PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=20,
                leftMargin=20,
                topMargin=20,
                bottomMargin=20
            )

            elements = []
            styles = getSampleStyleSheet()

            # Titre
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1e40a'),
                spaceAfter=30,
            )
            title = Paragraph(
                "Rapport d'Analyse Vidéo",
                title_style
            )
            elements.append(title)

            # Informations générales
            info_data = [
                ['Vidéo', analysis.video.title],
                ['Statut', analysis.status],
                ['Date d\'analyse', analysis.created_at.strftime('%d/%m/%Y %H:%M')],
                ['Durée du traitement', "{analysis.processing_time:.2f}s" if analysis.processing_time else 'N/A'],
                ['FPS moyen', "{analysis.average_fps:.1f}" if analysis.average_fps else 'N/A'],
            ]

            info_table = Table(info_data, colWidths=[150, 250])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e0e7f')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 20))

            # Résumé des résultats
            summary_title = Paragraph("Résumé des Détections", styles['Heading2'])
            elements.append(summary_title)

            summary_data = [
                ['Type d\'événement', 'Nombre'],
                ['Chutes détectées', str(analysis.falls_detected)],
                ['Attroupements détectés', str(analysis.crowds_detected)],
                ['Objets abandonnés', str(analysis.abandoned_objects)],
                ['Total d\'événements', str(analysis.total_events)],
            ]

            summary_table = Table(summary_data, colWidths=[250, 150])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 20))

            # Détails des alertes si nombreuses
            if alerts.count() > 0:
                elements.append(PageBreak())
                alerts_title = Paragraph("Détails des Alertes", styles['Heading2'])
                elements.append(alerts_title)

                alerts_data = [
                    ['Type', 'Niveau de Risque', 'Statut', 'Heure']
                ]

                for alert in alerts[:20]:  # Limiter à 20 alertes par page
                    alerts_data.append([
                        alert.event_type,
                        alert.risk_level,
                        alert.status,
                        alert.created_at.strftime('%H:%M:%S'),
                    ])

                alerts_table = Table(alerts_data, colWidths=[100, 120, 100, 100])
                alerts_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40a')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ]))
                elements.append(alerts_table)

            # Générer le PDF
            doc.build(elements)

            pdf_content = buffer.getvalue()
            buffer.close()

            return {
                'content': pdf_content,
                'filename': "analysis_{analysis.id}_report.pd",
                'code': 200
            }
        except Analysis.DoesNotExist:
            return {'error': 'Analysis not found', 'code': 404}
        except Exception:
            return {'error': 'PDF generation failed: {str(e)}', 'code': 500}
