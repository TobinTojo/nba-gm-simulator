"""News and transaction feed."""

from sqlalchemy.orm import Session

from app.models import Transaction
from app.schemas import NewsItem


def log_news(
    db: Session,
    season: str,
    transaction_type: str,
    description: str,
    career_id: int | None = None,
) -> NewsItem:
    entry = Transaction(
        season=season,
        transaction_type=transaction_type,
        description=description,
        career_id=career_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return NewsItem.model_validate(entry)


def get_news(db: Session, season: str | None = None, career_id: int | None = None, limit: int = 30) -> list[NewsItem]:
    query = db.query(Transaction).order_by(Transaction.created_at.desc())
    if career_id is not None:
        query = query.filter(Transaction.career_id == career_id)
    elif season:
        query = query.filter(Transaction.season == season)
    return [NewsItem.model_validate(item) for item in query.limit(limit).all()]
