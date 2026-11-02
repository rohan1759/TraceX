import os
import sqlite3
from sqlmodel import create_engine, Session, select

from pages.helper.data_models import RegisteredCases, PublicSubmissions

sqlite_url = "sqlite:///sqlite_database.db"
engine = create_engine(sqlite_url)


def create_db():
    try:
        RegisteredCases.__table__.create(engine)
        PublicSubmissions.__table__.create(engine)
    except:
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


def update_found_status(register_case_id: str, public_case_id: str):
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
