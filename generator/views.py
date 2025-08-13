# generator/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from scripts.models import WorkoutTemplate
from .models import WorkoutSession
from .services import FlexibleWorkoutGenerator
from .serializers import WorkoutSessionSerializer

class WorkoutGeneratorViewSet(viewsets.ViewSet):
    """Smart workout generation with custom duration support"""
    
    @action(detail=False, methods=['post'])
    def generate_workout(self, request):
        """Generate a smart workout with custom duration"""
        training_type = request.data.get('training_type')
        goal = request.data.get('goal', 'allround')
        target_duration = request.data.get('target_duration', 60.0)  # NEW: Accept target_duration
        
        if not training_type:
            return Response({
                'error': 'training_type is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate target_duration
        try:
            target_duration = float(target_duration)
            if target_duration < 15 or target_duration > 70:
                return Response({
                    'error': 'target_duration must be between 15 and 70 minutes'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                'error': 'target_duration must be a valid number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            generator = FlexibleWorkoutGenerator()
            
            # Use the new method with duration support
            workout_data = generator.generate_workout_with_duration(
                training_type, 
                goal, 
                target_duration
            )
            
            return Response({
                'success': True,
                'workout': workout_data,
                'message': f"Generated {workout_data['time_status']} workout"
            })
            
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Generation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def preview_template(self, request):
        """Preview workout template structure"""
        training_type = request.query_params.get('training_type')
        if not training_type:
            return Response({'error': 'training_type parameter required'}, status=400)
        
        templates = WorkoutTemplate.objects.filter(
            training_type=training_type
        ).order_by('sequence_order').prefetch_related('alternative_categories')
        
        template_data = []
        for template in templates:
            alternatives = list(template.alternative_categories.values('id', 'display_name'))
            
            template_data.append({
                'sequence_order': template.sequence_order,
                'primary_category': {
                    'id': template.primary_category.id,
                    'display_name': template.primary_category.display_name,
                    'difficulty_level': template.primary_category.difficulty_level
                },
                'alternatives': alternatives,
                'is_required': template.is_required,
                'requires_surprise_round': template.requires_surprise_round,
                'requires_transition': template.requires_transition
            })
        
        return Response({
            'training_type': training_type,
            'template': template_data
        })

class WorkoutSessionViewSet(viewsets.ModelViewSet):  # Changed from ReadOnlyModelViewSet
    """
    Full CRUD operations for generated workouts
    
    CRUD Operations Available:
    - GET /sessions/ - List all sessions
    - GET /sessions/{id}/ - Get specific session
    - PUT /sessions/{id}/ - Full update of session
    - PATCH /sessions/{id}/ - Partial update (notes, is_used, compiled_script, etc.)
    - DELETE /sessions/{id}/ - Delete session
    """
    queryset = WorkoutSession.objects.all()
    serializer_class = WorkoutSessionSerializer
    
    def get_queryset(self):
        """Filter sessions based on query parameters"""
        queryset = super().get_queryset()
        
        # Filter by training type
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type=training_type)
        
        # Filter by goal
        goal = self.request.query_params.get('goal')
        if goal:
            queryset = queryset.filter(goal=goal)
        
        # Filter by usage status
        is_used = self.request.query_params.get('is_used')
        if is_used is not None:
            queryset = queryset.filter(is_used=is_used.lower() == 'true')
        
        # Search in title and notes
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(notes__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a workout session
        Also deletes associated SessionScript records automatically (CASCADE)
        """
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({
                'success': True,
                'message': 'Workout session deleted successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f'Failed to delete session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """
        Full update of workout session
        Supports updating: notes, is_used, compiled_script, title
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Validate updateable fields
        allowed_fields = {'notes', 'is_used', 'compiled_script', 'title'}
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(instance, data=update_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'success': True,
            'message': 'Workout session updated successfully',
            'data': serializer.data
        })
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partial update (PATCH) - most common for updating notes and usage status
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def mark_used(self, request, pk=None):
        """
        Convenience action to mark a session as used/unused
        POST /sessions/{id}/mark_used/
        Body: { "is_used": true }
        """
        session = self.get_object()
        is_used = request.data.get('is_used', True)
        
        session.is_used = is_used
        session.save(update_fields=['is_used'])
        
        return Response({
            'success': True,
            'message': f'Session marked as {"used" if is_used else "unused"}',
            'is_used': session.is_used
        })
    
    @action(detail=True, methods=['post'])
    def update_notes(self, request, pk=None):
        """
        Convenience action to update session notes
        POST /sessions/{id}/update_notes/
        Body: { "notes": "New notes content" }
        """
        session = self.get_object()
        notes = request.data.get('notes', '')
        
        session.notes = notes
        session.save(update_fields=['notes'])
        
        return Response({
            'success': True,
            'message': 'Session notes updated',
            'notes': session.notes
        })