"""API and database tests through the real routes and a temporary database.
The LLM is replaced by a simple fake here, so these test our pipeline and not the model."""
import io

import fitz
import pytest
from docx import Document as WordDocument

from app.nlp import extraction, llm, quality, user_stories
from app.nlp.extraction import ExtractedRequirement, ExtractionResult
from app.nlp.llm import LLMUnavailable
from app.nlp.quality import ContradictionCheck, LLMReview
from app.nlp.user_stories import StoryDraft


def fake_extract(_system, prompt, _schema):
    """Pretends to be the LLM: returns the sentence, unless it mentions the company."""
    sentence = prompt.split('Sentence: "')[1].split('"')[0]
    if "company" in sentence:
        return ExtractionResult(requirements=[])
    return ExtractionResult(requirements=[ExtractedRequirement(text=sentence, actor="")])


def fake_story(_system, prompt, _schema):
    requirement = prompt.split('"')[1].rstrip(".")
    return StoryDraft(role="user", feature=requirement.lower(), benefit="it helps", acceptance_criteria=[requirement + "."])


def fake_quality(_system, _prompt, schema):
    return LLMReview(issues=[]) if schema is LLMReview else ContradictionCheck(contradiction=False, explanation="")


@pytest.fixture()
def fake_llm(monkeypatch):
    monkeypatch.setattr(extraction, "ask_llm", fake_extract)
    monkeypatch.setattr(user_stories, "ask_llm", fake_story)
    monkeypatch.setattr(quality, "ask_llm", fake_quality)


TEXT = ("Our company sells furniture. Users can log in. The website should be very fast. "
        "Users can log in. Admins must not delete logs. Admins can delete logs.")


def make_project(client, text=TEXT):
    project = client.post("/api/projects", json={"name": "Demo"}).json()
    if text:
        assert client.post(f"/api/projects/{project['id']}/documents/text", json={"text": text}).status_code == 201
    return project["id"]


def analyse(client, project_id, steps=None):
    assert client.post(f"/api/projects/{project_id}/analyze", json={"steps": steps}).status_code == 202
    return client.get(f"/api/projects/{project_id}").json()


def requirements(client, project_id):
    return client.get(f"/api/projects/{project_id}/requirements").json()


# ----- Projects and database -----

def test_project_create_edit_delete(client):
    project_id = make_project(client)
    assert client.patch(f"/api/projects/{project_id}", json={"name": "New"}).json()["name"] == "New"
    assert client.delete(f"/api/projects/{project_id}").status_code == 204
    assert client.get(f"/api/projects/{project_id}").status_code == 404


def test_blank_project_name_is_refused(client):
    assert client.post("/api/projects", json={"name": ""}).status_code == 422


def test_deleting_a_project_deletes_everything_inside(client, fake_llm):
    from app.database import SessionLocal
    from app.models import Document, DuplicatePair, QualityIssue, Requirement, UserStory
    project_id = make_project(client)
    analyse(client, project_id)
    client.delete(f"/api/projects/{project_id}")
    with SessionLocal() as db:
        for table in (Document, Requirement, DuplicatePair, QualityIssue, UserStory):
            assert db.query(table).count() == 0, table


