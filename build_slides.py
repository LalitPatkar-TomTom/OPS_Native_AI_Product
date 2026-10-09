import sys
sys.stdout.reconfigure(encoding='utf-8')
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

TT_DARK   = RGBColor(0x0F, 0x2B, 0x5B)
TT_BLUE   = RGBColor(0x1A, 0x4D, 0xB3)
TT_LIGHT  = RGBColor(0xE8, 0xF0, 0xFE)
TT_GREEN  = RGBColor(0x2E, 0x7D, 0x32)
TT_ORANGE = RGBColor(0xE6, 0x51, 0x00)
TT_RED    = RGBColor(0xC6, 0x28, 0x28)
TT_WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
TT_GREY   = RGBColor(0x78, 0x90, 0x9C)
TT_TEXT   = RGBColor(0x22, 0x22, 0x22)
TEAL      = RGBColor(0x00, 0x69, 0x5C)
PURPLE    = RGBColor(0x6A, 0x1B, 0x9A)

W = Inches(13.33)
H = Inches(7.5)

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H
BLANK = prs.slide_layouts[6]


def add_rect(slide, l, t, w, h, fill):
    s = slide.shapes.add_shape(1, l, t, w, h)
    s.line.fill.background()
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    return s


def txt(slide, text, l, t, w, h, size=18, bold=False, color=TT_TEXT,
        align=PP_ALIGN.LEFT, italic=False):
    box = slide.shapes.add_textbox(l, t, w, h)
    box.word_wrap = True
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return box


def bullet_box(slide, items, l, t, w, h, size=16, color=TT_TEXT, spacing=3):
    box = slide.shapes.add_textbox(l, t, w, h)
    box.word_wrap = True
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(spacing)
        run = p.add_run()
        run.text = item
        run.font.size = Pt(size)
        run.font.color.rgb = color
    return box


def header_bar(slide, title, subtitle=None):
    add_rect(slide, 0, 0, W, Inches(1.45), TT_DARK)
    txt(slide, title, Inches(0.5), Inches(0.18), Inches(12.3), Inches(0.8),
        size=28, bold=True, color=TT_WHITE)
    if subtitle:
        txt(slide, subtitle, Inches(0.5), Inches(0.92), Inches(12.3), Inches(0.48),
            size=13, color=RGBColor(0xB0, 0xC4, 0xDE), italic=True)


def colored_card(slide, l, t, w, h, header_color, title, bullets,
                 title_size=14, body_size=12, body_fill=None):
    add_rect(slide, l, t, w, Inches(0.44), header_color)
    txt(slide, title, l + Inches(0.12), t + Inches(0.04),
        w - Inches(0.2), Inches(0.38), size=title_size, bold=True, color=TT_WHITE)
    bf = body_fill or RGBColor(0xF8, 0xF9, 0xFF)
    add_rect(slide, l, t + Inches(0.44), w, h - Inches(0.44), bf)
    bullet_box(slide, bullets, l + Inches(0.15), t + Inches(0.5),
               w - Inches(0.25), h - Inches(0.58), size=body_size, color=TT_TEXT)


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 1 — Title
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, TT_DARK)
add_rect(s, 0, Inches(2.85), W, Inches(0.07), TT_BLUE)
txt(s, 'OPS Native AI', Inches(1), Inches(1.1), Inches(11), Inches(1.3),
    size=54, bold=True, color=TT_WHITE, align=PP_ALIGN.CENTER)
txt(s, 'Your Personal AI Agent  —  Beta User Briefing',
    Inches(1), Inches(2.55), Inches(11), Inches(0.65),
    size=22, color=RGBColor(0xB0, 0xC4, 0xDE), align=PP_ALIGN.CENTER, italic=True)
txt(s, 'October 2026  |  TomTom Maps Operations  |  Lalit Patkar',
    Inches(1), Inches(5.9), Inches(11), Inches(0.45),
    size=13, color=TT_GREY, align=PP_ALIGN.CENTER)
