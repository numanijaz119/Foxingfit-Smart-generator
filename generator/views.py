from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from scripts.models import WorkoutTemplate
from .models import WorkoutSession
from .services import IntelligentWorkoutGenerator  # Updated class name
from .serializers import WorkoutSessionSerializer

class WorkoutGeneratorViewSet(viewsets.ViewSet):
    """Smart workout generation with full admin control and sport-specific intelligence"""
    
    @action(detail=False, methods=['post'])
    def generate_workout(self, request):
        """
        Generate an intelligent workout with custom duration and full admin control
        
        UPDATED: Now uses IntelligentWorkoutGenerator with full admin control
        Body Parameters:
        - training_type (required): 'kickboxing', 'power_yoga', or 'calisthenics'
        - goal (optional): 'allround', 'endurance', 'strength', 'flexibility', 'technique' (default: 'allround')
        - target_duration (optional): Target duration in minutes, 15-120 (default: 60.0)
        
        Returns:
        - Complete workout with admin-controlled special rounds
        - Time status analysis
        - Sport-specific additions summary based on admin template configuration
        """
        training_type = request.data.get('training_type')
        goal = request.data.get('goal', 'allround')
        target_duration = request.data.get('target_duration', 60.0)
        
        if not training_type:
            return Response({
                'error': 'training_type is required',
                'valid_types': ['kickboxing', 'power_yoga', 'calisthenics']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate training_type
        valid_types = ['kickboxing', 'power_yoga', 'calisthenics']
        if training_type not in valid_types:
            return Response({
                'error': f'Invalid training_type. Must be one of: {valid_types}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate goal
        valid_goals = ['allround', 'endurance', 'strength', 'flexibility', 'technique']
        if goal not in valid_goals:
            return Response({
                'error': f'Invalid goal. Must be one of: {valid_goals}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate target_duration
        try:
            target_duration = float(target_duration)
            if target_duration < 15 or target_duration > 120:
                return Response({
                    'error': 'target_duration must be between 15 and 120 minutes'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                'error': 'target_duration must be a valid number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # UPDATED: Use new IntelligentWorkoutGenerator class name
            generator = IntelligentWorkoutGenerator()
            
            # UPDATED: Use new method name with admin control
            workout_data = generator.generate_workout_with_custom_duration(
                training_type, 
                goal, 
                target_duration
            )
            
            return Response({
                'success': True,
                'workout': workout_data,
                'message': f"Generated {workout_data['time_status']} workout with admin-controlled special rounds",
                'admin_control_applied': True,  # NEW: Indicate admin control is active
                'sport_intelligence_applied': workout_data['sport_specific_additions']
            })
            
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Workout generation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def preview_workout_template(self, request):
        """
        Preview the workout template structure with admin control information
        UPDATED: Shows admin control status and warnings
        """
        training_type = request.query_params.get('training_type')
        if not training_type:
            return Response({
                'error': 'training_type parameter required',
                'valid_types': ['kickboxing', 'power_yoga', 'calisthenics']
            }, status=400)
        
        # Get active templates for this sport
        templates = WorkoutTemplate.objects.filter(
            training_type=training_type,
            is_active=True  # UPDATED: Only show active templates
        ).order_by('sequence_order').prefetch_related('alternative_categories')
        
        if not templates.exists():
            return Response({
                'error': f'No active workout templates found for {training_type}',
                'suggestion': 'Run the setup command: python manage.py setup --setup-complete-system'
            }, status=404)
        
        template_data = []
        for template in templates:
            alternatives = list(template.alternative_categories.values('id', 'display_name'))
            
            # UPDATED: Enhanced auto-additions with admin control info
            auto_additions = []
            warnings = []  # NEW: Include warnings in preview
            
            if template.add_surprise_round_after:
                auto_additions.append({
                    'type': 'surprise_round',
                    'description': 'Admin-controlled surprise round (system will find kb_surprise category)',
                    'admin_configured': True
                })
                # Check for warnings
                if template.primary_category:
                    category_name = template.primary_category.name.lower()
                    if any(term in category_name for term in ['warmup', 'cooldown', 'stretch']):
                        warnings.append('Surprise round after gentle section may be intense')
            
            if template.add_max_challenge_after:
                auto_additions.append({
                    'type': 'max_challenge',
                    'description': 'Admin-controlled MAX challenge (system will find cal_max_challenge category)',
                    'admin_configured': True
                })
                # Check for warnings  
                if template.sequence_order <= 2:
                    warnings.append('MAX challenge early in sequence may need more preparation')
            
            if template.add_vinyasa_transition_after:
                vinyasa_desc = f"Admin-controlled vinyasa {template.vinyasa_type}" if template.vinyasa_type else "Admin-controlled vinyasa"
                auto_additions.append({
                    'type': 'vinyasa_transition',
                    'vinyasa_type': template.vinyasa_type,
                    'description': f'{vinyasa_desc} (system will find matching category)',
                    'admin_configured': True
                })
                # Check for warnings
                if template.primary_category:
                    category_name = template.primary_category.name.lower()
                    if any(term in category_name for term in ['savasana', 'mindfulness']):
                        warnings.append('Vinyasa after relaxation may disrupt flow')
            
            template_data.append({
                'sequence_order': template.sequence_order,
                'primary_category': {
                    'id': template.primary_category.id,
                    'name': template.primary_category.name,
                    'display_name': template.primary_category.display_name
                },
                'alternatives': alternatives,
                'is_required': template.is_required,
                'is_active': template.is_active,  # NEW: Include active status
                'auto_additions_after': auto_additions,
                'placement_warnings': warnings,  # NEW: Include warnings
                'logic_explanation': self._get_template_logic_explanation(template)
            })
        
        return Response({
            'training_type': training_type,
            'training_type_display': dict(WorkoutTemplate.TRAINING_TYPES).get(training_type),
            'template_sequence': template_data,
            'admin_control_status': {  # NEW: Admin control information
                'full_control_enabled': True,
                'description': 'Admin has complete control over special round placement via template checkboxes',
                'warning_system': 'Active - provides guidance but does not block decisions'
            },
            'sport_intelligence_summary': self._get_sport_intelligence_summary(training_type)
        })
    
    def _get_template_logic_explanation(self, template):
        """Get human-readable explanation of template logic with admin control info"""
        explanations = []
        
        alternatives = template.alternative_categories.all()
        if alternatives.exists():
            alt_names = [alt.display_name for alt in alternatives]
            explanations.append(f"Choice: {template.primary_category.display_name} OR {' OR '.join(alt_names)}")
        else:
            explanations.append(f"Fixed: {template.primary_category.display_name}")
        
        # UPDATED: Admin control emphasis
        if template.add_surprise_round_after:
            explanations.append("Then: Admin-controlled surprise round")
        if template.add_max_challenge_after:
            explanations.append("Then: Admin-controlled MAX challenge")
        if template.add_vinyasa_transition_after:
            vinyasa_type = template.vinyasa_type or "generic"
            explanations.append(f"Then: Admin-controlled vinyasa ({vinyasa_type})")
        
        return " | ".join(explanations)
    
    def _get_sport_intelligence_summary(self, training_type):
        """UPDATED: Get summary emphasizing admin control"""
        summaries = {
            'kickboxing': {
                'control_type': 'Full Admin Control',
                'special_rounds': 'Surprise rounds added exactly where admin configures via template checkboxes',
                'automatic_logic': 'None - admin decides everything',
                'detection': 'System finds categories with "surprise" in name',
                'flexibility': 'Admin can create intense or gentle workout styles'
            },
            'power_yoga': {
                'control_type': 'Full Admin Control',  # UPDATED
                'vinyasa_transitions': 'Vinyasa transitions added exactly where admin configures via template checkboxes',  # UPDATED
                'automatic_logic': 'None - admin decides everything',  # UPDATED
                'detection': 'System finds categories with "vinyasa" + "s2s" or "s2sit" in name',
                'flexibility': 'Admin can create flowing or static yoga styles'  # UPDATED
            },
            'calisthenics': {
                'control_type': 'Full Admin Control',  # UPDATED
                'max_challenge': 'MAX challenges added exactly where admin configures via template checkboxes',  # UPDATED
                'automatic_logic': 'Logical exercise ordering only (warmup first, etc.)',  # UPDATED
                'detection': 'System finds categories with "max" + "challenge" in name',
                'flexibility': 'Admin can place MAX challenges anywhere in workout'  # UPDATED
            }
        }
        
        return summaries.get(training_type, {})

# WorkoutSessionViewSet remains unchanged - no modifications needed for admin control
class WorkoutSessionViewSet(viewsets.ModelViewSet):
    """
    Complete CRUD operations for generated workouts
    NO CHANGES NEEDED - existing functionality works with new admin control system
    """
    queryset = WorkoutSession.objects.all()
    serializer_class = WorkoutSessionSerializer
    
    def get_queryset(self):
        """Enhanced filtering for workout sessions"""
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
        
        # Filter by duration range
        min_duration = self.request.query_params.get('min_duration')
        max_duration = self.request.query_params.get('max_duration')
        if min_duration:
            try:
                queryset = queryset.filter(total_duration__gte=float(min_duration))
            except ValueError:
                pass
        if max_duration:
            try:
                queryset = queryset.filter(total_duration__lte=float(max_duration))
            except ValueError:
                pass
        
        # Search in title and notes
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(notes__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def destroy(self, request, *args, **kwargs):
        """Delete a workout session with confirmation"""
        try:
            instance = self.get_object()
            session_title = instance.title
            self.perform_destroy(instance)
            return Response({
                'success': True,
                'message': f'Workout session "{session_title}" deleted successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f'Failed to delete workout session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def mark_used(self, request, pk=None):
        """Mark a session as used/unused"""
        session = self.get_object()
        is_used = request.data.get('is_used', True)
        
        if not isinstance(is_used, bool):
            return Response({
                'error': 'is_used must be a boolean value'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        session.is_used = is_used
        session.save(update_fields=['is_used'])
        
        return Response({
            'success': True,
            'message': f'Session marked as {"used" if is_used else "unused"}',
            'is_used': session.is_used,
            'session_title': session.title
        })
    
    @action(detail=True, methods=['post'])
    def update_notes(self, request, pk=None):
        """Update session notes"""
        session = self.get_object()
        notes = request.data.get('notes', '')
        
        if not isinstance(notes, str):
            return Response({
                'error': 'notes must be a string'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        session.notes = notes
        session.save(update_fields=['notes'])
        
        return Response({
            'success': True,
            'message': 'Session notes updated successfully',
            'notes': session.notes,
            'session_title': session.title
        })