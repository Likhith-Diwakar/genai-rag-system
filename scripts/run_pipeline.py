from src.scheduler.sync_scheduler import run_full_pipeline
from src.utils.logger import logger

if __name__ == "__main__":

    logger.info("Starting scheduled RAG pipeline run...")

    try:
        run_full_pipeline()
        logger.info("RAG pipeline completed successfully.")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise
