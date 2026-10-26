from pathlib import Path
import json
from pymongo import MongoClient
from pymongo.errors import PyMongoError


DATABASE_NAME = "bih_curriculum"
COLLECTION_NAME = "courses"
MONGODB_URI = "mongodb://localhost:27017/"


def main():

    project_root = Path(__file__).resolve().parent.parent

    json_path = (
        project_root
        / "data"
        / "structured"
        / "unified"
        / "all_courses.json"
    )

    print("=" * 90)
    print("MONGODB DATA LOAD")
    print("=" * 90)

    print(f"Input JSON: {json_path}")

    if not json_path.exists():
        print("\nERROR: Unified JSON file does not exist.")
        raise SystemExit(1)

    with json_path.open("r", encoding="utf-8") as file:
        courses = json.load(file)

    print(f"Loaded {len(courses)} records from JSON.")

    if not isinstance(courses, list):
        print("\nERROR: JSON root must be a list of course records.")
        raise SystemExit(1)

    if len(courses) == 0:
        print("\nERROR: JSON contains no course records.")
        raise SystemExit(1)

    client = None

    try:
        print(f"\nConnecting to MongoDB: {MONGODB_URI}")

        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
        )

        # Force an actual connection check.
        client.admin.command("ping")

        print("MongoDB connection successful.")

        database = client[DATABASE_NAME]
        collection = database[COLLECTION_NAME]

        print(
            f"Target database: {DATABASE_NAME}\n"
            f"Target collection: {COLLECTION_NAME}"
        )

        # --------------------------------------------------
        # RESET COLLECTION
        # --------------------------------------------------
        #
        # For this reproducible dataset pipeline we rebuild the
        # collection from the current validated JSON each time.
        # This prevents duplicate records when the script is rerun.
        #
        existing_count = collection.count_documents({})

        if existing_count > 0:
            print(
                f"\nExisting documents found: {existing_count}"
            )
            print("Clearing existing collection before reload...")

            collection.delete_many({})

        # --------------------------------------------------
        # INSERT DATA
        # --------------------------------------------------

        result = collection.insert_many(courses)

        print(
            f"\nInserted documents: "
            f"{len(result.inserted_ids)}"
        )

        # --------------------------------------------------
        # INDEXES
        # --------------------------------------------------

        collection.create_index(
            "dataset_id",
            unique=True,
            name="idx_dataset_id_unique",
        )

        collection.create_index(
            "institution_key",
            name="idx_institution_key",
        )

        collection.create_index(
            "course_name",
            name="idx_course_name",
        )

        collection.create_index(
            "course_code",
            name="idx_course_code",
        )

        collection.create_index(
            [
                ("institution_key", 1),
                ("year_of_study", 1),
                ("semester", 1),
            ],
            name="idx_institution_year_semester",
        )

        print("Indexes created successfully.")

        # --------------------------------------------------
        # VALIDATION
        # --------------------------------------------------

        total_count = collection.count_documents({})

        fit_count = collection.count_documents(
            {"institution_key": "fit"}
        )

        ibu_count = collection.count_documents(
            {"institution_key": "ibu"}
        )

        etf_count = collection.count_documents(
            {"institution_key": "etf"}
        )

        source_inconsistency_count = (
            collection.count_documents(
                {"has_source_inconsistency": True}
            )
        )

        print("\n" + "-" * 90)
        print("DATABASE VALIDATION")
        print("-" * 90)

        print(f"Total documents: {total_count}")
        print(f"FIT documents:   {fit_count}")
        print(f"IBU documents:   {ibu_count}")
        print(f"ETF documents:   {etf_count}")

        print(
            "Source inconsistencies: "
            f"{source_inconsistency_count}"
        )

        expected = {
            "total": 120,
            "fit": 35,
            "ibu": 44,
            "etf": 41,
            "inconsistencies": 14,
        }

        checks_ok = (
            total_count == expected["total"]
            and fit_count == expected["fit"]
            and ibu_count == expected["ibu"]
            and etf_count == expected["etf"]
            and source_inconsistency_count
            == expected["inconsistencies"]
        )

        if checks_ok:
            print(
                "\nSUCCESS: MongoDB contains the expected "
                "validated dataset."
            )
        else:
            print(
                "\nWARNING: MongoDB counts do not match "
                "the expected validated dataset."
            )

        print("\n" + "=" * 90)
        print("MONGODB LOAD FINISHED")
        print("=" * 90)

    except PyMongoError as error:
        print("\nMONGODB ERROR:")
        print(error)
        print(
            "\nCheck that MongoDB is installed and the "
            "MongoDB service is running on localhost:27017."
        )
        raise SystemExit(1)

    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()
