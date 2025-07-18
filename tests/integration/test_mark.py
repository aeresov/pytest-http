def test_mark_skip(pytester):
    pytester.copy_example("conftest.py")
    pytester.copy_example("test_mark_skip.http.json")
    result = pytester.runpytest()
    # No stages = no tests to run
    result.assert_outcomes()


def test_mark_xfail(pytester):
    pytester.copy_example("conftest.py")
    pytester.copy_example("test_mark_xfail.http.json")
    result = pytester.runpytest()
    # Test fails because URL is invalid, mark inheritance needs further work
    result.assert_outcomes(failed=1)
