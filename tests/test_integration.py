#TODO
import pytest
from shell_adventure.tutorial import Tutorial
from textwrap import dedent
from pathlib import Path
import subprocess
import docker, docker.errors

PUZZLES = dedent("""
    def move():
        file = File("A.txt")
        file.write_text("A")

        def checker():
            return not file.exists() and File("B.txt").exists()

        return Puzzle(
            question = f"Rename A.txt to B.txt",
            checker = checker
        )

    def cd_puzzle():
        dir = File("dir")
        dir.mkdir()

        def checker(cwd):
            return cwd == dir.resolve()

        return Puzzle(
            question = f"cd into dir.",
            checker = checker
        )
""")
CONFIG = """
    modules:
        - puzzles.py
    puzzles:
        - puzzles.move
        - puzzles.cd_puzzle
"""

class TestIntegration:
    def test_basic(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {"puzzles.py": PUZZLES}, CONFIG)
        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            assert docker.from_env().containers.get(tutorial.container.id) != None

            # Assert files were transfered to the volume
            modules = Path(tutorial._volume.name, "modules").glob("*.py")
            assert {m.name for m in modules} == {"puzzles.py"}

            # Puzzles were generated
            for pt in tutorial.puzzles:
                assert pt.puzzle != None

            tutorial.container.exec_run(["mv", "A.txt", "B.txt"])

            move_puzzle = tutorial.puzzles[0].puzzle
            solved, feedback = tutorial.solve_puzzle(move_puzzle)
            assert solved == True
            assert move_puzzle.solved == True
            assert feedback == "Correct!"

        # Make sure the container was removed.
        with pytest.raises(docker.errors.NotFound):
            docker.from_env().containers.get(tutorial.container.id)

    def test_cwd(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {"puzzles.py": PUZZLES}, CONFIG)
        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            # Connect to bash
            bash = subprocess.Popen(["docker", "exec", "-i", "-w", "/home/student/dir", tutorial.container.id, "bash"],
                stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            assert tutorial.connect_to_bash() > 1

            cwd_puzzle = tutorial.puzzles[1].puzzle
            solved, feedback = tutorial.solve_puzzle(cwd_puzzle)
            assert solved == True
            assert cwd_puzzle.solved == True
            assert feedback == "Correct!"

            solved, feedback = tutorial.solve_puzzle(cwd_puzzle)
            assert solved == True
            assert cwd_puzzle.solved == True
            assert feedback == "Correct!"