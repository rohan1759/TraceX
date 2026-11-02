import os
import sqlite3
from datetime import datetime, timezone, time
from sqlmodel import create_engine, Session, select

from pages.helper.data_models import RegisteredCases, PublicSubmissions, UploadAudit

DAILY_REPORTER_SUBMISSION_CAP = 30

sqlite_url = "sqlite:///sqlite_database.db"
engine = create_engine(sqlite_url)


def create_db():
    try:
        RegisteredCases.__table__.create(engine)
    except Exception:
        pass
    try:
        PublicSubmissions.__table__.create(engine)
    except Exception:
        pass
    try:
        UploadAudit.__table__.create(engine)
    except Exception:
        pass
    # Add new columns to existing tables if they don't exist (SQLite migration)
    _migrate_db()


def _migrate_db():
    """Add any new columns to existing tables without dropping data."""
    new_columns = [
        ("registeredcases", "complainant_email", "TEXT"),
        ("registeredcases", "city", "TEXT"),
        ("registeredcases", "description", "TEXT"),
    ]
    try:
        con = sqlite3.connect("sqlite_database.db")
        cursor = con.cursor()
        for table, column, col_type in new_columns:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists
        con.commit()
        con.close()
    except Exception:
        pass


def register_new_case(case_details: RegisteredCases):
    with Session(engine) as session:
        session.add(case_details)
        session.commit()


def fetch_registered_cases(submitted_by: str, status: str, is_admin: bool = False, date_filter=None):
    if status == "All":
        status_list = ["F", "NF"]
    elif status == "Found":
        status_list = ["F"]
    elif status == "Not Found":
        status_list = ["NF"]
    else:
        status_list = ["F", "NF"]

    with Session(engine) as session:
        query = select(
            RegisteredCases.id,
            RegisteredCases.name,
            RegisteredCases.age,
            RegisteredCases.status,
            RegisteredCases.last_seen,
            RegisteredCases.matched_with,
            RegisteredCases.city,
            RegisteredCases.birth_marks,
            RegisteredCases.complainant_name,
            RegisteredCases.complainant_mobile,
            RegisteredCases.submitted_on,
            RegisteredCases.adhaar_card,
            RegisteredCases.father_name,
            RegisteredCases.address,
            RegisteredCases.description,
        ).where(RegisteredCases.status.in_(status_list))

        if not is_admin:
            query = query.where(RegisteredCases.submitted_by == submitted_by)

        if date_filter:
            import datetime
            date_dt = datetime.datetime.combine(date_filter, datetime.time.min)
            query = query.where(RegisteredCases.submitted_on >= date_dt)

        query = query.order_by(RegisteredCases.submitted_on.desc())
        result = session.exec(query).all()
        return result

def fetch_public_cases(train_data: bool, status: str, date_filter=None):
    if train_data:
        with Session(engine) as session:
            result = session.exec(
                select(
                    PublicSubmissions.id,
                    PublicSubmissions.face_mesh,
                ).where(PublicSubmissions.status == status)
            ).all()
            return result

    with Session(engine) as session:
        query = select(
            PublicSubmissions.id,
            PublicSubmissions.status,
            PublicSubmissions.location,
            PublicSubmissions.mobile,
            PublicSubmissions.birth_marks,
            PublicSubmissions.submitted_on,
            PublicSubmissions.submitted_by,
            PublicSubmissions.email,
        )
        if date_filter:
            import datetime
            date_dt = datetime.datetime.combine(date_filter, datetime.time.min)
            query = query.where(PublicSubmissions.submitted_on >= date_dt)

        query = query.order_by(PublicSubmissions.submitted_on.desc())
        result = session.exec(query).all()
        return result

def get_not_confirmed_registered_cases(submitted_by: str):
    with Session(engine) as session:
        result = session.exec(
            select(RegisteredCases)
            .where(RegisteredCases.submitted_by == submitted_by)
            .where(RegisteredCases.status == "NF")
        ).all()
        return result


def get_training_data(submitted_by: str = None):
    with Session(engine) as session:
        query = select(RegisteredCases.id, RegisteredCases.face_mesh).where(
            RegisteredCases.status == "NF"
        )
        if submitted_by:
            query = query.where(RegisteredCases.submitted_by == submitted_by)
        result = session.exec(query).all()
        return result


def new_public_case(public_case_details: PublicSubmissions):
    with Session(engine) as session:
        session.add(public_case_details)
        session.commit()


def get_public_case_detail(case_id: str):
    with Session(engine) as session:
        result = session.exec(
            select(
                PublicSubmissions.location,
                PublicSubmissions.submitted_by,
                PublicSubmissions.mobile,
                PublicSubmissions.birth_marks,
            ).where(PublicSubmissions.id == case_id)
        ).all()
        return result


def get_registered_case_detail(case_id: str):
    with Session(engine) as session:
        result = session.exec(
            select(
                RegisteredCases.name,
                RegisteredCases.complainant_mobile,
                RegisteredCases.complainant_email,
                RegisteredCases.age,
                RegisteredCases.last_seen,
                RegisteredCases.birth_marks,
            ).where(RegisteredCases.id == case_id)
        ).all()
        return result


