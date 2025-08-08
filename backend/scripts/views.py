from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory
from .serializers import (
    WorkoutScriptSerializer, 
    MotivationalQuoteSerializer, 
    ScriptCategorySerializer,
    WorkoutTemplateSerializer
)

class ScriptCategoryViewSet(viewsets.ModelViewSet):
    queryset = ScriptCategory.objects.filter(is_active=True)
    serializer_class = ScriptCategorySerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type=training_type)
        
        return queryset.order_by('training_type', 'display_name')
    
    @action(detail=False, methods=['post'])
    def create_custom_category(self, request):
        """
        Johnny can create custom script categories
        """
        required_fields = ['display_name', 'training_type']
        
        for field in required_fields:
            if not request.data.get(field):
                return Response(
                    {'error': f'{field} is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        display_name = request.data['display_name']
        training_type = request.data['training_type']
        
        # Create internal name (e.g., "Footwork Training" -> "kb_footwork_training")
        type_prefix = {
            'kickboxing': 'kb',
            'power_yoga': 'py', 
            'calisthenics': 'cal'
        }.get(training_type, 'custom')
        
        internal_name = f"{type_prefix}_{display_name.lower().replace(' ', '_').replace('-', '_')}"
        
        if ScriptCategory.objects.filter(name=internal_name, training_type=training_type).exists():
            return Response(
                {'error': 'A script category with this name already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the category
        script_category = ScriptCategory.objects.create(
            name=internal_name,
            display_name=display_name,
            training_type=training_type,
            description=request.data.get('description', '')
        )
        
        serializer = self.get_serializer(script_category)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class WorkoutScriptViewSet(viewsets.ModelViewSet):
    """
    Johnny's workout script management with updated filtering
    """
    queryset = WorkoutScript.objects.filter(is_active=True)
    serializer_class = WorkoutScriptSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by training type
        training_type = self.request.query_params.get('type')
        if training_type:
            queryset = queryset.filter(type=training_type)
        
        # Filter by script category
        script_category_id = self.request.query_params.get('script_category_id')
        if script_category_id:
            queryset = queryset.filter(script_category_id=script_category_id)
        
        # Filter by script category name (for convenience)
        script_category_name = self.request.query_params.get('script_category_name')
        if script_category_name:
            queryset = queryset.filter(script_category__name=script_category_name)
        
        # Filter by goal
        goal = self.request.query_params.get('goal')
        if goal:
            queryset = queryset.filter(goal=goal)
        
        # Search in title and content
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        
        return queryset.order_by('type', 'script_category__display_name', 'title')
    
    @action(detail=False, methods=['get'])
    def available_categories(self, request):
        """
        Get available script categories for a training type
        """
        training_type = request.query_params.get('type')
        if not training_type:
            return Response({'error': 'type parameter required'}, status=400)
        
        script_categories = ScriptCategory.objects.filter(
            training_type=training_type,
            is_active=True
        ).order_by('display_name')
        
        return Response({
            'training_type': training_type,
            'script_categories': [
                {
                    'id': category.id,
                    'name': category.name,
                    'display_name': category.display_name,
                    'description': category.description
                }
                for category in script_categories
            ]
        })

class MotivationalQuoteViewSet(viewsets.ModelViewSet):
    """
    Johnny's motivational quotes management
    """
    queryset = MotivationalQuote.objects.filter(is_active=True)
    serializer_class = MotivationalQuoteSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type=training_type)
        
        context = self.request.query_params.get('context')
        if context:
            queryset = queryset.filter(context=context)
        
        return queryset.order_by('training_type', 'context', 'quote_text')
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Johnny can bulk create motivational quotes
        """
        quotes_data = request.data.get('quotes', [])
        if not quotes_data:
            return Response({'error': 'quotes array is required'}, status=400)
        
        created_quotes = []
        errors = []
        
        for i, quote_data in enumerate(quotes_data):
            try:
                serializer = self.get_serializer(data=quote_data)
                if serializer.is_valid():
                    quote = serializer.save()
                    created_quotes.append(serializer.data)
                else:
                    errors.append(f"Quote {i+1}: {serializer.errors}")
            except Exception as e:
                errors.append(f"Quote {i+1}: {str(e)}")
        
        return Response({
            'created': len(created_quotes),
            'errors': errors,
            'quotes': created_quotes
        })

class WorkoutTemplateViewSet(viewsets.ModelViewSet):
    """
    Manage workout templates with OR logic
    """
    queryset = WorkoutTemplate.objects.all()
    serializer_class = WorkoutTemplateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type=training_type)
        
        return queryset.order_by('training_type', 'sequence_order')