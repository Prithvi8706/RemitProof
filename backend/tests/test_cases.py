from app.models import CandidateBundle


def test_spike_contains_exactly_the_ten_required_cases(spike_cases):
    assert list(spike_cases) == [f"SPIKE_{number:02d}" for number in range(1, 11)]


def test_ground_truth_is_separate_from_model_input(spike_cases):
    for case in spike_cases.values():
        CandidateBundle.model_validate(case["input"])
        assert "ground_truth" not in case["input"]
        assert "should_resolve" not in case["input"]
