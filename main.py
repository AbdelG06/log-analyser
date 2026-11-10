import os

from ingestion.logging_config import configure_logging
from ingestion.run_pipeline import run
from serving.dashboard import launch_dashboard_app


def main() -> None:
    project_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(project_dir, "data")
    configure_logging()
    run(data_dir)
    launch_dashboard_app()


if __name__ == "__main__":
    main()
