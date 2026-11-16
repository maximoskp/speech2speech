# speech2speech
A basic implementation of speech-to-speech system.


### Tentative project structure

singcompany/
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   │
│   └── audio/
│       ├── audio_capture.js
│       └── pcm-processor.js
│
├── backend/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── websocket.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── events.py
│   │   └── config.py
│   │
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── buffers.py
│   │   ├── resampling.py
│   │   └── vad.py
│   │
│   └── modules/
│       ├── __init__.py
│       │
│       ├── asr/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── faster_whisper.py
│       │
│       ├── llm/
│       │   └── ...
│       │
│       └── tts/
│           └── ...
│
├── configs/
│   ├── development.yaml
│   └── models.yaml
│
├── experiments/
│
└── requirements.txt