def list_public_cases():
    with Session(engine) as session:
        result = session.exec(select(PublicSubmissions)).all()
        return result


def update_found_status(register_case_id: str, public_case_id: str, actor_username: str = None):
    with Session(engine) as session:
        registered_case_details = session.exec(
            select(RegisteredCases).where(RegisteredCases.id == str(register_case_id))
        ).one()
        registered_case_details.status = "F"
        registered_case_details.matched_with = str(public_case_id)

        public_case_details = session.exec(
            select(PublicSubmissions).where(PublicSubmissions.id == str(public_case_id))
        ).one()
        public_case_details.status = "F"

        session.add(registered_case_details)
        session.add(public_case_details)
        session.commit()

        reporter = public_case_details.submitted_by or "unknown"

    record_audit_log(
        reporter_username=actor_username or reporter,
        sighting_id=str(public_case_id),
        action="APPROVE",
    )


def record_audit_log(
    reporter_username: str,
    sighting_id: str,
    action: str,
    city: str = None,
    area: str = None,
):
    """Write an accountability log row for sighting upload, approval, or deletion."""
    with Session(engine) as session:
        audit_entry = UploadAudit(
            reporter_username=reporter_username,
            sighting_id=str(sighting_id),
            action=action.upper(),
            city=city,
            area=area,
            timestamp=datetime.now(timezone.utc),
        )
        session.add(audit_entry)
        session.commit()


def get_daily_submissions_count(reporter_username: str) -> int:
    """
    Count total sightings submitted by this reporter today (UTC calendar day).
    Counted from UploadAudit where action == 'SUBMIT'.
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    with Session(engine) as session:
        query = (
            select(UploadAudit)
            .where(UploadAudit.reporter_username == reporter_username)
            .where(UploadAudit.action == "SUBMIT")
            .where(UploadAudit.timestamp >= today_start)
        )
        results = session.exec(query).all()
        return len(results)


def fetch_audit_logs(
    reporter: str = None,
    start_date = None,
    end_date = None,
    action: str = None,
):
    """Retrieve audit log rows with optional filtering by reporter, date range, and action."""
    with Session(engine) as session:
        query = select(UploadAudit)
        if reporter and reporter != "All Reporters":
            query = query.where(UploadAudit.reporter_username == reporter)
        if action and action != "All Actions":
            query = query.where(UploadAudit.action == action)
        if start_date:
            start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
            query = query.where(UploadAudit.timestamp >= start_dt)
        if end_date:
            end_dt = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)
            query = query.where(UploadAudit.timestamp <= end_dt)

        query = query.order_by(UploadAudit.timestamp.desc())
        return session.exec(query).all()


def delete_public_case(case_id: str, actor_username: str = None):
    """Delete a public sighting lead, removing record, disk image, and recording DELETE audit."""
    reporter = "unknown"
    with Session(engine) as session:
        case = session.exec(
            select(PublicSubmissions).where(PublicSubmissions.id == str(case_id))
        ).first()
        if case:
            reporter = case.submitted_by or "unknown"
            session.delete(case)
            session.commit()

    record_audit_log(
        reporter_username=actor_username or reporter,
        sighting_id=str(case_id),
        action="DELETE",
    )

    image_path = f"./resources/{case_id}.jpg"
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
        except OSError:
            pass


def get_registered_cases_count(submitted_by: str, status: str, is_admin: bool = False):
    with Session(engine) as session:
        query = select(RegisteredCases).where(RegisteredCases.status == status)
        if not is_admin:
            query = query.where(RegisteredCases.submitted_by == submitted_by)
        result = session.exec(query).all()
        return result



def get_public_cases_count(status: str = None) -> int:
    with Session(engine) as session:
        query = select(PublicSubmissions)
        if status:
            query = query.where(PublicSubmissions.status == status)
        result = session.exec(query).all()
        return len(result)


def get_case_counts_by_city():
    """Return a dict mapping city -> {found: int, not_found: int}."""
    with Session(engine) as session:
        result = session.exec(
            select(RegisteredCases.city, RegisteredCases.status)
        ).all()
    counts = {}
    for city, status in result:
        if not city:
            city = "Unknown"
        if city not in counts:
            counts[city] = {"found": 0, "not_found": 0}
        if status == "F":
            counts[city]["found"] += 1
        else:
            counts[city]["not_found"] += 1
    return counts


def delete_registered_case(case_id: str):
    with Session(engine) as session:
        case = session.exec(
            select(RegisteredCases).where(RegisteredCases.id == case_id)
        ).one()
        session.delete(case)
        session.commit()
    # Remove image from disk
    image_path = f"./resources/{case_id}.jpg"
    if os.path.exists(image_path):
        os.remove(image_path)


def update_registered_case(case_id: str, fields: dict):
    with Session(engine) as session:
        case = session.exec(
            select(RegisteredCases).where(RegisteredCases.id == case_id)
        ).one()
        for key, value in fields.items():
            setattr(case, key, value)
        session.add(case)
        session.commit()


if __name__ == "__main__":
    r = fetch_public_cases("NF")
    print(r)
