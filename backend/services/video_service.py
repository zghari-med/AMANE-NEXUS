"""Service de gestion des vidéos."""

import os
import cv2
from datetime import datetime
from werkzeug.utils import secure_filename
from ..models.video import Video
from ..models.user import User


ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}
UPLOAD_FOLDER = 'backend/uploads'
MAX_FILE_SIZE = 1024 * 1024 * 500  # 500 MB


class VideoService:
    """Service de gestion des vidéos."""

    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Vérifie si le fichier a une extension autorisée."""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @staticmethod
    def get_video_metadata(filepath: str) -> dict:
        """Extrait les métadonnées d'une vidéo."""
        try:
            cap = cv2.VideoCapture(filepath)

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            duration = frame_count / fps if fps > 0 else 0

            cap.release()

            return {
                'duration': duration,
                'fps': fps,
                'resolution': f"{width}x{height}",
                'frame_count': frame_count,
            }
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def upload_video(file, user: User, title: str = "", description: str = "") -> dict:
        """Upload une vidéo."""

        # Vérifier l'extension
        if not file or not VideoService.allowed_file(file.filename):
            return {'error': 'Invalid file format', 'code': 400}

        # Vérifier la taille
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return {'error': 'File too large', 'code': 413}

        # Créer le dossier s'il n'existe pas
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Sauvegarder le fichier
        filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Extraire les métadonnées
        metadata = VideoService.get_video_metadata(filepath)

        if 'error' in metadata:
            os.remove(filepath)
            return {'error': 'Failed to process video', 'code': 400}

        # Créer l'objet vidéo dans MongoDB
        video = Video(
            title=title or file.filename,
            description=description,
            filename=filename,
            filepath=filepath,
            uploaded_by=user,
            duration=metadata['duration'],
            fps=int(metadata['fps']),
            resolution=metadata['resolution'],
            file_size=file_size,
            status='uploaded',
        )
        video.save()

        return {
            'video': video.to_dict(),
            'code': 201
        }

    @staticmethod
    def get_video(video_id: str, user: User) -> dict:
        """Récupère une vidéo."""
        try:
            video = Video.objects.get(id=video_id)

            # Vérifier les permissions
            if video.uploaded_by.id != user.id and not user.can_view_all_analyses:
                return {'error': 'Access denied', 'code': 403}

            return {'video': video.to_dict(), 'code': 200}
        except Video.DoesNotExist:
            return {'error': 'Video not found', 'code': 404}

    @staticmethod
    def list_videos(user: User, skip: int = 0, limit: int = 20) -> dict:
        """Liste les vidéos accessibles à l'utilisateur."""

        if user.role == 'admin':
            # Les admins voient toutes les vidéos
            videos = Video.objects.skip(skip).limit(limit).order_by('-created_at')
        else:
            # Les utilisateurs ne voient que leurs vidéos et celles partagées
            videos = Video.objects(
                uploaded_by=user
            ).skip(skip).limit(limit).order_by('-created_at')

        total = len(videos)
        return {
            'videos': [v.to_dict() for v in videos],
            'total': total,
            'code': 200
        }

    @staticmethod
    def delete_video(video_id: str, user: User) -> dict:
        """Supprime une vidéo."""
        try:
            video = Video.objects.get(id=video_id)

            # Vérifier les permissions (seulement le propriétaire ou un admin)
            if video.uploaded_by.id != user.id and user.role != 'admin':
                return {'error': 'Access denied', 'code': 403}

            # Supprimer le fichier
            if os.path.exists(video.filepath):
                os.remove(video.filepath)

            # Supprimer de la base de données
            video.delete()

            return {'message': 'Video deleted', 'code': 200}
        except Video.DoesNotExist:
            return {'error': 'Video not found', 'code': 404}

    @staticmethod
    def update_video_status(video_id: str, status: str) -> dict:
        """Met à jour le statut d'une vidéo."""
        try:
            video = Video.objects.get(id=video_id)
            video.status = status
            video.updated_at = datetime.utcnow()

            if status == 'completed':
                video.processed_at = datetime.utcnow()

            video.save()

            return {'video': video.to_dict(), 'code': 200}
        except Video.DoesNotExist:
            return {'error': 'Video not found', 'code': 404}
