# 📚 Study Pilot

An intelligent, AI-powered study planner dashboard that converts academic syllabi into prioritized weekly timetables. It supports dynamic colored PDF exports, visual deadline-tracking indicators, and scheduled HTML email reminders sent directly to your inbox using Gmail SMTP.

---

## 🚀 Key Features

*   **AI-Powered Syllabus Parsing**: Upload a syllabus PDF and instantly extract subjects, units, chapters, exam dates, and weightages via the Groq API.
*   **Proximity-Based Prioritization**: Automatically calculates a priority score (Weight / Proximity Days) to optimize daily study time allocation.
*   **Dynamic Timetable Generation**: Builds a logical weekly timeline with chapter sequencing, revision breaks, and weekend review cycles.
*   **Color-Coded PDF Export**: Generates high-quality PDFs containing a visual proximity legend matching subjects to colors (Urgent, Medium, Normal, and Relaxed schedules).
*   **Gmail SMTP Integration**: Send daily reminders to your inbox containing beautiful slot summaries.
*   **Automated Background Scheduler**: Sends your study reminder to your email address at a scheduled hour daily.
*   **Fallback Simulation Mode**: Run the scheduler and planner instantly via simulated mock data if API keys are missing or limits are exceeded.

---

## 🛠️ Project Structure

*   `streamlit_app.py`: The premium multi-tab dashboard built with interactive components, custom styles, and configuration logs.
*   `reminder.py`: Standalone CLI utility and programmatic helper to filter today's slots and send styled HTML email notifications.
*   `pdf_export.py`: Handles generating the ReportLab colored PDF timetable with customizable theme color palettes.
*   `planner.py`: Core logic for priority scores, daily minutes calculation, and weekly scheduling with LLMs.
*   `extract.py`: Text parser and structure builder for syllabus PDFs using LLMs.
*   `requirements.txt`: Project dependencies list.
*   `sample_syllabus.pdf`: Example input file for verification.

---

## 🔒 Gmail SMTP & App Password Setup

Due to Google's security guidelines, standard Gmail passwords cannot be used directly. You need to create a **Google App Password**:

1.  **Enable 2-Step Verification**:
    *   Go to your [Google Account Settings](https://myaccount.google.com/).
    *   Select **Security** from the left-hand navigation.
    *   Make sure **2-Step Verification** is enabled under "How you sign in to Google".
2.  **Generate an App Password**:
    *   Select **2-Step Verification**, scroll to the bottom, and click **App passwords** (or search for "App passwords" at the top search bar).
    *   Give your application a custom name (e.g., "Study Pilot") and click **Create**.
3.  **Use the Password**:
    *   Copy the 16-character code (e.g., `abcd efgh ijkl mnop`).
    *   Paste it directly into the `SMTP_PASSWORD` field inside your local `.env` or input form without spaces.

---

## ⚙️ Installation & Configuration

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/Niklaus2003/study_pilot.git
cd study_pilot

# Create and activate virtual environment
python -m venv venv
# On Windows (PowerShell):
venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# Gmail SMTP Settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail_address@gmail.com
SMTP_PASSWORD=your_16_character_app_password
FROM_EMAIL=your_gmail_address@gmail.com
TO_EMAIL=recipient_address@example.com
```

---

## 💻 Running the Application

### 1. Launch the Dashboard (Web UI)

Run the following command to start the interactive Streamlit dashboard:

```bash
streamlit run streamlit_app.py
```

### 2. Execute Standalone Daily Reminders (CLI / Cron)

To automate or trigger study plan reminders (for instance, via a scheduled Windows Task Scheduler task or Linux Cron job), use the `reminder.py` CLI script:

```bash
# Sends today's reminder email immediately based on timetable.json
python reminder.py

# Send a reminder for a specific date
python reminder.py --date 2026-06-13

# Send reminder and attach the generated color PDF study plan
python reminder.py --attach-pdf --pdf-path study_plan.pdf
```

---

## 📝 License

This project is open-source and available under the MIT License.
