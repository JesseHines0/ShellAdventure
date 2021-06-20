import pytest
from shell_adventure.tutorial import Tutorial
from shell_adventure import docker_helper
from textwrap import dedent
from .helpers import *

class TestUndo:
    def test_undo_disabled(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.puz:
                undo: no
            """,
            "puzzles.py": dedent("""
                from shell_adventure_docker import *

                def puz(home):
                    src = home / "A.txt"
                    dst = home / "B.txt"

                    def checker():
                        return not src.exists() and dst.exists()

                    return Puzzle(
                        question = f"{src} -> {dst}",
                        checker = checker
                    )
            """),
        })

        # If user isn't root, trying to add file to root will fail
        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            assert tutorial.undo_enabled == False
            tutorial.commit()
            assert len(tutorial.undo_list) == 0 # commit is ignored if undo_enabled is false
            assert tutorial.can_undo() == False
            tutorial.undo(); tutorial.restart() # Undo, restart should just do nothing
            assert tutorial.can_undo() == False

    def test_undo_basic(self, tmp_path):
        # Get the number of images before we made the tutorial
        docker_client = docker_helper.client
        images_before = docker_client.images.list(all = True)
        containers_before = docker_client.containers.list(all = True)

        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
                    - puzzles.move2
            """,
            "puzzles.py": SIMPLE_PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit for the initial state.
    
            run_command(tutorial, "touch temp\n")
            assert file_exists(tutorial, "temp")
            assert len(tutorial.undo_list) == 2
            tutorial.undo()
            assert len(tutorial.undo_list) == 1
            assert not file_exists(tutorial, "temp")

            run_command(tutorial, "touch B\n")
            run_command(tutorial, "touch C\n")
            assert len(tutorial.undo_list) == 3
            tutorial.undo()
            assert not file_exists(tutorial, "C")
            assert len(tutorial.undo_list) == 2
            run_command(tutorial, "touch D\n")
            assert len(tutorial.undo_list) == 3

            images_during = docker_client.images.list(all = True)
            assert len(images_before) < len(images_during)

        images_after = docker_client.images.list(all = True)
        assert len(images_before) == len(images_after)
        containers_after = docker_client.containers.list(all = True)
        assert len(containers_before) == len(containers_after)

    def test_undo_with_puzzle_solving(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
                    - puzzles.move2
            """,
            "puzzles.py": SIMPLE_PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit before first command

            puz1 = tutorial.get_all_puzzles()[0]
            puz2 = tutorial.get_all_puzzles()[1]

            run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(puz1) == (True, "Correct!")
            assert (puz1.solved, puz2.solved) == (True, False)

            tutorial.undo()
            assert file_exists(tutorial, "A.txt") and not file_exists(tutorial, "B.txt")
            assert (puz1.solved, puz2.solved) == (False, False) # Puzzle is no longer solved

            run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(puz1) == (True, "Correct!") # Re-solve puzzle

            run_command(tutorial, "mv C.txt D.txt\n")
            assert tutorial.solve_puzzle(puz2) == (True, "Correct!")

            assert tutorial.is_finished()

    def test_undo_empty_stack(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
                    - puzzles.move2
            """,
            "puzzles.py": SIMPLE_PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit before first command

            assert len(tutorial.undo_list) == 1
            assert not tutorial.can_undo()
            tutorial.undo() # Should do nothing since we have nothing to undo
            assert len(tutorial.undo_list) == 1

            run_command(tutorial, "touch A\n")
            run_command(tutorial, "touch B\n")
            run_command(tutorial, "touch C\n")
            run_command(tutorial, "touch D\n")
            assert len(tutorial.undo_list) == 5
            assert tutorial.can_undo()

            tutorial.undo()
            tutorial.undo()
            tutorial.undo()
            tutorial.undo()
            assert len(tutorial.undo_list) == 1
            assert not tutorial.can_undo()
            tutorial.undo() # Hit the bottom of the undo stack, nothing should happen (only current state in the stack)
            assert len(tutorial.undo_list) == 1

    def test_undo_sets_tutorial(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.set_totrial:
            """,
            "puzzles.py": dedent("""
                import shell_adventure_docker
                from shell_adventure_docker import *

                def set_totrial():
                    return Puzzle(
                        question = f"Home",
                        checker = lambda: shell_adventure_docker._tutorial != None,
                    )
            """),
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit before first command
            puz = tutorial.get_all_puzzles()[0]

            run_command(tutorial, "touch A\n")
            assert tutorial.solve_puzzle(puz) == (True, "Correct!")
            tutorial.undo()
            assert tutorial.solve_puzzle(puz) == (True, "Correct!") # Still has _tutorial set

    def test_redo(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.move:
                    - puzzles.move2
            """,
            "puzzles.py": SIMPLE_PUZZLES,
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            tutorial.commit() # Bash PROMPT_COMMAND would normally run a commit before first command

            puz1 = tutorial.get_all_puzzles()[0]
            puz2 = tutorial.get_all_puzzles()[1]

            run_command(tutorial, "mv A.txt B.txt\n")
            assert tutorial.solve_puzzle(puz1) == (True, "Correct!")

            run_command(tutorial, "mv C.txt D.txt\n")
            assert tutorial.solve_puzzle(puz2) == (True, "Correct!")

            tutorial.restart()
            assert len(tutorial.undo_list) == 1
            assert (puz1.solved, puz2.solved) == (False, False)
            assert file_exists(tutorial, "A.txt")
            assert file_exists(tutorial, "C.txt")

    def test_undo_pickle_failure(self, tmp_path):
        tutorial = create_tutorial(tmp_path, {
            "config.yaml": """
                modules:
                    - puzzles.py
                puzzles:
                    - puzzles.unpicklable
                undo: true
            """,
            "puzzles.py": dedent("""
                from shell_adventure_docker import *

                def unpicklable():
                    gen = (i for i in range(1, 10))
                    return Puzzle(
                        question = f"Can't pickle generators",
                        checker = lambda: gen == None,
                    )
            """)  
        })

        with tutorial: # start context manager, calls Tutorial.start() and Tutorial.stop()
            puz = tutorial.get_all_puzzles()[0]
            assert puz.checker == None

            assert tutorial.undo_enabled == False
            assert len(tutorial.undo_list) == 0

            tutorial.commit()
            assert len(tutorial.undo_list) == 0 # Commit does nothing

