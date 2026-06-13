import argparse
import json
import os
import smtplib
import ssl
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv

# Load env variables
load_dotenv()

def get_today_slots(timetable_data, target_date_str=None):
    """
    Filters the timetable data to find slots matching the target date.
    Defaults to today's date if not specified.
    """
    if not target_date_str:
        target_date_str = date.today().strftime("%Y-%m-%d")
    
    today_day = None
    for day in timetable_data.get("timetable", []):
        if day.get("date") == target_date_str:
            today_day = day
            break
            
    return today_day

def build_html_email(today_data, weekly_summary, target_date_str):
    """
    Builds a beautifully styled responsive HTML body for the study planner reminder.
    """
    parsed_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    formatted_date = parsed_date.strftime("%A, %b %d, %Y")
    
    if not today_data or not today_data.get("slots"):
        # No study sessions scheduled today
        slots_html = """
        <div class="no-slots" style="text-align: center; padding: 40px 20px; border: 1px dashed #cbd5e1; border-radius: 8px;">
            <div style="font-size: 48px; margin-bottom: 16px;">☕</div>
            <h3 style="margin: 0 0 10px 0; color: #475569; font-size: 18px;">No study slots scheduled for today!</h3>
            <p style="margin: 0; color: #64748b; font-size: 14px;">Great day to review previous material, work on long-term assignments, or take a well-deserved rest.</p>
        </div>
        """
        total_time = 0
    else:
        slots_html = ""
        total_time = today_data.get("total_study_minutes", 0)
        for idx, slot in enumerate(today_data.get("slots", [])):
            subject = slot.get("subject", "General Study")
            duration = slot.get("duration_minutes", 0)
            chapters = ", ".join(slot.get("chapters_to_cover", [])) or "No specific chapters"
            notes = slot.get("notes", "")
            
            notes_html = ""
            if notes:
                notes_html = f"""
                <div class="notes" style="font-size: 13px; color: #64748b; font-style: italic; border-top: 1px dashed #e2e8f0; padding-top: 8px; margin-top: 8px;">
                    <strong>Note:</strong> {notes}
                </div>
                """
                
            slots_html += f"""
            <div class="slot" style="border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 16px; padding: 16px; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                    <tr>
                        <td style="font-weight: 700; font-size: 16px; color: #0f172a; padding-bottom: 4px;">
                            {subject}
                        </td>
                        <td align="right" style="vertical-align: top;">
                            <span class="duration" style="font-size: 12px; font-weight: 600; color: #4338ca; background-color: #e0e7ff; padding: 4px 8px; border-radius: 6px; white-space: nowrap;">
                                {duration} min
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2" style="font-size: 14px; color: #334155; padding-top: 4px; padding-bottom: 4px;">
                            <span style="font-weight: 600; color: #4f46e5;">Chapters:</span> {chapters}
                        </td>
                    </tr>
                </table>
                {notes_html}
            </div>
            """

    # Format weekly summary paragraph
    summary_section = ""
    if weekly_summary:
        summary_section = f"""
        <div class="summary-card" style="background-color: #f8fafc; border-left: 4px solid #6366f1; padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 24px;">
            <h3 style="margin: 0 0 6px 0; color: #1e293b; font-size: 15px; font-weight: 600;">Weekly Plan Insights</h3>
            <p style="margin: 0; font-size: 14px; color: #475569; line-height: 1.5;">{weekly_summary}</p>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Your Daily Study Plan</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f6f9fc; margin: 0; padding: 0; color: #333333;">
      <div class="wrapper" style="background-color: #f6f9fc; width: 100%; padding: 30px 0;">
        <div class="container" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); overflow: hidden; border: 1px solid #e2e8f0;">
          
          <!-- Header -->
          <div class="header" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 30px; text-align: center; color: #ffffff;">
            <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; text-transform: uppercase;">Study Pilot</h1>
            <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9; font-weight: 500;">Your Personalized Daily Learning Routine</p>
          </div>
          
          <!-- Content Body -->
          <div class="content" style="padding: 30px;">
            <div class="date-badge" style="display: inline-block; background-color: #f0fdf4; color: #166534; font-weight: 700; font-size: 12px; padding: 6px 12px; border-radius: 20px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.5px;">
              📅 {formatted_date}
            </div>
            
            <h2 style="margin: 0 0 15px 0; font-size: 20px; font-weight: 700; color: #0f172a;">Today's Study Slots</h2>
            <p style="margin: 0 0 20px 0; font-size: 15px; color: #475569; line-height: 1.5;">
              You have <strong>{total_time} minutes</strong> of active study scheduled for today. Prepare your workspace, limit distractions, and let's get learning!
            </p>
            
            {summary_section}
            
            <div style="margin-top: 10px; margin-bottom: 20px;">
                {slots_html}
            </div>
            
          </div>
          
          <!-- Footer -->
          <div class="footer" style="background-color: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0;">
            <p style="margin: 0 0 8px 0;">This email was sent automatically by your local Study Pilot Assistant.</p>
            <p style="margin: 0; font-weight: 600; color: #6366f1;">Keep pushing forward. Consistency is the key to mastery!</p>
          </div>
          
        </div>
      </div>
    </body>
    </html>
    """
    return html