txt(s, '11 Beta Users  |  Confidential — Internal Only',
    Inches(1), Inches(6.35), Inches(11), Inches(0.45),
    size=12, color=TT_GREY, align=PP_ALIGN.CENTER)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 2 — Agenda
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, RGBColor(0xF4, 0xF6, 0xFB))
header_bar(s, 'What We Will Cover Today')
items = [
    ('01', 'What is OPS Native AI — and what it does for you personally'),
    ('02', 'Your Personal Profile — the AI\'s brain about you'),
    ('03', 'The Onboarding Form — how to teach the AI about your work'),
    ('04', 'Use Cases — the 5 types of AI automation planned'),
    ('05', 'What lands in your inbox — the 4 live AI outputs'),
    ('06', 'What action to take when you receive a trigger'),
    ('07', 'What the AI will NEVER do — your guardrails'),
    ('08', 'What we need from you — validation and feedback'),
]
for i, (num, item) in enumerate(items):
    y = Inches(1.65) + i * Inches(0.61)
    add_rect(s, Inches(0.55), y + Inches(0.03), Inches(0.5), Inches(0.38), TT_BLUE)
    txt(s, num, Inches(0.55), y + Inches(0.03), Inches(0.5), Inches(0.38),
        size=13, bold=True, color=TT_WHITE, align=PP_ALIGN.CENTER)
    txt(s, item, Inches(1.2), y, Inches(11.5), Inches(0.45), size=17, color=TT_TEXT)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 3 — What is OPS Native AI
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, RGBColor(0xF4, 0xF6, 0xFB))
header_bar(s, 'What Is OPS Native AI?',
           "A personal AI agent that watches your projects and metrics — so you don't have to")

txt(s, 'Think of it as a smart personal assistant that works in the background:', Inches(0.6),
    Inches(1.6), Inches(12.5), Inches(0.4), size=16, bold=True, color=TT_DARK)

points = [
    (TT_BLUE,   '👁  Watches',   'Monitors your Jira tickets, quality metrics (FTA & CoQ), and project updates automatically — every day.'),
    (TT_GREEN,  '📬  Informs',   'Sends you a morning briefing, real-time quality alerts, SLA warnings, and a weekly report — each one personalised to your projects.'),
    (TT_ORANGE, '✍  Drafts',    'Prepares ready-to-send stakeholder messages for your review. You approve every word before anything goes out.'),
    (TT_RED,    '🚫  Never Acts', 'It never sends an email, closes a ticket, or makes a decision on your behalf. Every action stays with you, always.'),
]
for i, (clr, title, desc) in enumerate(points):
    col = i % 2
    row = i // 2
    l = Inches(0.4) + col * Inches(6.5)
    t = Inches(2.15) + row * Inches(2.3)
    colored_card(s, l, t, Inches(6.2), Inches(2.2), clr, title, [desc],
                 title_size=15, body_size=14)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 4 — Personal Profile
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, RGBColor(0xF4, 0xF6, 0xFB))
header_bar(s, 'Your Personal Profile',
           "The AI's brain about you — built once, kept up to date")

txt(s, 'What is it?', Inches(0.6), Inches(1.62), Inches(5.8), Inches(0.38),
    size=15, bold=True, color=TT_DARK)
bullet_box(s, [
    'A private profile file created for each of you after the onboarding form.',
    'It tells the AI: your role, your projects, your metrics, your preferences, and your working hours.',
    'Every briefing and alert you receive is personalised based on this file.',
    'Only you and the AI system can read it.',
    'You can update it anytime — just let Lalit know.',
], Inches(0.6), Inches(2.05), Inches(5.8), Inches(2.8), size=13, spacing=4)

add_rect(s, Inches(6.9), Inches(1.55), Inches(5.9), Inches(5.55), TT_LIGHT)
txt(s, "What's inside your profile", Inches(7.1), Inches(1.65), Inches(5.5), Inches(0.38),
    size=14, bold=True, color=TT_DARK)
