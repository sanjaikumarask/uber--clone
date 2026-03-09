from .incentive_engine import IncentiveEngine


def apply_driver_incentive(ride):
    """
    Called on ride completion to process all eligible driver incentives.
    Entry point used by apps.rides.services.complete_ride.
    """
    try:
        IncentiveEngine.process_ride_completion(ride)
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(
            f"Incentive processing failed for ride {ride.id}: {e}"
        )
    return 0
