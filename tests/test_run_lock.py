import pytest

from core.run_lock import AlreadyRunningError, single_instance_lock


def test_second_process_lock_is_rejected():
    with single_instance_lock("autoposter-template-test.lock"):
        with pytest.raises(AlreadyRunningError):
            with single_instance_lock("autoposter-template-test.lock"):
                pass
