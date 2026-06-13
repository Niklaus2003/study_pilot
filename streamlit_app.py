import io
import json
import os
import smtplib
import ssl
import threading
import time
from datetime import datetime, date, time as dt_time, timedelta
from email.message import EmailMessage
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Import utilities from local files
from extract import extract_syllabus_from_pdf
from planner import allocate_hours, generate_weekly_plan, prepare_study_plan
from pdf_export import create_study_plan_pdf, subject_color_by_deadline, _subject_meta_map, PALETTES
from reminder import send_today_reminder, build_html_email, get_today_slots

# Load environment variables
load_dotenv()

# Pre-load credentials from env
DEFAULT_SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
DEFAULT_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
DEFAULT_SMTP_USER = os.getenv("SMTP_USER", "")
DEFAULT_SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("FROM_EMAIL", DEFAULT_SMTP_USER)
DEFAULT_TO_EMAIL = os.getenv("TO_EMAIL", "")

# Fallback Mock Syllabus in case Groq API fails or is not configured
def get_mock_syllabus():
    today = date.today()
    return [
        {
            "subject": "Mathematics",
            "unit": "Calculus & Algebra",
            "chapters": ["Limits & Continuity", "Differentiation", "Integration", "Linear Algebra"],
            "exam_date": (today + timedelta(days=6)).strftime("%Y-%m-%d"),
            "weightage": "35%"
        },
        {
            "subject": "Physics",
            "unit": "Electromagnetism",
            "chapters": ["Electrostatics", "Magnetostatics", "Faraday's Law", "Maxwell's Equations"],
            "exam_date": (today + timedelta(days=12)).strftime("%Y-%m-%d"),
            "weightage": "25%"
        },
        {
            "subject": "Computer Science",
            "unit": "Algorithms & Data Structures",
            "chapters": ["Arrays & Linked Lists", "Trees & Graphs", "Sorting Algorithms", "Complexity Analysis"],
            "exam_date": (today + timedelta(days=25)).strftime("%Y-%m-%d"),
            "weightage": "25%"
        },
        {
            "subject": "English Literature",
            "unit": "Modern Drama",
            "chapters": ["Shakespearean Plays", "Victorian Poetry", "Modern Prose"],
            "exam_date": (today + timedelta(days=40)).strftime("%Y-%m-%d"),
            "weightage": "15%"
        }
    ]

