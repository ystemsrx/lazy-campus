import enum


class UserRole(str, enum.Enum):
    USER = 'user'
    ADMIN = 'admin'


class Gender(str, enum.Enum):
    MALE = 'male'
    FEMALE = 'female'
    OTHER = 'other'


class ContactVisibility(str, enum.Enum):
    AFTER_ACCEPT = 'after_accept'
    INTERNAL_ONLY = 'internal_only'


class TaskStatus(str, enum.Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELED = 'canceled'
    UNDER_REVIEW = 'under_review'


class ReportType(str, enum.Enum):
    REPORT = 'report'
    APPEAL = 'appeal'


class ReportStatus(str, enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class RatingTargetRole(str, enum.Enum):
    PUBLISHER = 'publisher'
    WORKER = 'worker'
