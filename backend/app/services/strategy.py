from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analytics import Experiment
from app.services.providers import WEIGHTS, WEIGHT_KEYS, normalize_weights

DEFAULT_STRATEGY_VERSION = "v1"


def get_active_strategy(db: Session) -> tuple[str, dict[str, float], str, Optional[int]]:
    """Trả về (strategy_version, weights, source, experiment_id).

    Ưu tiên experiment active mới nhất; chưa có thì dùng v1 mặc định (docs/13
    learning loop: metrics → insights → strategy version → opportunity/angle).
    """
    exp = db.scalar(
        select(Experiment).where(Experiment.status == "active").order_by(Experiment.id.desc())
    )
    if exp is not None:
        return (
            exp.strategy_version,
            normalize_weights(exp.weights or {}),
            "experiment",
            exp.id,
        )
    return (DEFAULT_STRATEGY_VERSION, dict(WEIGHTS), "default", None)