# Helper to save SMTP credentials back to .env
def save_smtp_to_env(server, port, user, password, from_email, to_email):
    env_path = Path(".env")
    lines = []
    keys_written = set()
    new_vals = {
        "SMTP_SERVER": server,
        "SMTP_PORT": str(port),
        "SMTP_USER": user,
        "SMTP_PASSWORD": password,
        "FROM_EMAIL": from_email,
        "TO_EMAIL": to_email
    }
    
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                matched = False
                for key in new_vals:
                    if line.strip().startswith(f"{key}=") or line.strip().startswith(f"{key} ="):
                        lines.append(f"{key}={new_vals[key]}\n")
                        keys_written.add(key)
                        matched = True
                        break
                if not matched:
                    lines.append(line)
    
    for key, val in new_vals.items():
        if key not in keys_written:
            lines.append(f"{key}={val}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

# Background email scheduler logic
def schedule_daily_email(settings, timetable_data, weekly_summary):
    send_time = settings['send_time']
    smtp_server = settings['smtp_server']
    smtp_port = settings['smtp_port']
    smtp_user = settings['smtp_user']
    smtp_password = settings['smtp_password']
    from_addr = settings['from_address']
    to_addr = settings['to_address']

    def run_loop():
        while True:
            now = datetime.now()
            next_run = datetime.combine(now.date(), send_time)
            if next_run <= now:
                next_run += timedelta(days=1)
            seconds_to_sleep = (next_run - now).total_seconds()
            
            # Check every 60 seconds or sleep
            time.sleep(min(seconds_to_sleep, 60))
            
            if datetime.now() >= next_run:
                try:
                    target_date_str = date.today().strftime("%Y-%m-%d")
                    today_slots = get_today_slots(timetable_data, target_date_str)
                    html_content = build_html_email(today_slots, weekly_summary, target_date_str)
                    
                    # Try to fetch PDF if exists
                    attachment_bytes = None
                    pdf_path = Path("study_plan.pdf")
                    if pdf_path.exists():
                        with open(pdf_path, "rb") as f:
                            attachment_bytes = f.read()
                            
                    subject = f"📚 Study Pilot: Plan for {datetime.today().strftime('%b %d, %Y')}"
                    
                    # Call SSL/TLS send
                    from reminder import send_email_with_ssl_tls
                    send_email_with_ssl_tls(
                        smtp_server=smtp_server,
                        smtp_port=smtp_port,
                        smtp_user=smtp_user,
                        smtp_password=smtp_password,
                        from_addr=from_addr,
                        to_addr=to_addr,
                        subject=subject,
                        html_content=html_content,
                        attachment_bytes=attachment_bytes,
                        attachment_name="study_plan.pdf"
                    )
                    st.session_state['last_email_sent'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                except Exception as exc:
                    st.session_state['last_email_error'] = str(exc)

    if 'email_thread' not in st.session_state or not st.session_state['email_thread'].is_alive():
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
        st.session_state['email_thread'] = thread

def main():
    # 1. Page Config & Layout
    st.set_page_config(page_title="Study Pilot Dashboard", page_icon="📚", layout="wide")
    
    # 2. Inject Premium Modern Styling
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Title Banner card */
    .premium-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%);
        padding: 40px 30px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 35px;
        box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #ffffff;
    }
    
    .premium-header h1 {
        font-size: 38px !important;
        font-weight: 800 !important;
        letter-spacing: -1px;
        margin: 0 0 10px 0 !important;
        color: #ffffff !important;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }
    
    .premium-header p {
        font-size: 16px !important;
        font-weight: 400;
        margin: 0 !important;
        opacity: 0.95;
    }
    
    /* Metrics Row */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 22px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
    }
    .metric-value {
        font-size: 34px;
        font-weight: 800;
        color: #4f46e5;
        line-height: 1;
        margin-bottom: 6px;
    }
    .metric-title {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Custom Slots Styles */
    .study-slot-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        border: 1px solid #e2e8f0;
        transition: border-color 0.2s;
    }
    .study-slot-card:hover {
        border-color: #cbd5e1;
    }
    
    /* Gmail Instruction Accordion styling */
    .gmail-step {
        background-color: #f1f5f9;
        color: #0f172a;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 10px;
        border-left: 4px solid #ea4335;
        font-size: 14.5px;
        line-height: 1.5;
    }
    .gmail-step strong {
        color: #0f172a !important;
    }
    .gmail-step a {
        color: #2563eb !important;
        text-decoration: underline !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 3. Header Title Banner
    st.markdown("""
    <div class="premium-header">
        <h1>STUDY PILOT</h1>
        <p>Interactive Study Timetable Builder, Colored PDF Reports & Automated HTML Email Reminders</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session states
    if 'timetable_data' not in st.session_state:
        # Load local timetable.json if exists
        t_path = Path("timetable.json")
        if t_path.exists():
            try:
                with open(t_path, "r", encoding="utf-8") as f:
                    st.session_state['timetable_data'] = json.load(f)
            except:
                st.session_state['timetable_data'] = {}
        else:
            st.session_state['timetable_data'] = {}
            
    if 'syllabus_subjects' not in st.session_state:
        # Load local syllabus.json if exists
        s_path = Path("syllabus.json")
        if s_path.exists():
            try:
                with open(s_path, "r", encoding="utf-8") as f:
                    st.session_state['syllabus_subjects'] = json.load(f)
            except:
                st.session_state['syllabus_subjects'] = []
        else:
            st.session_state['syllabus_subjects'] = []

    # 4. Sidebar Configuration & Operations
    with st.sidebar:
        st.header("📂 Syllabus Resource")
        uploaded_pdf = st.file_uploader("Upload syllabus PDF to extract topics", type=["pdf"])
        
        if uploaded_pdf is not None:
            if uploaded_pdf.name != st.session_state.get('uploaded_pdf_name'):
                with st.spinner("Extracting syllabus with Groq AI..."):
                    try:
                        extracted = extract_syllabus_from_pdf(uploaded_pdf)
                        st.session_state['syllabus_subjects'] = extracted
                        st.session_state['uploaded_pdf_name'] = uploaded_pdf.name
                        # Save extracted to local syllabus.json for planner compatibility
                        with open("syllabus.json", "w", encoding="utf-8") as f:
                            json.dump(extracted, f, indent=2)
                        st.success(f"Extracted {len(extracted)} syllabus units.")
                    except Exception as exc:
                        st.warning(f"Groq API error or empty key: {exc}")
                        st.info("Activating fallback Mock Syllabus for testing/demo purposes.")
                        mock_extracted = get_mock_syllabus()
                        st.session_state['syllabus_subjects'] = mock_extracted
                        st.session_state['uploaded_pdf_name'] = f"{uploaded_pdf.name} (Simulation Fallback)"
                        with open("syllabus.json", "w", encoding="utf-8") as f:
                            json.dump(mock_extracted, f, indent=2)
                        st.success(f"Fallback syllabus loaded successfully.")
                        
        if st.session_state.get('syllabus_subjects'):
            st.markdown(f"**Current Syllabus:** `{st.session_state.get('uploaded_pdf_name', 'syllabus.json')}`")
            
        has_data = bool(st.session_state.get('syllabus_subjects') or st.session_state.get('timetable_data'))
        if has_data:
            if st.button("🗑️ Clear & Start Fresh", use_container_width=True):
                st.session_state.pop('syllabus_subjects', None)
                st.session_state.pop('uploaded_pdf_name', None)
                st.session_state.pop('timetable_data', None)
                st.session_state.pop('allocated', None)
                
                # Delete local files
                for filename in ["syllabus.json", "timetable.json", "study_plan.pdf"]:
                    f_path = Path(filename)
                    if f_path.exists():
                        try:
                            os.remove(f_path)
                        except:
                            pass
                st.success("All configurations and plans cleared successfully!")
                st.rerun()
        else:
            st.info("Upload a PDF to parse. If no syllabus is loaded, a simulated schedule can be generated.")
            
        st.markdown("---")
        st.header("⚙️ Timetable Planner Settings")
        daily_hours = st.slider("Target hours to study daily", min_value=1.0, max_value=12.0, value=4.0, step=0.5)
        days_ahead = st.slider("Days to plan in advance", min_value=1, max_value=14, value=7, step=1)
        
        if st.button("⚡ Generate Study Timetable", type="primary"):
            with st.spinner("Generating optimal study path using LLM..."):
                try:
                    subjects_list = st.session_state.get('syllabus_subjects')
                    if not subjects_list:
                        # Fallback to load mock syllabus to plan
                        mock_s = get_mock_syllabus()
                        st.session_state['syllabus_subjects'] = mock_s
                        subjects_list = mock_s
                        with open("syllabus.json", "w", encoding="utf-8") as f:
                            json.dump(mock_s, f, indent=2)
                            
                    subjects, allocated, timetable_data = prepare_study_plan(daily_hours, days_ahead, subjects=subjects_list)
                    
                    st.session_state['allocated'] = allocated
                    st.session_state['timetable_data'] = timetable_data
                    
                    # Save generated timetable back to timetable.json
                    with open("timetable.json", "w", encoding="utf-8") as f:
                        json.dump(timetable_data, f, indent=2)
                        
                    st.success("New study timetable generated successfully!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Timetable generation failed: {exc}")
                    
        st.markdown("---")
        st.header("🎨 PDF Exporter Theme")
        selected_theme = st.selectbox("Select PDF palette", list(PALETTES.keys()), index=0)
        
        # Immediate PDF trigger in sidebar
        if st.session_state.get('timetable_data') and st.session_state.get('syllabus_subjects'):
            pdf_buffer = io.BytesIO()
            try:
                create_study_plan_pdf(
                    st.session_state['timetable_data'],
                    st.session_state['syllabus_subjects'],
                    output_stream=pdf_buffer,
                    theme_name=selected_theme
                )
                pdf_bytes = pdf_buffer.getvalue()
                
                # Write to disk study_plan.pdf for local attachments
                with open("study_plan.pdf", "wb") as f:
                    f.write(pdf_bytes)
                    
                st.download_button(
                    label="📥 Download Colored PDF",
                    data=pdf_bytes,
                    file_name="study_plan.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as exc:
                st.error(f"Failed to compile PDF: {exc}")
        else:
            st.warning("Generate a timetable first to download PDF.")

    # 5. Core Dashboard Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard Summary", 
        "📅 Weekly Timetable", 
        "📚 Syllabus & Priority", 
        "✉️ Gmail & Reminders Setup"
    ])
    
    # -----------------------------
    # TAB 1: DASHBOARD SUMMARY
    # -----------------------------
    with tab1:
        st.subheader("Plan Overview & Metrics")
        
        # Calculate Metric values
        num_subjects = len(st.session_state.get('syllabus_subjects', []))
        total_days = len(st.session_state.get('timetable_data', {}).get('timetable', []))
        
        # Get slots today
        today_str = date.today().strftime("%Y-%m-%d")
        today_data = get_today_slots(st.session_state.get('timetable_data', {}), today_str)
        today_mins = today_data.get("total_study_minutes", 0) if today_data else 0
        today_slots_count = len(today_data.get("slots", [])) if today_data else 0
        
        # Render clean dashboard metrics
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{num_subjects}</div>
                <div class="metric-title">Active Subjects</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{total_days} Days</div>
                <div class="metric-title">Planning Horizon</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{today_slots_count}</div>
                <div class="metric-title">Today's Study Slots</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{today_mins} min</div>
                <div class="metric-title">Today's Duration</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Render Today's Study Plan Card
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.markdown(f"### 🗓️ Today's Agenda ({datetime.today().strftime('%b %d, %Y')})")
            
            if not today_data or not today_data.get("slots"):
                st.info("☕ No study sessions scheduled for today! Use this time to rest or catch up.")
            else:
                subject_meta = _subject_meta_map(st.session_state.get('syllabus_subjects', []))
                palette = PALETTES[selected_theme]
                
                for slot in today_data.get("slots", []):
                    subj = slot.get("subject", "General Study")
                    dur = slot.get("duration_minutes", 0)
                    chaps = ", ".join(slot.get("chapters_to_cover", [])) or "General revision"
                    notes = slot.get("notes", "")
                    
                    # Compute deadline status
                    meta = subject_meta.get(subj, {})
                    exam_date_str = meta.get("exam_date", "")
                    
                    # Colors mapping
                    bg_color = palette["relaxed"]
                    accent_color = palette["primary"]
                    badge_label = "Relaxed"
                    
                    if exam_date_str:
                        try:
                            ed = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
                            days_rem = (ed - date.today()).days
                            if days_rem <= 7:
                                bg_color = palette["urgent"]
                                accent_color = "#ef4444"
                                badge_label = "🚨 Urgent (<= 7 days)"
                            elif days_rem <= 14:
                                bg_color = palette["medium"]
                                accent_color = "#f59e0b"
                                badge_label = "⚠️ Medium (<= 14 days)"
                            elif days_rem <= 30:
                                bg_color = palette["normal"]
                                accent_color = "#10b981"
                                badge_label = "📅 Normal (<= 30 days)"
                        except:
                            pass
                            
                    notes_block = f"<p style='font-size:13px; color:#64748b; font-style:italic; border-top:1px dashed #e2e8f0; padding-top:6px; margin: 6px 0 0 0;'><b>Note:</b> {notes}</p>" if notes else ""
                    
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 16px; border-radius: 12px; border-left: 6px solid {accent_color}; margin-bottom: 12px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
                       <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                          <tr>
                             <td style="font-weight: 700; font-size: 16px; color: #1e293b;">
                                {subj}
                             </td>
                             <td align="right" style="vertical-align: top;">
                                <span style="background-color: {accent_color}; color: #ffffff; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; white-space: nowrap;">
                                   {dur} mins
                                </span>
                             </td>
                          </tr>
                          <tr>
                             <td colspan="2" style="font-size: 14px; color: #475569; padding-top: 6px;">
                                <b>Chapters:</b> {chaps}
                             </td>
                          </tr>
                          <tr>
                             <td colspan="2" style="font-size: 12px; color: #64748b; padding-top: 4px;">
                                <b>Priority status:</b> {badge_label}
                             </td>
                          </tr>
                       </table>
                       {notes_block}
                    </div>
                    """, unsafe_allow_html=True)
                    
        with col_right:
            st.markdown("### ⚡ Quick Notifications")
            st.write("Send today's study slot notification directly via your configured Gmail SMTP server.")
            
            # Simple button trigger for reminder.py email dispatch
            if st.button("✉️ Send Today's Reminder Email Now", use_container_width=True):
                if not DEFAULT_SMTP_USER or not DEFAULT_SMTP_PASSWORD or not DEFAULT_TO_EMAIL:
                    st.error("Email configuration is missing! Go to the 'Gmail & Reminders Setup' tab to save credentials.")
                elif not st.session_state.get('timetable_data'):
                    st.error("No timetable data found. Generate a plan first.")
                else:
                    with st.spinner("Dispatching styled HTML email..."):
                        try:
                            # Use helper from reminder.py
                            send_today_reminder(
                                smtp_server=DEFAULT_SMTP_SERVER,
                                smtp_port=DEFAULT_SMTP_PORT,
                                smtp_user=DEFAULT_SMTP_USER,
                                smtp_password=DEFAULT_SMTP_PASSWORD,
                                from_addr=DEFAULT_FROM_EMAIL,
                                to_addr=DEFAULT_TO_EMAIL,
                                timetable_path="timetable.json",
                                attach_pdf=True,
                                pdf_path="study_plan.pdf"
                            )
                            st.success(f"Email successfully dispatched to {DEFAULT_TO_EMAIL}!")
                        except Exception as e:
                            st.error(f"Failed to send email: {e}")
                            
            st.markdown("---")
            st.markdown("##### 🕒 Daily Scheduler status")
            if st.session_state.get('email_thread') and st.session_state['email_thread'].is_alive():
                st.success("Scheduler Active: Spawning email alerts daily.")
            else:
                st.warning("Scheduler Idle: Set up scheduler in the fourth tab.")
                
            last_sent = st.session_state.get('last_email_sent')
            if last_sent:
                st.info(f"Last automated email sent: `{last_sent}`")
            last_err = st.session_state.get('last_email_error')
            if last_err:
                st.error(f"Last Scheduler Error: `{last_err}`")

    # -----------------------------
    # TAB 2: WEEKLY TIMETABLE
    # -----------------------------
    with tab2:
        st.subheader("📅 Plan Timetable Browser")
        timetable_data = st.session_state.get('timetable_data', {})
        timetable = timetable_data.get('timetable', [])
        
        if not timetable:
            st.info("No study timetable has been created yet. Upload a syllabus in the sidebar and click 'Generate Study Timetable'.")
        else:
            # Add searching or filtering
            search_subject = st.text_input("🔍 Search for slot by Subject name", "").strip().lower()
            
            for day in timetable:
                day_num = day.get("day", 1)
                day_date = day.get("date", "")
                total_mins = day.get("total_study_minutes", 0)
                slots = day.get("slots", [])
                
                # Filter slots if searching
                filtered_slots = slots
                if search_subject:
                    filtered_slots = [s for s in slots if search_subject in s.get("subject", "").lower()]
                    if not filtered_slots:
                        continue # Hide day if no subjects match
                        
                with st.expander(f"Day {day_num} — {day_date} | {total_mins} mins total ({len(filtered_slots)} slots)", expanded=day_num==1):
                    table_rows = []
                    for slot in filtered_slots:
                        table_rows.append({
                            "Subject": slot.get("subject", ""),
                            "Duration": f"{slot.get('duration_minutes', 0)} min",
                            "Chapters to Cover": ", ".join(slot.get("chapters_to_cover", [])),
                            "Study Notes": slot.get("notes", "")
                        })
                    st.table(table_rows)
                    
            if timetable and timetable_data.get("weekly_summary"):
                st.markdown("### 📝 Weekly Planner Summary")
                st.info(timetable_data.get("weekly_summary"))

    # -----------------------------
    # TAB 3: SYLLABUS & PRIORITY
    # -----------------------------
    with tab3:
        st.subheader("📚 Extracted Syllabus Preview & Priority Proximity")
        subjects = st.session_state.get('syllabus_subjects', [])
        
        if not subjects:
            st.info("No syllabus data uploaded yet. You can upload a PDF in the sidebar.")
        else:
            col_list, col_prio = st.columns([1, 1])
            
            with col_list:
                st.markdown("#### Raw Syllabus Units")
                st.json(subjects)
                
            with col_prio:
                st.markdown("#### Subject Proximity Priorities")
                st.markdown("Priorities are computed automatically based on exam dates and chapter weightages (Syllabus weight / Proximity days).")
                
                try:
                    allocated_subs = allocate_hours(subjects, daily_hours)
                    priority_table = []
                    for idx, s in enumerate(allocated_subs):
                        priority_table.append({
                            "Rank": idx + 1,
                            "Subject": s["subject"],
                            "Weight/Score": f"{s['priority_score']:.2f}",
                            "Daily Allocated Minutes": f"{s['daily_minutes']} min",
                            "Chapters Count": len(s["chapters"])
                        })
                    st.table(priority_table)
                except Exception as e:
                    st.error(f"Failed to calculate priorities: {e}")

    # -----------------------------
    # TAB 4: GMAIL & REMINDERS SETUP
    # -----------------------------
    with tab4:
        st.subheader("✉️ Gmail SMTP Configuration")
        st.markdown("Set up and authenticate your Gmail account to enable automatic HTML reminders.")
        
        col_form, col_guide = st.columns([1, 1])
        
        with col_form:
            st.markdown("#### SMTP Credentials Settings")
            smtp_server = st.text_input("SMTP Server Host", value=DEFAULT_SMTP_SERVER)
            smtp_port = st.number_input("SMTP Port", min_value=1, max_value=65535, value=DEFAULT_SMTP_PORT)
            smtp_user = st.text_input("SMTP Username / Email", value=DEFAULT_SMTP_USER, help="Your primary Gmail address")
            smtp_password = st.text_input("SMTP Password / App Password", type="password", value=DEFAULT_SMTP_PASSWORD, help="Your Gmail App Password")
            
            from_email = st.text_input("From Email Address", value=DEFAULT_FROM_EMAIL or smtp_user)
            to_email = st.text_input("Recipient Email Address (Send To)", value=DEFAULT_TO_EMAIL)
            
            if st.button("💾 Save Settings to .env file", type="secondary", use_container_width=True):
                try:
                    save_smtp_to_env(smtp_server, smtp_port, smtp_user, smtp_password, from_email, to_email)
                    st.success("SMTP Settings successfully saved to .env file! System reloaded credentials.")
                    # Update active environment variables
                    os.environ["SMTP_SERVER"] = smtp_server
                    os.environ["SMTP_PORT"] = str(smtp_port)
                    os.environ["SMTP_USER"] = smtp_user
                    os.environ["SMTP_PASSWORD"] = smtp_password
                    os.environ["FROM_EMAIL"] = from_email
                    os.environ["TO_EMAIL"] = to_email
                    # Trigger rerun to reload defaults
                    st.rerun()
                except Exception as ex:
                    st.error(f"Failed to save to env: {ex}")
                    
            st.markdown("---")
            st.markdown("#### 🕒 Automated Morning Scheduler")
            st.write("Trigger automated emails daily when the application is hosted continuously.")
            schedule_time = st.time_input("Daily dispatch time", value=dt_time(8, 0))
            enable_scheduler = st.checkbox("Toggle automated daily email trigger", value=False)
            
            if enable_scheduler:
                if not smtp_user or not smtp_password or not to_email:
                    st.error("Please fill SMTP credentials and recipient emails before starting scheduler.")
                else:
                    settings = {
                        'send_time': schedule_time,
                        'smtp_server': smtp_server,
                        'smtp_port': int(smtp_port),
                        'smtp_user': smtp_user,
                        'smtp_password': smtp_password,
                        'from_address': from_email or smtp_user,
                        'to_address': to_email
                    }
                    schedule_daily_email(settings, st.session_state.get('timetable_data', {}), st.session_state.get('timetable_data', {}).get('weekly_summary', ''))
                    st.success(f"Daily Scheduler active! Email alerts will send daily at {schedule_time.strftime('%I:%M %p')}.")
            else:
                if 'email_thread' in st.session_state:
                    # Let the daemon thread run, but ignore it
                    pass
                st.info("Daily Scheduler is idle.")
                
        with col_guide:
            st.markdown("#### 🔒 Gmail App Password Setup Guide")
            st.markdown("""
            Gmail has deprecated standard username/password logins for third-party scripts. To connect this app, you must generate a **Google App Password**:
            """)
            
            st.markdown("""
            <div class="gmail-step">
                <strong>Step 1: Enable 2-Step Verification</strong><br>
                Go to your <a href="https://myaccount.google.com/" target="_blank">Google Account Settings</a>, select <strong>Security</strong> on the left, and make sure <strong>2-Step Verification</strong> is enabled under 'How you sign in to Google'.
            </div>
            <div class="gmail-step">
                <strong>Step 2: Access App Passwords</strong><br>
                Click on <strong>2-Step Verification</strong>. Scroll down to the bottom of the page and select <strong>App passwords</strong> (if visible, or search for 'App passwords' in the search bar at the top).
            </div>
            <div class="gmail-step">
                <strong>Step 3: Generate Password</strong><br>
                Enter a custom name for the application (e.g., "Study Pilot") and click <strong>Create</strong>.
            </div>
            <div class="gmail-step">
                <strong>Step 4: Copy the Key</strong><br>
                Google will display a 16-character code (like `abcd efgh ijkl mnop`). Copy this code and paste it directly into the <strong>SMTP Password</strong> field on the left. Do not include spaces.
            </div>
            """, unsafe_allow_html=True)
            
            # Button to trigger immediate SMTP validation test
            if st.button("🧪 Dispatch Test SMTP Connection Email", use_container_width=True):
                if not smtp_user or not smtp_password or not to_email:
                    st.error("Username, Password, and Recipient are required to run tests.")
                else:
                    with st.spinner("Testing SMTP handshake and sending greeting email..."):
                        try:
                            # Build a standard greetings email template
                            test_subject = "🧪 Study Pilot: SMTP Connection Test Success"
                            test_html = """
                            <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; max-width: 500px; margin: 0 auto;">
                                <h2 style="color: #10b981; margin: 0 0 10px 0;">Connection Test Succeeded!</h2>
                                <p style="font-size: 14px; color: #475569; line-height: 1.5;">
                                    This greeting confirms that your Gmail App Password setup is correct, and Study Pilot can establish a secure SMTP handshake to send daily schedules.
                                </p>
                                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 15px 0;">
                                <p style="font-size: 12px; color: #94a3b8;">Sent automatically by Study Pilot App.</p>
                            </div>
                            """
                            # Call the standard sending procedure
                            from reminder import send_email_with_ssl_tls
                            send_email_with_ssl_tls(
                                smtp_server=smtp_server,
                                smtp_port=int(smtp_port),
                                smtp_user=smtp_user,
                                smtp_password=smtp_password,
                                from_addr=from_email or smtp_user,
                                to_addr=to_email,
                                subject=test_subject,
                                html_content=test_html
                            )
                            st.success("Test email sent successfully! Please check your mailbox.")
                        except Exception as e:
                            st.error(f"SMTP Handshake failed: {e}")

if __name__ == '__main__':
    main()
