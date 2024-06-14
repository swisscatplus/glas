from typing import Optional

from pydantic import BaseModel


class BaseNodeModel(BaseModel):
    id: str
    name: str
    status: str
    online: bool
    task_id: Optional[str]
