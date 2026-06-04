def enable_system_truststore() -> None:
    """
    Route Python HTTPS verification through the OS trust store when available.

    Local macOS and corporate-network Python installs can fail SSL validation
    even when the browser and curl work. The optional truststore package fixes
    that without changing app behavior in environments where it is unavailable.
    """
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:
        pass
