"""Collects everything the PDF and DOCX reports need, so both show the same content."""
from datetime import datetime

from ..nlp.user_stories import story_sentence
from ..models import Document, DuplicatePair, QualityIssue, Requirement, UserStory

TYPE_NAMES = {"functional": "Functional", "non_functional": "Non-functional", None: "Unclassified"}
STATUS_NAMES = {
    "accepted": "Approved", "confirmed": "Confirmed", "pending": "Unreviewed AI suggestion",
    "rejected": "Rejected", "dismissed": "Dismissed",
}
KIND_NAMES = {
    "vague_expression": "Vague expression", "missing_measure": "Missing measurable constraint",
    "unclear_actor": "Unclear actor", "unspecified_behavior": "Unspecified behaviour",
    "potential_contradiction": "Potential contradiction",
}
EXCERPT_LENGTH = 1200


def requirement_status(row):
    if row.origin == "human":
        return "Added by reviewer"
    return STATUS_NAMES[row.status]


def build_report(db, project) -> dict:
    documents = db.query(Document).filter(Document.project_id == project.id).order_by(Document.id).all()
    all_rows = db.query(Requirement).filter(Requirement.project_id == project.id).order_by(Requirement.id).all()
    active = [row for row in all_rows if row.status != "rejected"]
    by_id = {row.id: row for row in active}

    requirements = [
        {
            "id": f"REQ-{row.id}", "text": row.text, "req_type": row.req_type,
            "type": TYPE_NAMES[row.req_type], "category": (row.nfr_category or "-").capitalize(),
            "status": requirement_status(row), "source": row.source_sentence or "Added by reviewer",
        }
        for row in active
    ]

    duplicates = [
        {
            "a": f"REQ-{pair.req_a_id}: {by_id[pair.req_a_id].text}",
            "b": f"REQ-{pair.req_b_id}: {by_id[pair.req_b_id].text}",
            "score": f"{pair.score:.2f}", "reason": pair.reason, "status": STATUS_NAMES[pair.status],
        }
        for pair in db.query(DuplicatePair).filter(DuplicatePair.project_id == project.id)
        .order_by(DuplicatePair.score.desc())
        if pair.status != "dismissed" and pair.req_a_id in by_id and pair.req_b_id in by_id
    ]

    issues = [
        issue for issue in db.query(QualityIssue).filter(QualityIssue.project_id == project.id)
        .order_by(QualityIssue.requirement_id)
        if issue.status != "dismissed" and issue.requirement_id in by_id
    ]
    warnings = [
        {
            "requirement": f"REQ-{issue.requirement_id}: {by_id[issue.requirement_id].text}",
            "kind": KIND_NAMES.get(issue.kind, issue.kind), "message": issue.message,
            "origin": "Rule" if issue.origin == "rule" else "Local LLM",
            "status": "Accepted by reviewer" if issue.status == "accepted" else STATUS_NAMES[issue.status],
        }
        for issue in issues
    ]
    questions = [
        {"requirement": f"REQ-{issue.requirement_id}", "question": issue.question}
        for issue in issues if issue.question
    ]

    stories = [
        {
            "requirement": f"REQ-{story.requirement_id}",
            "story": story_sentence(story.role, story.feature, story.benefit),
            "criteria": story.acceptance_criteria or [], "status": story.status,
        }
        for story in db.query(UserStory).filter(UserStory.project_id == project.id).order_by(UserStory.id)
        if story.requirement_id in by_id and story.status != "rejected"
    ]

    return {
        "title": project.name,
        "description": project.description or "",
        "generated": datetime.now().strftime("%d %B %Y, %H:%M"),
        "stats": {
            "Active requirements": len(active),
            "Approved requirements": sum(row.status == "accepted" for row in active),
            "Unreviewed requirements": sum(row.status == "pending" for row in active),
            "Rejected (not listed)": len(all_rows) - len(active),
            "Potential duplicates": len(duplicates),
            "Quality warnings": len(warnings),
        },
        "documents": [
            {
                "name": document.filename, "words": len(document.text.split()),
                "excerpt": document.text[:EXCERPT_LENGTH] + ("..." if len(document.text) > EXCERPT_LENGTH else ""),
            }
            for document in documents
        ],
        "requirements": requirements,
        "functional": [row for row in requirements if row["req_type"] == "functional"],
        "non_functional": [row for row in requirements if row["req_type"] == "non_functional"],
        "duplicates": duplicates,
        "warnings": warnings,
        "questions": questions,
        "approved_stories": [story for story in stories if story["status"] == "accepted"],
        "draft_stories": [story for story in stories if story["status"] == "pending"],
    }


LEGEND = ("Approved items were accepted by a person using this tool. Unreviewed AI suggestions were "
          "generated automatically and have not been checked. Neither status means that the client "
          "has approved the item.")
QUESTIONS_NOTE = "These questions were inferred by this tool. The client did not state them."
DUPLICATES_NOTE = "High similarity does not prove duplication. No requirement was merged or removed."
WARNINGS_NOTE = "This analysis is not exhaustive. Other ambiguities or contradictions may exist."
DRAFT_NOTE = ("NOT APPROVED. These are unreviewed AI drafts. The benefits and acceptance criteria are "
              "suggestions, and the client did not state them.")
APPROVED_NOTE = ("Approved by a reviewer using this tool. Acceptance criteria are suggestions until "
                 "the client confirms them.")
