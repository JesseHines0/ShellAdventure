from typing import *
import pytest
from shell_adventure.tutorial import Tutorial
from textwrap import dedent;
from pathlib import PurePosixPath
from yamale.yamale_error import YamaleError
import re

SIMPLE_PUZZLES = dedent("""
    from shell_adventure_docker import *

    def move():
        file = File("A.txt")
        file.write_text("A")

        def checker():
            return not file.exists() and File("B.txt").exists()

        return Puzzle(
            question = f"Rename A.txt to B.txt",
            checker = checker
        )
""")
SIMPLE_TUTORIAL = """
    modules:
        - mypuzzles.py
    puzzles:
        - mypuzzles.move
"""

class TestTutorial:
    def test_simple_tutorial(self, tmp_path):
        # Create the files
        tutorial = pytest.helpers.create_tutorial(tmp_path, {"config.yaml": SIMPLE_TUTORIAL, "mypuzzles.py": SIMPLE_PUZZLES})
        tutorial = Tutorial(f"{tmp_path / 'config.yaml'}") # Strings should also work for path
        assert tutorial.config_file == tmp_path / "config.yaml"
        assert str(tutorial.name_dictionary).endswith("resources/name_dictionary.txt")

    def test_creation(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": f"""
                image: my-custom-image:latest
                home: /home/user
                user: user
                resources:
                    my_resource.txt: file1.txt
                setup_scripts:
                    - setup.py
                    - setup.sh 
                modules:
                    - puzzle1.py # Relative path
                    - {tmp_path / "puzzle2.py"} # Absolute path
                puzzles:
                    - puzzle1.move
                    - puzzle2.move
                name_dictionary: "my_dictionary.txt"
                content_sources:
                    - content.txt
            """,
            "puzzle1.py": SIMPLE_PUZZLES,
            "puzzle2.py": SIMPLE_PUZZLES,
            "my_dictionary.txt": "a\nb\nc\n",
            "content.txt": "STUFF\n\nSTUFF\n\nMORE STUFF\n",
            "setup.py": "File('A.txt').create()",
            "setup.sh": "touch B.txt",
            "my_resource.txt": "1",
        })
        assert tutorial.data_dir == tmp_path
        assert tutorial.image == "my-custom-image:latest"
        assert tutorial.home == PurePosixPath("/home/user")
        assert tutorial.user == "user"
        assert tutorial.name_dictionary == tmp_path / "my_dictionary.txt"
        assert tutorial.content_sources == [tmp_path / "content.txt"]

        assert tutorial.resources == {tmp_path / "my_resource.txt": PurePosixPath("file1.txt")}
        assert [s for s in tutorial.setup_scripts] == [tmp_path / "setup.py", tmp_path / "setup.sh"]
        assert [m for m in tutorial.module_paths] == [tmp_path / "puzzle1.py", tmp_path / "puzzle2.py"]
        assert [pt.generator for pt in tutorial.puzzles] == ["puzzle1.move", "puzzle2.move"]

    def test_nested_puzzles(self, tmp_path):
        tutorial: Tutorial = pytest.helpers.create_tutorial(tmp_path, {
            "config.yaml": f"""
                modules:
                    - puzzle1.py
                    - puzzle2.py
                    - puzzle3.py
                puzzles:
                    - puzzle1.move:
                        - puzzle2.move:
                            - puzzle1.move
                    - puzzle2.move
                    - puzzle3.move:
                name_dictionary: "my_dictionary.txt"
                content_sources:
                    - content.txt
            """,
            "puzzle1.py": SIMPLE_PUZZLES, "puzzle2.py": SIMPLE_PUZZLES, "puzzle3.py": SIMPLE_PUZZLES,
        })
        # First level
        assert [pt.generator for pt in tutorial.puzzles] == ["puzzle1.move", "puzzle2.move", "puzzle3.move"]

        # Second Level
        assert [pt.generator for pt in tutorial.puzzles[0].dependents] == ["puzzle2.move"]

        # Third Level
        assert [pt.generator for pt in tutorial.puzzles[0].dependents[0].dependents] == ["puzzle1.move"]

    def test_missing_files(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            tutorial = pytest.helpers.create_tutorial(tmp_path, {"config.yaml": SIMPLE_TUTORIAL}) # Don't make any puzzle files
        with pytest.raises(FileNotFoundError):
            tutorial = Tutorial(tmp_path / "not_a_config_file.yaml")

    def test_duplicate_module_names(self, tmp_path):
        with pytest.raises(Exception, match='Multiple puzzle modules with name "puzzle1.py" found'):
            tutorial = pytest.helpers.create_tutorial(tmp_path, {
                "config.yaml": """
                    modules:
                        - puzzle1.py
                        - puzzle1.py
                    puzzles:
                        - puzzle1.move
                """,
                "puzzle1.py": SIMPLE_PUZZLES,
            }) 

    def test_validation_error(self, tmp_path):
        try:
            tutorial = pytest.helpers.create_tutorial(tmp_path, {
                "config.yaml": """
                    undo: 20
                    puzzles:
                        puzzles.move:
                    resources:
                        1: resource
                """,
                "puzzles.py": SIMPLE_PUZZLES,
            })
            assert False, "Didn't fail validation"
        except YamaleError as error:
            assert re.search("undo: .* is not a bool.", error.message)
            assert re.search("modules: Required field missing", error.message)
            assert re.search("puzzles: .* is not a list.", error.message)
            assert re.search("resources: Key error", error.message)

    def test_config(self, tmp_path):
        with pytest.raises(YamaleError):
            tutorial = pytest.helpers.create_tutorial(tmp_path, {"config.yaml": "", "mypuzzles.py": SIMPLE_PUZZLES})
