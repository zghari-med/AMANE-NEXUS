"""Service de gestion des analyses."""

from datetime import datetime
from ..models.analysis import Analysis
from ..models.video import Video
from ..models.user import User
from ..models.alert import Alert


class AnalysisService:
    """Service de gestion des analyses de vidéos."""

    @staticmethod
    def create_analysis(video_id: str, user: User) -> dict:
        """Crée une nouvelle analyse pour une vidéo."""
        try:
            video = Video.objects.get(id=video_id)

            # Vérifier les permissions
            if video.uploaded_by.id != user.id and user.role != 'admin':
                return {'error': 'Access denied', 'code': 403}

            # Vérifier que la vidéo n'est pas déjà en cours de traitement
            existing = Analysis.objects(video=video, status__in=['pending', 'processing']).first()
            if existing:
                return {'error': 'Video already being analyzed', 'code': 400}

            # Créer l'analyse
            analysis = Analysis(
                video=video,
                user=user,
                status='pending',
                camera_id='cam_01',
            )
            analysis.save()

            # Mettre à jour le statut de la vidéo
            video.status = 'processing'
            video.analysis_id = str(analysis.id)
            video.save()

            return {
                'analysis': analysis.to_dict(),
                'code': 201
            }
        except Video.DoesNotExist:
            return {'error': 'Video not found', 'code': 404}

    @staticmethod
    def get_analysis(analysis_id: str, user: User) -> dict:
        """Récupère une analyse."""
        try:
            analysis = Analysis.objects.get(id=analysis_id)

            # Vérifier les permissions
            if (analysis.user.id != user.id and
                user.role != 'admin' and
                not user.can_view_all_analyses):
                return {'error': 'Access denied', 'code': 403}

            return {'analysis': analysis.to_dict(), 'code': 200}
        except Analysis.DoesNotExist:
            return {'error': 'Analysis not found', 'code': 404}

    @staticmethod
    def list_analyses(user: User, skip: int = 0, limit: int = 20) -> dict:
        """Liste les analyses accessibles à l'utilisateur."""

        if user.role == 'admin':
            analyses = Analysis.objects.skip(skip).limit(limit).order_by('-created_at')
        else:
            analyses = Analysis.objects(user=user).skip(skip).limit(limit).order_by('-created_at')

        total = len(analyses)
        return {
            'analyses': [a.to_dict() for a in analyses],
            'total': total,
            'code': 200
        }

    @staticmethod
    def update_analysis_status(analysis_id: str, status: str, **kwargs) -> dict:
        """Met à jour le statut d'une analyse avec ses résultats."""
        try:
            analysis = Analysis.objects.get(id=analysis_id)

            analysis.status = status
            analysis.updated_at = datetime.utcnow()

            # Mettre à jour les résultats si fournis
            if 'total_events' in kwargs:
                analysis.total_events = kwargs['total_events']
            if 'falls_detected' in kwargs:
                analysis.falls_detected = kwargs['falls_detected']
            if 'crowds_detected' in kwargs:
                analysis.crowds_detected = kwargs['crowds_detected']
            if 'abandoned_objects' in kwargs:
                analysis.abandoned_objects = kwargs['abandoned_objects']
            if 'processing_time' in kwargs:
                analysis.processing_time = kwargs['processing_time']
            if 'average_fps' in kwargs:
                analysis.average_fps = kwargs['average_fps']
            if 'cpu_usage' in kwargs:
                analysis.cpu_usage = kwargs['cpu_usage']
            if 'events_timeline' in kwargs:
                analysis.events_timeline = kwargs['events_timeline']

            if status == 'completed':
                analysis.completed_at = datetime.utcnow()

            analysis.save()

            # Mettre à jour le statut de la vidéo aussi
            video = analysis.video
            video.status = 'completed' if status == 'completed' else 'processing'
            video.save()

            return {'analysis': analysis.to_dict(), 'code': 200}
        except Analysis.DoesNotExist:
            return {'error': 'Analysis not found', 'code': 404}

    @staticmethod
    def get_analysis_alerts(analysis_id: str, user: User) -> dict:
        """Récupère les alertes d'une analyse."""
        try:
            analysis = Analysis.objects.get(id=analysis_id)

            # Vérifier les permissions
            if (analysis.user.id != user.id and
                user.role != 'admin' and
                not user.can_view_all_analyses):
                return {'error': 'Access denied', 'code': 403}

            alerts = Alert.objects(analysis=analysis).order_by('-created_at')

            return {
                'alerts': [a.to_dict() for a in alerts],
                'total': len(alerts),
                'code': 200
            }
        except Analysis.DoesNotExist:
            return {'error': 'Analysis not found', 'code': 404}

    @staticmethod
    def get_statistics(user: User) -> dict:
        """Récupère les statistiques."""
        if user.role == 'admin':
            total_videos = Video.objects.count()
            total_analyses = Analysis.objects.count()
            total_alerts = Alert.objects.count()
            completed_analyses = Analysis.objects(status='completed').count()
        else:
            total_videos = Video.objects(uploaded_by=user).count()
            total_analyses = Analysis.objects(user=user).count()
            total_alerts = Alert.objects(user=user).count()
            completed_analyses = Analysis.objects(user=user, status='completed').count()

        # Compter par type d'alerte
        alerts_by_type = {}
        for alert_type in ['fall', 'crowding', 'abandoned_object']:
            if user.role == 'admin':
                count = Alert.objects(event_type=alert_type).count()
            else:
                count = Alert.objects(user=user, event_type=alert_type).count()
            alerts_by_type[alert_type] = count

        return {
            'statistics': {
                'total_videos': total_videos,
                'total_analyses': total_analyses,
                'completed_analyses': completed_analyses,
                'total_alerts': total_alerts,
                'alerts_by_type': alerts_by_type,
            },
            'code': 200
        }
