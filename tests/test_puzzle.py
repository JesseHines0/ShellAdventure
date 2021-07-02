from typing import Callable
import pytest, re
from shell_adventure_shared.support import UnrecognizedParamsError
from shell_adventure_shared.puzzle import Puzzle
import pickle

class TestSupport:
    def test_create_puzzle(self):
        puzzle = Puzzle("Solve this puzzle.", checker = lambda cwd, flag: False)

        assert puzzle.solved == False
        assert puzzle._checker_args == ["cwd", "flag"]

    def test_create_puzzle_invalid_args(self):
        with pytest.raises(UnrecognizedParamsError, match = re.escape("Unrecognized param(s) blah")):
            puzzle = Puzzle("Solve this puzzle.", checker = lambda blah: False)

    def test_create_puzzle_invalid_types(self):
        with pytest.raises(TypeError, match = "Puzzle.checker"):
            puzzle = Puzzle(
                question = "Hey",
                checker = "Not a lambda",
            )

        with pytest.raises(TypeError, match = "Puzzle.question"):
            puzzle = Puzzle(
                question = 1,
                checker = lambda: False,
            )

    def test_pickle_puzzle(self):
        old_puzzle = Puzzle("Solve this puzzle.", checker = lambda flag: False, score = 2)
        old_puzzle.solved = True

        data = pickle.dumps(old_puzzle)
        new_puzzle: Puzzle = pickle.loads(data)

        assert old_puzzle.question == new_puzzle.question
        assert old_puzzle.score == new_puzzle.score
        assert old_puzzle.solved == new_puzzle.solved
        assert old_puzzle.id == new_puzzle.id
        assert old_puzzle._checker_args == ["flag"]

        assert isinstance(old_puzzle.checker, Callable) # Doesn't affect original

        # Leaves the lambda as bytes for now, will load it if we use the puzzle
        assert isinstance(new_puzzle.checker, bytes)
        new_puzzle.extract()
        assert isinstance(new_puzzle.checker, Callable)

    def test_pickle_puzzle_already_pickled(self):
        old_puzzle = Puzzle("Solve this puzzle.", checker = lambda flag: False)

        new_puzzle: Puzzle = pickle.loads(pickle.dumps(old_puzzle))
        new_puzzle2: Puzzle = pickle.loads(pickle.dumps(new_puzzle))
        # Pickling twice does not double pickle the lambda
        new_puzzle2.extract()
        assert isinstance(new_puzzle2.checker, Callable)

        # Calling extract twice does nothing
        new_puzzle2.extract()
        assert isinstance(new_puzzle2.checker, Callable)