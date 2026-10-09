def test_cleanup():
    from etl.cleanup import cleanup_old_files

    cleanup_old_files()


def test_admin():
    from api.admin import router

    assert router is not None


def test_notifications():
    from etl.notifications import notify_admin

    assert callable(notify_admin)
