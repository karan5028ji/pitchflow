# Contributing to PitchFlow

Thank you for your interest in contributing to **PitchFlow**! We welcome improvements to the engine, UI, deliverability safeguards, and CRM integrations.

---

## 🛠️ Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/pitchflow.git
   cd pitchflow
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the studio**:
   ```bash
   python main.py gui
   ```
   Navigate to `http://localhost:8000`.

---

## 🧪 Running Tests

Before submitting any Pull Request, ensure that all automated unit tests pass cleanly:

```bash
python -m unittest discover tests
```

---

## 📐 Coding Standards

- **Deliverability First**: Never alter delay limits below 3 minutes without safety guards. Preserving Gmail sender reputation is paramount.
- **Zero-Env In-App First**: Any new configuration options must be configurable directly through the Settings GUI and stored in `ConfigStore` (`data/app_config.json`).
- **Cupertino Aesthetic**: UI components must strictly adhere to Apple Human Interface Guidelines (translucent glassmorphism, clean typography, tactile interactions).
- **Cross-Platform Compatibility**: Avoid platform-specific shell quirks or raw unescaped emojis in terminal outputs that break Windows `cp1252` encoding.

---

## 🔀 Branching Strategy

- `main`: Production-ready code.
- `feature/<feature-name>`: New capabilities or modules.
- `fix/<bug-name>`: Bug fixes and patches.

Submit pull requests against the `main` branch with descriptive summaries and screenshots for any UI adjustments.
