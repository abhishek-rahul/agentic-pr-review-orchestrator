GOLDEN_CASES = [
    {
        "name": "docs_only_pr",
        "expected": "No security or test findings unless docs affect behavior.",
    },
    {
        "name": "logic_change_missing_test",
        "expected": "Missing test finding should be generated.",
    },
]
