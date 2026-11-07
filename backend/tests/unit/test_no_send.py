"""Guarantee: the application contains no email-sending capability (requirement: never send automatically)."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
FORBIDDEN = re.compile(r"smtplib|sendgrid|mailgun|postmark|gmail|send_mail|send_email|sendmail|ses\.send|"
                       r"\.send_message\(|aiosmtplib|email\.mime", re.I)


def test_no_email_sending_code_in_app():
    hits = [f"{p.relative_to(APP)}:{n}: {line.strip()}"
            for p in APP.rglob("*.py") for n, line in enumerate(p.read_text().splitlines(), 1)
            if FORBIDDEN.search(line) and not line.strip().startswith("#")]
    assert hits == [], "Email-sending code found:\n" + "\n".join(hits)


def test_review_options_offer_no_send_action():
    from app.models import ReviewDecision
    actions = set(ReviewDecision.model_fields["action"].annotation.__args__)
    assert actions == {"approve", "reject", "edit", "choose_signal", "regenerate"}
