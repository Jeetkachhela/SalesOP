import logging
from app.core.database import engine, Base
from app.models.user import User
from app.models.upload import Upload
from app.models.analysis import DataQualityReport, StatisticalFinding, AIInsightReport
from app.models.session import AnalysisSession
from app.models.interactions import UserAnnotation, ChatHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db() -> None:
    logger.info("Creating initial data")
    # Base.metadata.drop_all(bind=engine) # Optional: drop if testing
    Base.metadata.create_all(bind=engine)
    logger.info("Initial data created")

def main() -> None:
    logger.info("Initializing service")
    init_db()
    logger.info("Service finished initializing")

if __name__ == "__main__":
    main()