profile_items = [
    '📋   Your active projects and Jira project keys',
    '📊   FTA target %, CoQ target %, and your alert thresholds',
    '⏰   Your briefing time and quiet hours (no late-night alerts)',
    '👥   Your manager and key stakeholders',
    '📣   Your communication style preference (bullet points, short summaries)',
    '🔒   Data access consents — read-only, Phase 1',
    '⚙️   Which use cases are active for you (UC1 to UC5)',
]
for i, item in enumerate(profile_items):
    txt(s, item, Inches(7.1), Inches(2.15) + i * Inches(0.62), Inches(5.5),
        Inches(0.55), size=13, color=TT_TEXT)

txt(s, '💡  If your projects or team change, just tell us and we update your profile within 24 hours.',
    Inches(0.5), Inches(5.85), Inches(12.3), Inches(0.5),
    size=13, color=TT_BLUE, italic=True)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 5 — Onboarding Form
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, RGBColor(0xF4, 0xF6, 0xFB))
header_bar(s, 'The Onboarding Form',
           'A one-time 10-minute form that teaches the AI about your work')

txt(s, 'You will be asked to fill in:', Inches(0.6), Inches(1.6), Inches(12), Inches(0.38),
    size=15, bold=True, color=TT_DARK)

steps = [
    ('Step 1', 'Your Role & Projects',     'Job title, your active Jira projects, and your role on each one.'),
    ('Step 2', 'Your Quality Metrics',      'FTA target %, CoQ target %, and the values at which you want to be alerted.'),
    ('Step 3', 'Your Working Hours',        'When your day starts and ends, and your quiet hours (no alerts after 19:00).'),
    ('Step 4', 'Your Stakeholders',         'Manager name and email, and the key people you coordinate with regularly.'),
    ('Step 5', 'Your Communication Style',  'How you like information delivered — bullet points, short summaries, etc.'),
    ('Step 6', 'Data Consent',              'Confirm the AI can read (not write) Jira, Confluence, and Power BI for you.'),
    ('Step 7', 'Which Triggers to Activate', 'Choose which of the 5 use cases you want the AI to run for you.'),
]

for i, (step, title, desc) in enumerate(steps):
    if i < 6:
        col = i % 2
        row = i // 2
        l = Inches(0.4) + col * Inches(6.5)
        t = Inches(2.1) + row * Inches(1.15)
        w = Inches(6.2)
    else:
        l, t, w = Inches(0.4), Inches(5.6), Inches(12.9)

    add_rect(s, l, t, Inches(0.72), Inches(0.38), TT_BLUE)
    txt(s, step, l + Inches(0.04), t + Inches(0.02), Inches(0.65), Inches(0.35),
        size=10, bold=True, color=TT_WHITE, align=PP_ALIGN.CENTER)
    txt(s, title, l + Inches(0.85), t, w - Inches(0.95), Inches(0.38),
        size=13, bold=True, color=TT_DARK)
    txt(s, desc, l + Inches(0.85), t + Inches(0.38), w - Inches(0.95), Inches(0.6),
        size=12, color=TT_TEXT)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 6 — Use Cases Planned
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, RGBColor(0xF4, 0xF6, 0xFB))
header_bar(s, 'Use Cases — What the AI Will Do for You',
           '5 automations planned — 4 are live today, UC5 coming next')

uc_data = [
    (TT_BLUE,   'UC1', 'Daily Morning Briefing',
     'LIVE', TT_GREEN,
     ['Triggered every working day at your chosen time (e.g. 08:30).',
      'Covers: RAG health of your projects, Jira SLA status, latest FTA & CoQ, top actions for your day.',
      'If everything is green — it is a short 5-bullet read. If there are issues, it leads with the most urgent.']),
    (TT_RED,    'UC2', 'Jira SLA Alert',
     'LIVE', TT_GREEN,
     ['Triggered the moment a Jira ticket you own breaches its SLA deadline.',
      'Shows you: which ticket, how overdue, who is responsible.',
      'Provides a ready-to-send follow-up message for your review — you send it, not the AI.']),
    (TEAL,      'UC3', 'Automated Weekly Report',
     'LIVE', TT_GREEN,
     ['Triggered every Friday at 16:00.',
      'Generates a PowerPoint draft: project RAG status, FTA/CoQ trends, risks, blockers, recommendations.',
      'All data pre-filled from Jira and Databricks. You review, edit if needed, then share.']),
    (TT_ORANGE, 'UC4', 'Quality & Metric Alert (FTA / CoQ)',
     'LIVE', TT_GREEN,
     ['Triggered the moment FTA drops below or CoQ rises above your personal threshold.',
      'Real-time — checked every 30 minutes during your working hours.',
      'Alert includes: current value, threshold breached, affected project and process type, suggested action.']),
    (PURPLE,    'UC5', 'Plan vs. Actual & CRD Risk Check',
     'COMING NEXT', TT_ORANGE,
     ['Triggered every day at 17:00 — your end-of-day delivery check.',
      'Compares today\'s Jira ticket progress against the sprint plan.',
      'Flags if sprint is at risk of not completing and presents your options: descope, extend, or escalate.']),
]