def test_deleting_a_document_deletes_its_requirements(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    document = client.get(f"/api/projects/{project_id}/documents").json()[0]
    assert client.delete(f"/api/documents/{document['id']}").status_code == 204
    assert requirements(client, project_id) == []


def test_sample_project_has_source_text(client):
    project = client.post("/api/projects/sample").json()
    documents = client.get(f"/api/projects/{project['id']}/documents").json()
    assert "ShopEasy" in documents[0]["text"]


def test_upload_formats(client):
    project_id = make_project(client, text=None)
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Users can log in.")
    word = WordDocument()
    word.add_paragraph("Admins can export data.")
    buffer = io.BytesIO()
    word.save(buffer)
    files = {"a.txt": b"Guests can browse.", "a.pdf": pdf.tobytes(), "a.docx": buffer.getvalue()}
    for name, content in files.items():
        response = client.post(f"/api/projects/{project_id}/documents/upload", files={"file": (name, content)})
        assert response.status_code == 201, name
    assert client.post(f"/api/projects/{project_id}/documents/upload", files={"file": ("a.exe", b"x")}).status_code == 422


# ----- Analysis -----

def test_full_analysis_keeps_source_links(client, fake_llm):
    project_id = make_project(client)
    project = analyse(client, project_id)
    assert project["analysis_status"] == "done"
    rows = requirements(client, project_id)
    assert len(rows) == 5  # the company sentence is not a requirement
    for row in rows:
        assert TEXT[row["source_start"]:row["source_end"]] == row["source_sentence"]
        assert row["req_type"] in ("functional", "non_functional")
        assert row["status"] == "pending"


def test_repeated_requirement_is_flagged_but_not_removed(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    assert sum(row["text"] == "Users can log in." for row in requirements(client, project_id)) == 2
    pairs = client.get(f"/api/projects/{project_id}/duplicates").json()
    identical = [pair for pair in pairs if pair["text_a"] == pair["text_b"]]
    assert identical and identical[0]["score"] > 0.99 and identical[0]["status"] == "pending"


def test_contradiction_is_flagged(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    issues = client.get(f"/api/projects/{project_id}/issues").json()
    found = [issue for issue in issues if issue["kind"] == "potential_contradiction"]
    assert found and found[0]["other_requirement_text"]
    assert found[0]["origin"] == "rule"


def test_vague_requirement_is_flagged(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    questions = [issue["question"] for issue in client.get(f"/api/projects/{project_id}/issues").json()]
    assert "What response-time target should the website meet?" in questions


def test_threshold_changes_results(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    low = len(client.get(f"/api/projects/{project_id}/duplicates").json())
    client.patch(f"/api/projects/{project_id}", json={"similarity_threshold": 1.0})
    analyse(client, project_id, ["duplicates"])
    assert len(client.get(f"/api/projects/{project_id}/duplicates").json()) < low


def test_analysis_without_text_is_refused(client):
    project_id = make_project(client, text=None)
    assert client.post(f"/api/projects/{project_id}/analyze", json={}).status_code == 422


def test_second_analysis_is_refused_while_running(client):
    from app.database import SessionLocal
    from app.models import Project
    project_id = make_project(client)
    with SessionLocal() as db:
        db.get(Project, project_id).analysis_status = "running"
        db.commit()
    assert client.post(f"/api/projects/{project_id}/analyze", json={}).status_code == 409
    assert client.delete(f"/api/projects/{project_id}").status_code == 409


# ----- Honest failure -----

def test_ollama_failure_is_reported_and_nothing_is_invented(client, monkeypatch):
    def offline(*_):
        raise LLMUnavailable("Cannot reach Ollama.")
    monkeypatch.setattr(extraction, "ask_llm", offline)
    project_id = make_project(client)
    project = analyse(client, project_id)
    assert project["analysis_status"] == "failed"
    assert "Cannot reach Ollama" in project["analysis_error"]
    assert requirements(client, project_id) == []


def test_analysis_can_recover_after_failure(client, monkeypatch, fake_llm):
    def offline(*_):
        raise LLMUnavailable("Cannot reach Ollama.")
    monkeypatch.setattr(extraction, "ask_llm", offline)
    project_id = make_project(client)
    assert analyse(client, project_id)["analysis_status"] == "failed"
    monkeypatch.setattr(extraction, "ask_llm", fake_extract)
    assert analyse(client, project_id)["analysis_status"] == "done"
    assert requirements(client, project_id)


def test_failed_sentence_becomes_a_warning(client, monkeypatch, fake_llm):
    monkeypatch.setattr(extraction, "ask_llm", lambda *_: ExtractionResult(requirements=[]))
    project_id = make_project(client, text="The system must send invoices.")
    project = analyse(client, project_id)
    assert project["analysis_status"] == "done"
    assert project["analysis_warnings"][0]["source"] == "The system must send invoices."
    assert requirements(client, project_id) == []


def test_llm_outage_during_quality_keeps_rule_results(client, monkeypatch, fake_llm):
    def offline(*_):
        raise LLMUnavailable("Cannot reach Ollama.")
    monkeypatch.setattr(quality, "ask_llm", offline)
    project_id = make_project(client)
    project = analyse(client, project_id, ["extract", "classify", "quality"])
    assert project["analysis_status"] == "done"
    assert any(item["step"] == "quality" for item in project["analysis_warnings"])
    assert client.get(f"/api/projects/{project_id}/issues").json()


def test_status_reports_missing_ollama(client, monkeypatch):
    def offline():
        raise LLMUnavailable("Cannot reach Ollama.")
    monkeypatch.setattr(llm, "list_models", offline)
    status = client.get("/api/system/status").json()
    assert status["ollama_running"] is False and status["active_model"] is None
    assert "Cannot reach" in status["message"]


@pytest.mark.parametrize("installed, selected, expected", [
    (["llama3:8b", "qwen3:4b", "qwen3:4b-instruct"], "", "qwen3:4b-instruct"),
    (["llama3:8b", "qwen3:4b"], "", "qwen3:4b"),
    (["llama3:8b"], "", None),
    (["llama3:8b", "qwen3:4b"], "llama3:8b", "llama3:8b"),
    (["qwen3:4b"], "missing:1b", None),
])
def test_model_choice(monkeypatch, installed, selected, expected):
    monkeypatch.setattr(llm, "selected_model", selected)
    assert llm.choose_model(installed) == expected


# ----- Human review -----

def test_edit_keeps_original_wording_and_source(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    row = requirements(client, project_id)[0]
    updated = client.patch(f"/api/requirements/{row['id']}", json={"text": "Users can log in with email."}).json()
    assert updated["edited"] is True
    assert updated["original_text"] == row["text"]
    assert updated["source_sentence"] == row["source_sentence"]


def test_editing_text_refreshes_rule_issues(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    fast = next(row for row in requirements(client, project_id) if "fast" in row["text"])
    client.patch(f"/api/requirements/{fast['id']}", json={"text": "Pages must load in 2 seconds."})
    remaining = [i for i in client.get(f"/api/projects/{project_id}/issues").json()
                 if i["requirement_id"] == fast["id"] and i["kind"] == "vague_expression"]
    assert remaining == []


def test_reviews_and_edits_survive_a_rerun(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    rows = requirements(client, project_id)
    accepted, edited, retyped, rejected = rows[0], rows[1], rows[2], rows[3]
    client.patch(f"/api/requirements/{accepted['id']}", json={"status": "accepted"})
    client.patch(f"/api/requirements/{edited['id']}", json={"text": "Changed by a person."})
    client.patch(f"/api/requirements/{retyped['id']}", json={"req_type": "functional"})
    client.patch(f"/api/requirements/{rejected['id']}", json={"status": "rejected"})
    pair = client.get(f"/api/projects/{project_id}/duplicates").json()[0]
    client.patch(f"/api/duplicates/{pair['id']}", json={"status": "confirmed"})

    analyse(client, project_id)

    after = {row["id"]: row for row in requirements(client, project_id)}
    assert len(after) == len(rows)
    assert after[accepted["id"]]["status"] == "accepted"
    assert after[edited["id"]]["text"] == "Changed by a person."
    assert after[retyped["id"]]["req_type"] == "functional"
    assert after[rejected["id"]]["status"] == "rejected"
    pairs = {row["id"]: row for row in client.get(f"/api/projects/{project_id}/duplicates").json()}
    assert pairs[pair["id"]]["status"] == "confirmed"


def test_rejected_requirement_leaves_counts_and_lists(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    rows = requirements(client, project_id)
    before = client.get(f"/api/projects/{project_id}").json()["stats"]["total"]
    client.patch(f"/api/requirements/{rows[0]['id']}", json={"status": "rejected"})
    stats = client.get(f"/api/projects/{project_id}").json()["stats"]
    assert stats["total"] == before - 1 and stats["rejected"] == 1
    listed = {story["requirement_id"] for story in client.get(f"/api/projects/{project_id}/stories").json()}
    assert rows[0]["id"] not in listed


def test_changing_to_functional_clears_category(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    row = next(r for r in requirements(client, project_id) if r["req_type"] == "non_functional")
    updated = client.patch(f"/api/requirements/{row['id']}", json={"req_type": "functional"}).json()
    assert updated["nfr_category"] is None and updated["predicted_type"] == "non_functional"


def test_invalid_status_is_refused(client, fake_llm):
    project_id = make_project(client)
    analyse(client, project_id)
    row = requirements(client, project_id)[0]
    assert client.patch(f"/api/requirements/{row['id']}", json={"status": "approved-by-client"}).status_code == 422


def test_add_requirement_by_hand(client):
    project_id = make_project(client, text=None)
    row = client.post(f"/api/projects/{project_id}/requirements", json={"text": "Users can log out."}).json()
    assert row["origin"] == "human" and row["status"] == "accepted" and row["source_sentence"] == ""


def test_mark_duplicate_by_hand_merges_nothing(client):
    project_id = make_project(client, text=None)
    a = client.post(f"/api/projects/{project_id}/requirements", json={"text": "Users can log out."}).json()
    b = client.post(f"/api/projects/{project_id}/requirements", json={"text": "Users can upload files."}).json()
    pair = client.post(f"/api/projects/{project_id}/duplicates", json={"req_a_id": a["id"], "req_b_id": b["id"]}).json()
    assert pair["status"] == "confirmed"
    assert len(requirements(client, project_id)) == 2
    assert client.post(f"/api/projects/{project_id}/duplicates", json={"req_a_id": a["id"], "req_b_id": a["id"]}).status_code == 422


def test_story_edit_and_approval(client, fake_llm):
    project_id = make_project(client, text="Users can log in.")
    analyse(client, project_id)
    story = client.get(f"/api/projects/{project_id}/stories").json()[0]
    assert story["status"] == "pending"
    updated = client.patch(f"/api/stories/{story['id']}", json={"benefit": "I can work", "status": "accepted"}).json()
    assert updated["benefit"] == "I can work" and updated["edited"] and updated["status"] == "accepted"


# ----- Export and other endpoints -----

@pytest.mark.parametrize("file_format, start", [("pdf", b"%PDF"), ("docx", b"PK")])
def test_export_download(client, fake_llm, file_format, start):
    project_id = make_project(client)
    analyse(client, project_id)
    response = client.get(f"/api/projects/{project_id}/export/{file_format}")
    assert response.status_code == 200 and response.content.startswith(start)
    assert f"requirements.{file_format}" in response.headers["content-disposition"]


def test_export_separates_approved_from_unreviewed(client, fake_llm):
    project_id = make_project(client, text="Users can log in. Users can upload files.")
    analyse(client, project_id)
    stories = client.get(f"/api/projects/{project_id}/stories").json()
    client.patch(f"/api/stories/{stories[0]['id']}", json={"status": "accepted"})
    response = client.get(f"/api/projects/{project_id}/export/pdf")
    with fitz.open(stream=response.content, filetype="pdf") as pdf:
        text = " ".join(" ".join(page.get_text().split()) for page in pdf)
    approved_section = text.split("8. Approved user stories")[1].split("9. Unreviewed AI draft")[0]
    draft_section = text.split("9. Unreviewed AI draft")[1]
    assert "log in" in approved_section and "upload files" not in approved_section
    assert "upload files" in draft_section and "NOT APPROVED" in draft_section


def test_unknown_export_format(client):
    project_id = make_project(client, text=None)
    assert client.get(f"/api/projects/{project_id}/export/xls").status_code == 404


def test_metrics_and_predict_endpoints(client):
    assert client.get("/api/model/metrics").json()["type_model"]["test_rows"] > 0
    assert client.post("/api/model/predict", json={"text": "Users can register."}).json()["type"] == "functional"
