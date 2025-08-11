# generator/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from scripts.models import WorkoutTemplate
from .models import WorkoutSession
from .services import FlexibleWorkoutGenerator
from .serializers import WorkoutSessionSerializer

class WorkoutGeneratorViewSet(viewsets.ViewSet):
    """Smart workout generation"""
    
    @action(detail=False, methods=['post'])
    def generate_workout(self, request):
        """Generate a smart 1-hour workout"""
        training_type = request.data.get('training_type')
        goal = request.data.get('goal', 'allround')
        
        if not training_type:
            return Response({
                'error': 'training_type is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            generator = FlexibleWorkoutGenerator()
            workout_data = generator.generate_1hour_workout(training_type, goal)
            
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

class WorkoutSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """View generated workouts"""
    queryset = WorkoutSession.objects.all()
    serializer_class = WorkoutSessionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type=training_type)
        
        goal = self.request.query_params.get('goal')
        if goal:
            queryset = queryset.filter(goal=goal)
        
        return queryset