for i, (clr, uc, title, status, status_clr, bullets) in enumerate(uc_data):
    col = i % 2 if i < 4 else 0
    row = i // 2
    if i == 4:
        l, t, w, h = Inches(0.4), Inches(5.92), Inches(12.9), Inches(1.35)
    else:
        l = Inches(0.4) + col * Inches(6.5)
        t = Inches(1.55) + row * Inches(2.18)
        w, h = Inches(6.2), Inches(2.1)

    add_rect(s, l, t, w, Inches(0.44), clr)
    txt(s, uc, l + Inches(0.1), t + Inches(0.04), Inches(0.55), Inches(0.38),
        size=14, bold=True, color=TT_WHITE)
    txt(s, title, l + Inches(0.7), t + Inches(0.04), w - Inches(2.2), Inches(0.38),
        size=14, bold=True, color=TT_WHITE)
    add_rect(s, l + w - Inches(1.5), t + Inches(0.06), Inches(1.4), Inches(0.32), status_clr)
    txt(s, status, l + w - Inches(1.5), t + Inches(0.06), Inches(1.4), Inches(0.32),
        size=10, bold=True, color=TT_WHITE, align=PP_ALIGN.CENTER)
    add_rect(s, l, t + Inches(0.44), w, h - Inches(0.44), RGBColor(0xF8, 0xF9, 0xFF))
    bullet_box(s, ['• ' + b for b in bullets],
               l + Inches(0.15), t + Inches(0.5), w - Inches(0.25),
               h - Inches(0.58), size=12 if i < 4 else 13)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 7 — What Lands in Your Inbox
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, RGBColor(0xF4, 0xF6, 0xFB))
header_bar(s, 'What Lands in Your Inbox — The 4 Live AI Outputs',
           'Each output is personalised to your profile and your projects')

outputs = [
    (TT_BLUE,   '🌅  UC1 — Morning Briefing',   '08:30 every working day',
     ['Overall health of your projects — Green / Amber / Red',
      'Jira tickets approaching or past SLA',
      'Your latest FTA and CoQ values',
      'Top 1-2 actions for your day']),
    (TT_RED,    '🚨  UC2 — SLA Alert',           'Real-time — on ticket breach',
     ['Which Jira ticket is overdue and by how many days',
      'Who is the current owner of the ticket',
      'A ready-to-send follow-up draft (you approve and send)']),
    (TEAL,      '📊  UC3 — Weekly Report',        'Every Friday at 16:00',
     ['Full project status — completed vs planned deliverables',
      'FTA and CoQ week-over-week trend',
      'Key risks, blockers, and recommendations',
      'PowerPoint draft ready for your review']),
    (TT_ORANGE, '⚠️  UC4 — Quality Alert',       'Real-time — on metric threshold breach',
     ['Metric name, current value, and threshold crossed',
      'Which project and process type is affected',
      'Suggested action — e.g. "Check orbis-dir-turnrestriction"',
      'Your Power BI report link included']),
]

