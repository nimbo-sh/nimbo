import enum

import click


class HelpSection(enum.Enum):
    INSTANCE = "Instance"
    STORAGE = "Storage"
    UTILS = "Utilities"
    ADMIN = "Admin Utilities"


class NimboCommand(click.Command):
    """ click.Command extension for command grouping """

    def __init__(self, *args, **kwargs):
        self.help_section: HelpSection = kwargs.pop("help_section", None)
        super().__init__(*args, **kwargs)


class NimboGroup(click.Group):
    """ click.Group extension for command grouping """

    def list_commands(self, ctx):
        # Avoid command sorting
        return self.commands.keys()

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        # Display commands in sections

        section_to_commands = {section.value: [] for section in HelpSection}

        max_cmd_len = 0
        for sub_cmd in self.list_commands(ctx):
            max_cmd_len = max(max_cmd_len, len(sub_cmd))
            cmd = self.get_command(ctx, sub_cmd)

            if hasattr(cmd, "help_section") and cmd.help_section:
                section_to_commands[cmd.help_section.value].append((sub_cmd, cmd))

        # allow for 3 times the default spacing
        limit = formatter.width - 6 - max_cmd_len

        for section, commands in section_to_commands.items():
            if len(commands):
                rows = []
                max_section_cmd_len = 0

                for sub_cmd, cmd in commands:
                    max_section_cmd_len = max(max_section_cmd_len, len(sub_cmd))

                    help_text = cmd.get_short_help_str(limit)
                    rows.append((sub_cmd, help_text))

                if rows:
                    col_spacing = max_cmd_len - max_section_cmd_len + 2

                    with formatter.section(section):
                        formatter.write_dl(rows, col_spacing=col_spacing)
