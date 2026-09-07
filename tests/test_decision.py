from src.healthtech_service import decide_notification


def test_urgent_document_guidance_escalates_patient_notification():
    result = decide_notification("Call the clinic the same day for urgent symptoms.", "2026-09-12")
    assert result.status == "escalate"
    assert "today" in result.message


def test_routine_guidance_keeps_appointment_scheduled():
    result = decide_notification("Bring your medication list to the visit.", "2026-09-12")
    assert result.status == "scheduled"
    assert "2026-09-12" in result.message
