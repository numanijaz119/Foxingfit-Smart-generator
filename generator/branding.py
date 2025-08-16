class FoxingFitBranding:
    """
    Handles standardized Foxing Fit opening and closing texts
    """
    
    OPENING_TEXTS = {
        'kickboxing': "Get ready to start your Foxing Fit Heavybag Training.",
        'power_yoga': "Get ready to start your Foxing Fit Power Yoga Lesson.",
        'calisthenics': "Get ready to start your Foxing Fit Calisthenics workout."
    }
    
    CLOSING_TEXTS = {
        'kickboxing': "Stay Sharp, Stay Foxing Fit.",
        'power_yoga': "Stay Flexible, Stay Foxing Fit.",
        'calisthenics': "Stay Strong, Stay Foxing Fit."
    }
    
    @classmethod
    def get_opening_text(cls, training_type):
        """Get standardized opening text for sport"""
        return cls.OPENING_TEXTS.get(training_type, "Get ready to start your Foxing Fit workout.")
    
    @classmethod
    def get_closing_text(cls, training_type):
        """Get standardized closing text for sport"""
        return cls.CLOSING_TEXTS.get(training_type, "Stay Fit, Stay Foxing Fit.")