def send_email_with_ssl_tls(smtp_server, smtp_port, smtp_user, smtp_password, from_addr, to_addr, subject, html_content, attachment_bytes=None, attachment_name="study_plan.pdf"):
    """
    Sends an HTML email with optional attachments. Handles SSL and STARTTLS ports correctly.
    """
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    
    # Set HTML content
    message.set_content("Please enable HTML viewing to see today's study plan.")
    message.add_alternative(html_content, subtype="html")
    
    if attachment_bytes is not None:
        message.add_attachment(
            attachment_bytes, 
            maintype="application", 
            subtype="pdf", 
            filename=attachment_name
        )
        
    context = ssl.create_default_context()
    
    if smtp_port == 465:
        # Secure SMTP SSL
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(message)
    else:
        # Standard SMTP with STARTTLS (port 587 or others)
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.send_message(message)

def send_today_reminder(
    smtp_server=None,
    smtp_port=None,
    smtp_user=None,
    smtp_password=None,
    from_addr=None,
    to_addr=None,
    timetable_path="timetable.json",
    attach_pdf=False,
    pdf_path="study_plan.pdf",
    target_date=None
):
    """
    Programmatic entry point to load data, filter, build html, and send.
    """
    # 1. Resolve configuration with environment variables fallback
    smtp_server = smtp_server or os.getenv("SMTP_SERVER", "smtp.gmail.com")
    try:
        smtp_port = int(smtp_port or os.getenv("SMTP_PORT", "587"))
    except ValueError:
        smtp_port = 587
        
    smtp_user = smtp_user or os.getenv("SMTP_USER", "")
    smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")
    from_addr = from_addr or os.getenv("FROM_EMAIL", smtp_user)
    to_addr = to_addr or os.getenv("TO_EMAIL", "")
    
    # Validations
    if not smtp_user or not smtp_password:
        raise ValueError("SMTP username or password is not configured.")
    if not to_addr:
        raise ValueError("Recipient email address (TO_EMAIL) is not configured.")
        
    # 2. Load timetable data
    t_path = Path(timetable_path)
    if not t_path.exists():
        raise FileNotFoundError(f"Timetable file not found at: {t_path.absolute()}")
        
    with open(t_path, "r") as f:
        timetable_data = json.load(f)
        
    # 3. Filter today's slots
    target_date_str = target_date or date.today().strftime("%Y-%m-%d")
    today_data = get_today_slots(timetable_data, target_date_str)
    
    # 4. Compile HTML body
    weekly_summary = timetable_data.get("weekly_summary", "")
    html_body = build_html_email(today_data, weekly_summary, target_date_str)
    
    # 5. Handle attachment
    attachment_bytes = None
    if attach_pdf:
        p_path = Path(pdf_path)
        if p_path.exists():
            with open(p_path, "rb") as f:
                attachment_bytes = f.read()
        else:
            print(f"Warning: PDF attachment specified but file not found at {p_path.absolute()}")
            
    # 6. Send
    subject = f"📚 Study Pilot: Plan for {datetime.strptime(target_date_str, '%Y-%m-%d').strftime('%b %d, %Y')}"
    send_email_with_ssl_tls(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_addr=from_addr,
        to_addr=to_addr,
        subject=subject,
        html_content=html_body,
        attachment_bytes=attachment_bytes,
        attachment_name=t_path.stem + "_plan.pdf" if attach_pdf else None
    )
    
    return today_data

def main():
    parser = argparse.ArgumentParser(description="Study Pilot Daily Email Reminder standalone utility.")
    parser.add_argument("--timetable", type=str, default="timetable.json", help="Path to timetable.json file")
    parser.add_argument("--date", type=str, default=None, help="Target date to filter in YYYY-MM-DD format (defaults to today)")
    parser.add_argument("--smtp-server", type=str, default=None, help="SMTP Server address")
    parser.add_argument("--smtp-port", type=str, default=None, help="SMTP Port")
    parser.add_argument("--smtp-user", type=str, default=None, help="SMTP Username")
    parser.add_argument("--smtp-password", type=str, default=None, help="SMTP Password")
    parser.add_argument("--from-email", type=str, default=None, help="Sender email address")
    parser.add_argument("--to-email", type=str, default=None, help="Recipient email address")
    parser.add_argument("--attach-pdf", action="store_true", help="Attach study_plan.pdf if available")
    parser.add_argument("--pdf-path", type=str, default="study_plan.pdf", help="Path to pdf to attach")
    
    args = parser.parse_args()
    
    try:
        print(f"Processing study reminder for date: {args.date or date.today().strftime('%Y-%m-%d')}")
        today_data = send_today_reminder(
            smtp_server=args.smtp_server,
            smtp_port=args.smtp_port,
            smtp_user=args.smtp_user,
            smtp_password=args.smtp_password,
            from_addr=args.from_email,
            to_addr=args.to_email,
            timetable_path=args.timetable,
            attach_pdf=args.attach_pdf,
            pdf_path=args.pdf_path,
            target_date=args.date
        )
        if today_data:
            print(f"Success! Sent email reminder containing {len(today_data.get('slots', []))} study slots.")
        else:
            print("Success! Sent email reminder (no active study slots scheduled for today).")
            
    except Exception as e:
        print(f"Error executing study reminder: {e}")
        exit(1)

if __name__ == "__main__":
    main()
