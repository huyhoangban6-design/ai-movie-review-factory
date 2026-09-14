# Voice System

Voice Profile:
voice_id, provider, model, language, style, speed, emotion,
commercial_use, license_url, cloning_permission, status.

Routing:
Cloud TTS → GPU Cloud TTS → self-hosted/local-capable TTS → backup provider.

License gate:
commercial YES → allow
NO → block
UNKNOWN → human review

Cache bằng hash(text + voice + model + settings).
Audio phải có sentence/word timestamps để Visual Planner căn theo voice.
