# 🧠 Smart Workout Script Generator

**Django-powered intelligent workout generation for fitness instructors**

[![Django](https://img.shields.io/badge/Django-4.2.7-green.svg)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org/)
[![REST API](https://img.shields.io/badge/API-REST-orange.svg)](https://www.django-rest-framework.org/)

## 🎯 Overview

Automatically generates varied 60-minute workout scripts for **Kickboxing**, **Power Yoga**, and **Calisthenics** by intelligently combining pre-written content blocks. Reduces decision fatigue while maintaining sport-specific methodology.

### ✨ Key Features

- **🤖 Sport Intelligence**: Auto surprise rounds (kickboxing), vinyasa transitions (yoga), difficulty progression (calisthenics)
- **⏱️ Perfect Timing**: 60-minute target with ±5 minute flexibility
- **🔄 Variety Engine**: Smart selection prevents repetition
- **📱 Easy Management**: Self-service admin interface
- **🎤 Voice Ready**: Optimized for Murf.ai and TTS platforms

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/smart-workout-generator.git
cd smart-workout-generator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Initialize database
python manage.py migrate
python manage.py createsuperuser

# Setup system
python manage.py import_from_drive --setup-complete-system

# Run server
python manage.py runserver
```

**Access**: Admin at http://localhost:8000/admin/ | API at http://localhost:8000/api/

## 🎮 Usage

### Generate Workout (API)

```bash
curl -X POST http://localhost:8000/api/generator/generate/generate_workout/ \
  -H "Content-Type: application/json" \
  -d '{"training_type": "kickboxing", "goal": "strength"}'
```

### Admin Panel

- **Scripts**: Add workout content with timing and intensity
- **Categories**: Define workout sections (warmup, combos, etc.)
- **Templates**: Configure workout structure with OR logic
- **Quotes**: Manage motivational insertions

## 🧠 Sport Intelligence

| Sport               | Intelligence Features                        |
| ------------------- | -------------------------------------------- |
| **🥊 Kickboxing**   | Auto surprise rounds after core sections     |
| **🧘‍♀️ Power Yoga**   | Vinyasa transitions between pose changes     |
| **💪 Calisthenics** | Difficulty progression, MAX challenge at end |

## 📁 Project Structure

```
foxing_fit_backend/
├── scripts/           # Content management
├── generator/         # Workout generation engine
├── requirements.txt   # Dependencies
└── manage.py         # Django management
```

## 🗄️ Data Import

```bash
# Import from folder structure
python manage.py import_from_drive --import-local-files --folder-path DATABASE_CONTENT
```

Expected structure:

```
DATABASE_CONTENT/
├── kickboxing/combinations/
├── power_yoga/standing_poses/
└── calisthenics/pushup/
```

## 🔧 Configuration

Create `.env`:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
```

## 📊 Example Output

```json
{
  "title": "Kickboxing - Strength - 2024-08-10 14:30",
  "total_duration": 58.5,
  "time_status": "Perfect (58.5 min)",
  "sport_specific_additions": {
    "surprise_rounds_added": 2
  },
  "compiled_script": "**Onthoud, [elke stoot maakt je sterker]**\n\n## Warm-up..."
}
```

## 📚 API Endpoints

| Endpoint                                    | Method    | Description       |
| ------------------------------------------- | --------- | ----------------- |
| `/api/scripts/scripts/`                     | GET, POST | Manage scripts    |
| `/api/scripts/categories/`                  | GET, POST | Manage categories |
| `/api/generator/generate/generate_workout/` | POST      | Generate workout  |
| `/api/generator/sessions/`                  | GET       | View sessions     |

## 🚧 Development

```bash
# Run tests
python manage.py test

# Add new sport
# 1. Add to TRAINING_TYPES in models.py
# 2. Create SportGeneratorMixin in services.py
# 3. Add to FlexibleWorkoutGenerator class
```

## 🎯 Roadmap

- [ ] .docx export functionality
- [ ] Multi-language support (English)
- [ ] AI-powered content suggestions
- [ ] Voice file (.mp3) integration

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Add tests and documentation
4. Submit pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

**Made for fitness professionals who want intelligent automation, not content creation headaches.**
