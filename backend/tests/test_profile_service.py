from app.services.profile_service import calculate_level, calculate_rank_title


def test_calculate_level_minimum_level():
    """
    Test that a student always starts at minimum level 1.

    Even if the student has 0 XP, the platform should show them as level 1,
    not level 0.

    Expected result:
    - 0 XP should return level 1.
    """
    assert calculate_level(0) == 1


def test_calculate_level_increases_every_100_xp():
    """
    Test that student level increases every 100 XP.

    The current level rule is:
    - every 100 XP gives 1 additional level
    - level starts at 1

    Expected result:
    - 0 XP = level 1
    - 99 XP = level 1
    - 100 XP = level 2
    - 250 XP = level 3
    """
    assert calculate_level(0) == 1
    assert calculate_level(99) == 1
    assert calculate_level(100) == 2
    assert calculate_level(250) == 3


def test_calculate_rank_title_beginner():
    """
    Test that low-level students get the Beginner rank title.

    Expected result:
    - Levels below 5 should return "Beginner".
    """
    assert calculate_rank_title(1) == "Beginner"
    assert calculate_rank_title(4) == "Beginner"


def test_calculate_rank_title_active_learner():
    """
    Test that students from level 5 to 9 get Active Learner.

    Expected result:
    - Level 5 should return "Active Learner".
    - Level 9 should return "Active Learner".
    """
    assert calculate_rank_title(5) == "Active Learner"
    assert calculate_rank_title(9) == "Active Learner"


def test_calculate_rank_title_higher_levels():
    """
    Test that higher student levels receive the correct rank titles.

    Expected result:
    - Level 10 should return "Concept Champion".
    - Level 15 should return "Olympiad Master".
    - Level 20 should return "AI Scholar".
    """
    assert calculate_rank_title(10) == "Concept Champion"
    assert calculate_rank_title(15) == "Olympiad Master"
    assert calculate_rank_title(20) == "AI Scholar"