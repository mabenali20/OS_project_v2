import fs_constants
import os


class Shell:
    # Invalid characters for FAT file names
    INVALID_CHARS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']

    def __init__(self, file_system):
        self.fs = file_system
        # Stack to keep track of directory clusters
        self.dir_cluster_history = [fs_constants.ROOT_DIR_CLUSTER]
        # Path history for display (Linux Style)
        self.path_history = ["/"]

    def run(self):
        print("Welcome to MiniFAT Shell! Type 'help' for commands.")

        while True:
            # 1. Build Prompt: H:/DOCS>
            current_path = "/".join(self.path_history).replace("//", "/")
            if current_path != "/" and current_path.startswith("/"):
                current_path = current_path[1:]  # Cosmetic fix for subdirs

            prompt = f"H:{current_path}> "

            try:
                user_input = input(prompt).strip()
            except EOFError:
                break

            if not user_input:
                continue

            # 2. Parse Input (Handle echo quotes)
            if user_input.lower().startswith("echo"):
                parts = self._parse_echo(user_input)
            else:
                parts = user_input.split()

            command = parts[0].lower()
            args = parts[1:]

            # 3. Dispatch Command
            if command == "exit" or command == "quit":
                break
            elif command == "help":
                self._cmd_help()
            elif command == "cls" or command == "clear":
                print("\n" * 50)
            elif command == "ls" or command == "dir":
                self._cmd_ls(args)
            elif command == "cd":
                self._cmd_cd(args)
            elif command == "mkdir" or command == "md":
                self._cmd_mkdir(args)
            elif command == "rmdir" or command == "rd":
                self._cmd_rmdir(args)
            elif command == "touch":
                self._cmd_touch(args)
            elif command == "cat" or command == "type":
                self._cmd_cat(args)
            elif command == "rm" or command == "del":
                self._cmd_rm(args)
            elif command == "cp" or command == "copy":
                self._cmd_cp(args)
            elif command == "mv" or command == "move":
                self._cmd_mv(args)
            elif command == "import":
                self._cmd_import(args)
            elif command == "export":
                self._cmd_export(args)
            elif command == "echo":
                self._cmd_echo(args)
            else:
                print(f"Unknown command: '{command}'")

    def _parse_echo(self, input_str):
        try:
            first_quote = input_str.find('"')
            last_quote = input_str.rfind('"')
            if first_quote != -1 and last_quote != -1 and first_quote != last_quote:
                cmd = "echo"
                text = input_str[first_quote + 1: last_quote]
                rest = input_str[last_quote + 1:].strip().split()
                return [cmd, text] + rest
        except:
            pass
        return input_str.split()

    def _is_valid_name(self, name):
        """Check if filename/dirname contains invalid characters."""
        for char in self.INVALID_CHARS:
            if char in name:
                print(f"Error: Name cannot contain '{char}' character.")
                return False
        if len(name) == 0:
            print("Error: Name cannot be empty.")
            return False
        return True

    # --- Command Implementations ---

    def _cmd_help(self):
        print("\nAvailable Commands:")
        print("  ls [dir]        : List files")
        print("  cd <dir>        : Change directory (.. to go back)")
        print("  mkdir <name>    : Create directory")
        print("  rmdir <name>    : Remove empty directory")
        print("  touch <name>    : Create empty file")
        print("  cat <name>      : Display file content")
        print("  rm <name>       : Delete file")
        print("  cp <src> <dst>  : Copy file")
        print("  mv <src> <dst>  : Move/Rename file")
        print("  import <path>   : Import file from computer")
        print("  export <name>   : Export file to computer")
        print("  echo <text>     : Write text to file (-append supported)")
        print("  clear           : Clear screen")
        print("  exit            : Exit shell")
        print("")

    def _cmd_ls(self, args):
        # Back to the Clean/Simple Table Style
        target_cluster = self.fs.current_dir

        if args:
            dir_name = args[0]
            # Updated: using fs.dir instead of dir_manager
            entry = self.fs.dir.find_entry(self.fs.current_dir, dir_name)

            # Updated: using ATTR_DIR instead of ATTR_DIRECTORY
            if entry and entry.attr == fs_constants.ATTR_DIR:
                target_cluster = entry.first_cluster
            else:
                print(f"Error: Directory '{dir_name}' not found.")
                return

        self.fs.list_directory(target_cluster)

    def _cmd_cd(self, args):
        if not args:
            # Just print current path
            current_path = "/".join(self.path_history).replace("//", "/")
            if current_path != "/" and current_path.startswith("/"): current_path = current_path[1:]
            print(f"Current Directory: {current_path}")
            return

        target = args[0]

        if target == "..":
            if len(self.dir_cluster_history) > 1:
                self.dir_cluster_history.pop()
                self.path_history.pop()
                prev_cluster = self.dir_cluster_history[-1]
                self.fs.current_dir = prev_cluster
            return

        # Updated: using fs.dir and ATTR_DIR
        entry = self.fs.dir.find_entry(self.fs.current_dir, target)
        if entry:
            if entry.attr == fs_constants.ATTR_DIR:
                self.dir_cluster_history.append(entry.first_cluster)
                self.path_history.append(target.upper())
                self.fs.current_dir = entry.first_cluster
            else:
                print(f"Error: '{target}' is not a directory.")
        else:
            print(f"Error: Directory '{target}' not found.")

    def _cmd_mkdir(self, args):
        if not args: print("Usage: mkdir <dirname>"); return
        if not self._is_valid_name(args[0]): return
        self.fs.create_directory(args[0])

    def _cmd_rmdir(self, args):
        if not args: print("Usage: rmdir <dirname>"); return
        self.fs.remove_directory(args[0])

    def _cmd_touch(self, args):
        if not args: print("Usage: touch <filename>"); return
        if not self._is_valid_name(args[0]): return
        self.fs.create_file(args[0])

    def _cmd_cat(self, args):
        if not args: print("Usage: cat <filename>"); return
        content = self.fs.read_file(args[0])
        if content is not None:
            print(content.decode('utf-8', errors='replace'))

    def _cmd_rm(self, args):
        if not args: print("Usage: rm <filename>"); return
        self.fs.delete_file(args[0])

    def _cmd_cp(self, args):
        if len(args) < 2: print("Usage: cp <src> <dst>"); return
        self.fs.copy_file(args[0], args[1])

    def _cmd_mv(self, args):
        if len(args) < 2: print("Usage: mv <src> <dst>"); return
        self.fs.move_file(args[0], args[1])

    def _cmd_import(self, args):
        if len(args) < 1: print("Usage: import <host_path> [virtual_name]"); return
        host_path = args[0]
        virtual_name = args[1] if len(args) > 1 else os.path.basename(host_path)
        self.fs.import_file_from_host(host_path, virtual_name)

    def _cmd_export(self, args):
        if len(args) < 2: print("Usage: export <virtual_name> <host_path>"); return
        self.fs.export_file_to_host(args[0], args[1])

    def _cmd_echo(self, args):
        if len(args) < 2: print("Usage: echo \"text\" <filename> [-append]"); return
        text = args[0]
        filename = args[1]
        is_append = len(args) > 2 and args[2].lower() == "-append"

        # Check if file exists, if not create it first
        entry = self.fs.dir.find_entry(self.fs.current_dir, filename)
        if not entry:
            if not self._is_valid_name(filename): return
            self.fs.create_file(filename)

        if is_append:
            self.fs.append_to_file(filename, (text + '\n').encode('utf-8'))
        else:
            self.fs.write_file(filename, (text + '\n').encode('utf-8'))