for i, (clr, title, trigger, bullets) in enumerate(outputs):
    col = i % 2
    row = i // 2
    l = Inches(0.4) + col * Inches(6.5)
    t = Inches(1.55) + row * Inches(2.9)
    add_rect(s, l, t, Inches(6.2), Inches(0.44), clr)
    txt(s, title, l + Inches(0.12), t + Inches(0.04), Inches(4.2), Inches(0.38),
        size=14, bold=True, color=TT_WHITE)
    txt(s, trigger, l + Inches(4.35), t + Inches(0.08), Inches(1.75), Inches(0.32),
        size=10, color=TT_WHITE, italic=True, align=PP_ALIGN.RIGHT)
    add_rect(s, l, t + Inches(0.44), Inches(6.2), Inches(2.38), RGBColor(0xF8, 0xF9, 0xFF))
    bullet_box(s, ['• ' + b for b in bullets],
               l + Inches(0.15), t + Inches(0.52), Inches(5.9), Inches(2.18), size=12)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 8 — What Action to Take
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, RGBColor(0xF4, 0xF6, 0xFB))
header_bar(s, 'What Action to Take When You Receive a Trigger',
           'You are always in control — the AI only informs, you decide')

actions = [
    (TT_BLUE,   '🌅  Morning Briefing',
     ['Read the RAG status at the top (Green / Amber / Red).',
      'GREEN: no action needed — your day is on track.',
      'AMBER: review the flagged Jira tickets or metric warning.',
      'RED: review the draft message the AI has prepared, then send if you agree.']),
    (TT_RED,    '🚨  SLA Alert',
     ['The AI shows you which ticket is overdue and by how many days.',
      'A ready-to-send follow-up draft is attached.',
      'Review the draft, edit if needed, then send it yourself.',
      'The AI never sends anything without you clicking send.']),
    (TEAL,      '📊  Weekly Report',
     ['Open the PowerPoint draft from your Friday briefing.',
      'All numbers are pre-filled from Jira and Databricks.',
      'Add your own commentary where needed.',
      'Share with your manager or team when you are satisfied.']),
    (TT_ORANGE, '⚠️  Quality Alert (FTA / CoQ)',
     ['A metric has crossed your personal threshold — this needs your attention.',
      'Open the Power BI dashboard link included in the alert.',
      'Check the process type or work package the AI flagged.',
      'Decide: investigate yourself, escalate, or note as a known issue.']),
]

for i, (clr, title, bullets) in enumerate(actions):
    col = i % 2
    row = i // 2
    l = Inches(0.4) + col * Inches(6.5)
    t = Inches(1.55) + row * Inches(2.9)
    add_rect(s, l, t, Inches(6.2), Inches(0.44), clr)
    txt(s, title, l + Inches(0.12), t + Inches(0.04), Inches(5.9), Inches(0.38),
        size=14, bold=True, color=TT_WHITE)
    add_rect(s, l, t + Inches(0.44), Inches(6.2), Inches(2.38), RGBColor(0xF8, 0xF9, 0xFF))
    bullet_box(s, ['→  ' + b for b in bullets],
               l + Inches(0.15), t + Inches(0.52), Inches(5.9), Inches(2.18), size=12)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 9 — What the AI Will NEVER Do
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, RGBColor(0xF4, 0xF6, 0xFB))
header_bar(s, 'What the AI Will NEVER Do',
           'Built-in rules that keep you in full control at all times')

never = [
    ('Send an email or Teams message on your behalf',
     'All drafts are shown to you first. Nothing goes out without your explicit approval.'),
    ('Close, approve, or transition a Jira ticket',
     'The AI reads tickets and flags issues. Only you can move or close a ticket.'),
    ('Make a decision for you',
     'When there is a trade-off, the AI presents options with data. You choose.'),
    ('Contact your manager without your sign-off',
     'Even if 3 reminders have gone unanswered, the AI drafts the escalation and waits for your go-ahead.'),
    ('Access data outside your approved scope',
     'It only reads Jira, Confluence, and Power BI — exactly what you consented to in the onboarding form.'),
    ('Alert you at night',
     'Quiet hours (19:00 - 08:00) are always respected. Only a complete system failure would send a night alert.'),
]

