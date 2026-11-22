from pydantic import BaseModel


class AdminOverview(BaseModel):
    total_users: int
    total_schemes: int
    total_documents: int
    total_grievances: int
    open_grievances: int
    resolved_grievances: int
    pending_review_grievances: int
    pending_service_tasks: int
    verification_count: int
