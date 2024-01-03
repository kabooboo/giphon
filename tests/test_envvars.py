"""
Unit tests for the siphon module.

Integration test for the main function.
"""


from giphon.envvars import _match_environment_to_scope


def test_match_environment_to_scope():
    # Regular successful tests
    assert (
        _match_environment_to_scope(environment="env/dev", scope="env/dev")
        is True
    )
    assert (
        _match_environment_to_scope(environment="env/dev", scope="env/*")
        is True
    )

    assert (
        _match_environment_to_scope(environment="env/dev", scope="*/dev")
        is True
    )

    # Test unmatching wildcards
    assert (
        _match_environment_to_scope(environment="env/dev", scope="toto/*")
        is False
    )

    # Test another separation token
    assert (
        _match_environment_to_scope(environment="env+dev", scope="env+*")
        is True
    )

    # Test: not a regular regex
    assert (
        _match_environment_to_scope(environment="env/dev", scope="env/.*")
        is False
    )


def test_source():
    """
    TODO: setup a fake directory structure with hierarchy and test variables
    are printed in the correct order.
    """
    ...