for i, (title, desc) in enumerate(never):
    col = i % 2
    row = i // 2
    l = Inches(0.4) + col * Inches(6.5)
    t = Inches(1.55) + row * Inches(1.9)
    add_rect(s, l, t, Inches(6.2), Inches(1.78), RGBColor(0xFF, 0xEB, 0xEE))
    add_rect(s, l, t, Inches(6.2), Inches(0.44), TT_RED)
    txt(s, 'X  ' + title, l + Inches(0.12), t + Inches(0.04), Inches(5.9), Inches(0.38),
        size=13, bold=True, color=TT_WHITE)
    txt(s, desc, l + Inches(0.15), t + Inches(0.52), Inches(5.9), Inches(1.12),
        size=12, color=TT_TEXT)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 10 — What We Need From You
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, RGBColor(0xF4, 0xF6, 0xFB))
header_bar(s, 'What We Need From You',
           'Your feedback shapes how the AI works for you — this is a beta')

txt(s, 'During the beta, we ask you to do 3 things:', Inches(0.6), Inches(1.6),
    Inches(12), Inches(0.38), size=15, bold=True, color=TT_DARK)

three = [
    (TT_BLUE,  '1  Complete the Onboarding Form',
     ['Takes about 10 minutes.',
      'The form link will be shared today.',
      'Your profile is created within 24 hours.',
      'You can update it anytime.']),
    (TT_GREEN, '2  Validate Your First Week of Triggers',
     ['For each briefing or alert you receive, tell us: Useful / Partly / Not useful.',
      'Tell us if a threshold feels too sensitive or not sensitive enough.',
      'Tell us if a project or stakeholder is missing from your profile.']),
    (TEAL,     '3  Report Issues Openly',
     ['Flag immediately if you receive wrong data or a stale number.',
      'Tell us if something is missing from your morning briefing.',
      'Tell us if you receive too many or too few alerts.',
      'All feedback goes directly to Lalit for a same-day profile update.']),
]

for i, (clr, title, bullets) in enumerate(three):
    l = Inches(0.4) + i * Inches(4.35)
    t = Inches(2.1)
    add_rect(s, l, t, Inches(4.15), Inches(0.48), clr)
    txt(s, title, l + Inches(0.12), t + Inches(0.06), Inches(3.95), Inches(0.4),
        size=14, bold=True, color=TT_WHITE)
    add_rect(s, l, t + Inches(0.48), Inches(4.15), Inches(4.15), RGBColor(0xF8, 0xF9, 0xFF))
    bullet_box(s, ['• ' + b for b in bullets],
               l + Inches(0.15), t + Inches(0.58), Inches(3.85), Inches(3.95),
               size=13, spacing=5)

add_rect(s, Inches(0.4), Inches(6.78), Inches(12.93), Inches(0.48), TT_BLUE)
txt(s, '📅  Onboarding forms open today.  First briefings go live within 48 hours of your form submission.',
    Inches(0.6), Inches(6.82), Inches(12.5), Inches(0.42),
    size=13, bold=True, color=TT_WHITE)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 11 — Q&A / Close
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, TT_DARK)
add_rect(s, 0, Inches(3.05), W, Inches(0.07), TT_BLUE)
txt(s, 'Questions?', Inches(1), Inches(1.0), Inches(11), Inches(1.5),
    size=58, bold=True, color=TT_WHITE, align=PP_ALIGN.CENTER)
txt(s, 'Lalit Patkar  |  lalit.patkar@tomtom.com',
    Inches(1), Inches(3.35), Inches(11), Inches(0.55),
    size=18, color=RGBColor(0xB0, 0xC4, 0xDE), align=PP_ALIGN.CENTER)
txt(s, 'OPS Native AI Beta  —  October 2026  |  TomTom Maps Operations',
    Inches(1), Inches(3.95), Inches(11), Inches(0.45),
    size=13, color=TT_GREY, align=PP_ALIGN.CENTER)
txt(s, 'Onboarding form link shared today.\nFirst briefing live within 48 hours of your form submission.',
    Inches(2.5), Inches(5.1), Inches(8.5), Inches(1.1),
    size=16, color=RGBColor(0xB0, 0xC4, 0xDE), align=PP_ALIGN.CENTER)

prs.save('OPS_NativeAI_Beta_User_Briefing.pptx')
print('Saved: OPS_NativeAI_Beta_User_Briefing.pptx')
