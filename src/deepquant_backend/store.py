import os
from typing import List, Optional

from tinydb import Query, TinyDB

from .schemas import Policy, StrategyConfig


class PolicyStore:
    def __init__(self, db_path: str = "backend/data/policies.json"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = TinyDB(db_path)

    def add_policy(
        self, policy_id: str, prompt: str, strategy: StrategyConfig, name: str
    ) -> Policy:
        record = {
            "id": policy_id,
            "prompt": prompt,
            "name": name,
            "strategy": strategy.dict(),
        }
        self.db.insert(record)
        return Policy(id=policy_id, prompt=prompt, name=name, strategy=strategy)

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        query = Query()
        result = self.db.get(query.id == policy_id)
        if not result:
            return None
        normalized = {**result, "strategy": StrategyConfig(**result["strategy"])}
        return Policy(**normalized)

    def list_policies(self) -> List[Policy]:
        items = self.db.all()
        normalized_items = [
            {**item, "strategy": StrategyConfig(**item["strategy"])} for item in items
        ]
        return [Policy(**item) for item in normalized_items]
