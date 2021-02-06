from typing import Dict, List, Tuple, Union, Optional, Callable, ClassVar
from types import ModuleType
import os, sys, shlex
from pathlib import Path;
import docker, dockerpty
from docker.models.containers import Container
from docker.client import DockerClient
import yaml
import importlib.util, inspect

PathLike = Union[str, os.PathLike] # Type for a string representing a path or a PathLike object.

# Absolute path to the package folder
pkg_dir: Path = Path(__file__).parent.resolve()

class CommandOutput:
    """ Represents the output of a command. """

    exit_code: int
    """ The exit code that the command returned """

    output: str
    """ The printed output of the command """

    # error: str
    # """ Output to std error """

    def __init__(self, exit_code: int, output: str):
        self.exit_code = exit_code
        self.output = output

    def __iter__(self):
        """ Make it iterable so we can unpack it. """
        return iter((self.exit_code, self.output))

class Puzzle:
    """ Represents a single puzzle in the tutorial. """

    question: str
    """ The question to be asked. """

    score: int
    """ The score given on success. Defaults to 1. """

    checker: Callable[..., Union[str,bool]]
    """
    The function that will grade whether the puzzle was completed correctly or not.
    The function can take the following parameters. All parameters are optional, and order does not matter,
    but must have the same name as listed here.

    output: Dict[str, CommandOutput]
        A dict of all commands entered to their outputs, in the order they were entered.
    flag: str
        If the flag parameter is present, an input dialog will be shown to the student when sumbitting a puzzle,
        and their input will be passed to this parameter.
    file_system: FileSystem
        A frozen FileSystem object. Most methods that modify the file system will be disabled.
    """

    solved: bool
    """ Whether the puzzle is solved yet """

    def __init__(self, question: str, checker: Callable[..., Union[str,bool]] , score = 1):
        self.question = question
        self.score = score
        self.checker = checker # type: ignore # MyPy fusses about "Cannot assign to a method"
        self.solved = False

    def get_checker_params(self):
        return inspect.getfullargspec(self.checker).args

class FileSystem:
    """ Handles the docker container and the file system in it. """

    docker_client: DockerClient
    """ The docker daemon. """

    container: Container
    """ The docker container running the tutorial. """

    def __init__(self):
        self.docker_client = docker.from_env()
        self.container = self.docker_client.containers.run('shell-adventure',
            # Keep the container running so we can exec into it.
            # We could run the bash session directly, but then we'd have to hide the terminal until after puzzle generation finishes.
            command = 'sleep infinity',
            tty = True,
            stdin_open = True,
            auto_remove = True,
            detach = True,
        )

    def run_command(self, command: str) -> CommandOutput:
        """ Runs the given command in the tutorial environment. Returns a tuple containing (exit_code, output). """
        exit_code, output = self.container.exec_run(f'/bin/bash -c {shlex.quote(command)}')
        return CommandOutput(exit_code, output.decode())

    def stop(self):
        """ Stops the container. """
        self.container.stop(timeout = 0)

    # TODO Move this into a context manager, or make the container run the bash command directly so that it quits when the session quits.
    def __del__(self):
        if hasattr(self, "container"):
            self.stop()

class Tutorial:
    """ Contains the information for a running tutorial. """

    _puzzle_module_inject: ClassVar[Dict[str, object]] = {
        "Puzzle": Puzzle,
    }
    """ The classes/modules/packages to inject into the puzzle generator modules. """

    config_file: Path
    """ The path to the config file for this tutorial """

    modules: Dict[str, ModuleType]
    """ Puzzle modules mapped to their name. """

    generators: Dict[str, Callable[[FileSystem], Puzzle]]
    """ All available puzzle generator functions mapped to their name. """

    class PuzzleTree:
        """ A tree node so that puzzles can be unlocked after other puzzles are solved. """
        def __init__(self, generator: str, puzzle: Puzzle = None, dependents: List[Puzzle] = None):
            self.generator = generator
            self.puzzle = puzzle
            self.dependents = dependents if dependents else []

    puzzles: List[PuzzleTree]
    """ The tree of puzzles in this tutorial. """

    file_system: FileSystem
    """ The FileSystem object containing the Docker container for the tutorial (when the tutorial is running). """

    def __init__(self, config_file: PathLike):
        self.file_system = None
        self.config_file = Path(config_file)

        # TODO add validation and error checking, document config options
        with open(config_file) as temp:
            config = yaml.safe_load(temp)

            # Load modules
            files = [pkg_dir / "puzzles/default.py"] + config.get('modules', [])
            module_list = [self._get_module(Path(file)) for file in files]
            self.modules = {module.__name__: module for module in module_list}

            # Get puzzle generators from the modules
            self.generators = {}
            for module_name, module in self.modules.items():
                for func_name, func in inspect.getmembers(module, inspect.isfunction):
                    # Exclude imported functions, lambdas, and private functions
                    if func.__module__ == module_name and func_name != "<lambda>" and not func_name.startswith("_"):
                        self.generators[f"{module_name}.{func_name}"] = func

            self.puzzles = []
            for gen in config.get('puzzles', []):
                assert gen in self.generators, f"Unknown puzzle generator {gen}."
                self.puzzles.append(Tutorial.PuzzleTree(gen))

    def _get_module(self, file_path: Path) -> ModuleType:
        """
        Gets a module object from a file path to the module. The file path is relative to the config file.
        Injects some functions and classes into the module's namespace. TODO doc which classes and functions
        """
        if (not file_path.is_absolute()): # Files are relative to the config file
            file_path = self.config_file.parent / file_path

        module_name = file_path.stem # strip ".py"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)

        # Inject names into the modules
        for name, obj in Tutorial._puzzle_module_inject.items():
            setattr(module, name, obj)

        spec.loader.exec_module(module) # type: ignore # MyPy is confused about the types here

        return module

    def solve_puzzle(self, puzzle: Puzzle, flag: str = None) -> Tuple[bool, str]:
        """ Tries to solve the puzzle. Returns (success, feedback) and sets the Puzzle as solved if the checker succeeded. """
        args = {
            # "output": output,
            "flag": flag,
            "file_system": self.file_system,
        }
        # Only pass the args that the checker function has
        checker_params = puzzle.get_checker_params()
        assert set(checker_params).issubset(args.keys()), 'Only paramaters, "flag", "file_system" and "output" are allowed in checker functions.'
        args = {param: args[param] for param in checker_params}

        checker_result = puzzle.checker(**args)

        if checker_result == True:
            puzzle.solved = True
            feedback = "Correct!"
        elif checker_result == False:
            feedback = "Incorrect!"
        elif isinstance(checker_result, str):
            feedback = checker_result
        else:
            raise Exception(f'Checker function for puzzle "{puzzle.question}" returned {type(checker_result).__name__}, bool or str expected.')

        return (puzzle.solved, feedback)

    def run(self):
        """ Starts the tutorial. """
        self.file_system = FileSystem()

        # Generate the puzzles
        for puzzle_tree in self.puzzles:
            puzzle_tree.puzzle = self.generators[puzzle_tree.generator](self.file_system)

    # def attach(self, stdout = None, stderr = None, stdin = None):
    #     """ Attaches a the container to terminal for a bash session. """
    #     dockerpty.exec_command(self.file_system.docker_client.api, self.file_system.container.id, 'bash',
    #         stdout = stdout, stderr = stderr, stdin = stdin
    #     )