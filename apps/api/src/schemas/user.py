from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: Optional[str] = None
    is_platform_admin: bool
    created_at: datetime

class UserWithTenantsOut(UserOut):
    workspaces: List[dict] = []
