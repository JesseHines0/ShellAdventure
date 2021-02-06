import pytest
from shell_adventure.tutorial import *

SUPPORTED_COMMANDS = [
    "apt",
    "apt-get",
    "base32",
    "base64",
    "basename",
    "bash",
    "cal",
    "cat",
    "cd", # BASH built-in
    "chgrp",
    "chmod",
    "chown",
    "clear",
    "cmp",
    "cp",
    "date",
    "delgroup",
    "deluser",
    "df",
    "diff3",
    "diff",
    "dir",
    "dirname",
    "dpkg",
    "du",
    "echo",
    "egrep",
    "fgrep",
    "rgrep",
    "env",
    "exit", # BASH built-in
    "false",
    "file",
    "find",
    "flock",
    "fmt",
    "fold",
    "free",
    "groupadd",
    "groupdel",
    "groupmems",
    "groupmod",
    "gzip",
    "gunzip",
    "head",
    "hexdump",
    "hd",
    "history", # BASH built-in
    "hostid",
    "hostname",
    "id",
    "jobs",
    "join",
    "kill",
    "less",
    "link",
    "ln",
    "locale",
    "locate",
    "login", # BASH built-in
    "logout", # BASH built-in
    "look",
    "ls",
    "man",
    "mkdir",
    "mktemp",
    "more",
    "mount",
    "mv",
    "nano",
    "nice",
    "nl",
    "paste",
    "ping",
    "printf",
    "pwd",
    "readlink",
    "realpath",
    "rmdir",
    "rm",
    "sed",
    "size",
    "sleep",
    "sort",
    "split",
    "stat",
    "strip",
    "sudoedit",
    "sudo",
    "su",
    "tail",
    "tar",
    "tee",
    "tempfile",
    "test",
    "timeout",
    "top",
    "touch",
    "tree",
    "true",
    "umount",
    "uname",
    "uniq",
    "unlink",
    "useradd",
    "userdel",
    "usermod",
    "users",
    "wc",
    "wget",
    "whatis",
    "whereis",
    "which",
    "whoami",
    "who",
    "write",
    "zgrep",
    "zipgrep",
    "zipinfo",
    "zip",
    "unzip",
]

class TestContainer:
    @classmethod
    def setup_class(cls):
        cls.fs = FileSystem()

    @classmethod
    def teardown_class(cls):
        cls.fs.stop()

    @pytest.mark.parametrize("command", SUPPORTED_COMMANDS)
    def test_supported_commands(self, command):
        # command -v will check if the given command exists
        exit_code, output = TestContainer.fs.run_command(f"command -v {command}")
        assert exit_code == 0, f'"{command}" not found: "{output}".'

