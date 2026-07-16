from app.config import settings


def init_sentry() -> bool:
    """
    Initialise Sentry error tracking when SENTRY_DSN is configured.

    No-ops when SENTRY_DSN is unset (local/dev default) or when the sentry_sdk
    package or DSN is invalid, so this never blocks startup. Returns whether
    Sentry was actually enabled, for a single startup log line in main.py.
    """
    if not settings.SENTRY_DSN:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1,
        )
        return True
    except Exception:
        return False
