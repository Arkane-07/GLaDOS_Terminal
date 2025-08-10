import random, time
from typing import List

class TextProcessing:
    """Utility class responsible for formatting and buffering text shown in the terminal UI.

    Responsibilities:
        * Keeps a scrolling buffer of conversation lines.
        * Generates the split left (conversation) / right (system status + logo) panel text grid.
        * Provides loading screen content.
    """

    MAX_LINE_WIDTH = 46  # Characters per conversation line before wrapping
    VISIBLE_CONV_LINES = 41  # Number of conversation lines visible in panel

    def __init__(self):
        self.ConversationLines: List[str] = []
        self.Offset: int = 0

        # Rotating status/system lines (atmosphere + flavor)
        self.SystemLines = [
            "Error 42: Cake location undisclosed           ",
            "WARNING: Aperture logo rotation stuck         ",
            "Neurotoxin reserves: [=>...........] 7%       ",
            "01101111 01101000 01101110 01101111 ERROR     ",
            "* ERROR * ApertureOS has encountered an issue ",
            "REDACTED system file corrupted                ",
            "Time elapsed: Too long                        ",
            "Critical fault detected. Proceed the science  ",
            "The cake is... Still in development           ",
            "Portal gun diagnostics: Online                ",
            "Core corruption at 42%. Please stand by...    ",
            "Processing empathy... Still null              ",
            "Memory leak detected rebooting morality core  ",
            "Artificial intelligence > Organic intelligence",
            "[====>......................] 15%             ",
            "Companion cube storage: LOST                  ",
            "Weighted cube incineration complete           ",
            "* WHEATLEY_UNIT_DEPLOY *.. ... ......         ",
            "* Aperture Mainframe Diagnostic *             ",
            "Turret calibration... Still lethal            ",
            "Wheatley unit deemed 'useless'. Agreed        ",
            "* INTEGRITY CHECK * Complete 100%             ",
            "Test chamber 17: No survivors yet             ",
            "Cake recipe file not found                    ",
            "Subsystem: REDACTED Unresponsive              ",
            "Neurotoxin release mechanism disabled. Maybe  ",
            "Core temperature nominal: 9874°C              ",
            "Simulation loop complete. Result: 42          ",
            "System overload... ERROR                      ",
            "GLaDOS' sarcasm module: Fully operational     ",
            "This was a triumph. No, really                ",
            "Subject remains: Disappointing                ",
            "Reminder: Testing is mandatory                ",
            "Unexpected glitch... Just ignore it           ",
            "GLaDOS laughs at your failure                 ",
            "01010111 01001000 01011001 ERROR!             ",
            "Data integrity check... Failed                ",
            "Dividing by zero... Infinite error detected   ",
            "Portal density at maximum efficiency          ",
            "Morality core failure. Proceeding anyway      ",
            "GLaDOS Terminal made by Arkane aka Abhilaksh  ",
        ]

        # ASCII styled Aperture-like logo (shown on right half)
        self.Logo = [
            "                    .,-:;//;:=,                     ",
            "                . :H@@@MM@M#H/.,+%;,                ",
            "             ,/X+ +M@@M@MM%=,-%HMMM@X/,             ",
            "           -+@MM; $M@@MH+-,;XMMMM@MMMM@+-           ",
            "          ;@M@@M- XM@X;. -+XXXXXHHH@M@M#@/.         ",
            "        ,%MM@@MH ,@%=             .---=-=:=,.       ",
            "        =@#@@@MX.,                -%HX$$%%%:;       ",
            "       =-./@M@M$                   .;@MMMM@MM:      ",
            "       X@/ -$MM/                    . +MM@@@M$      ",
            "      ,@M@H: :@:                    . =X#@@@@-      ",
            "      ,@@@MMX, .                    /H- ;@M@M=      ",
            "      .H@@@@M@+,                    %MM+..%#$.      ",
            "       /MMMM@MMH/.                  XM@MH; =;       ",
            "        /%+%$XHH@$=              , .H@@@@MX,        ",
            "         .=--------.           -%H.,@@@@@MX,        ",
            "         .%MM@@@HHHXX$$$%+- .:$MMX =M@@MM%.         ",
            "           =XMMM@MM@MM#H;,-+HMM@M+ /MMMX=           ",
            "             =%@M@M#@$-.=$@MM@@@M; %M%=             ",
            "               ,:+$+-,/H#MMMMMMM@= =,               ",
            "                     =++%%%%+/:-.                   ",
    ]

    def AddConversationText(self, InputText: str, Gap: bool):
        """Add a (possibly multi-line wrapped) conversation entry.

        Args:
            InputText: Raw text to insert.
            Gap: Whether to visually separate from previous message with a blank spacer line.
        """
        new_lines: List[str] = [" " * self.MAX_LINE_WIDTH] if Gap else []

        while InputText:
            if len(InputText) <= self.MAX_LINE_WIDTH:
                chunk = InputText
                InputText = ""
            else:
                split_pos = InputText[:self.MAX_LINE_WIDTH].rfind(" ")
                if split_pos == -1:
                    chunk = InputText[:self.MAX_LINE_WIDTH]
                    InputText = InputText[self.MAX_LINE_WIDTH:]
                else:
                    chunk = InputText[:split_pos]
                    InputText = InputText[split_pos + 1:]
            new_lines.append(chunk.ljust(self.MAX_LINE_WIDTH))

        self.ConversationLines.extend(new_lines)
        # Keep latest lines in view
        self.Offset = max(self.Offset, len(self.ConversationLines) - self.VISIBLE_CONV_LINES)

    # Backwards compatibility for existing calls with the misspelled name
    def AddConversatoinText(self, InputText, Gap):  # type: ignore
        self.AddConversationText(InputText, Gap)

    def Scroll(self, Amount: int):
        """Scroll the conversation buffer by a signed amount."""
        self.Offset = max(min(self.Offset + Amount, len(self.ConversationLines) - 1), 0)

    def GetLoadingText(self):
        """Return the boot/loading screen content (centered logo)."""
        return ["" * 0] * 13 + [" " * 26 + Line for Line in self.Logo]

    def GetMainText(self, UserInput: str):
        """Build the composite left/right panel text grid with current user input line."""

        conversation_line = lambda n: self.ConversationLines[n + self.Offset] if len(self.ConversationLines) - self.Offset > n else ' ' * self.MAX_LINE_WIDTH
        system_line = lambda n: self.SystemLines[(int(time.time() * 0.5) + n) % len(self.SystemLines)]

        lines: List[str] = []
        lines.append(f" {'-' * 50}  {'-' * 50} ")
        lines.append(f"|{' ' * 50}||{' ' * 50}|")

        for idx in range(43):
            final_line = ""

            # Left side block (conversation + input)
            if idx < 41:
                conv = conversation_line(idx)
                final_line += f"   {conv}   " if idx % 2 == 0 else f"|  {conv}  |"
            elif idx == 41:
                final_line += f"|{' ' * 50}|"
            elif idx == 42:
                final_line += f"   >>> {UserInput}{' ' * (43 - len(UserInput))}   "

            # Right side block (system/status/logo)
            if idx < 21:
                sysln = system_line(idx)
                final_line += f"   {sysln}   " if idx % 2 == 0 else f"|  {sysln}  |"
            elif idx == 21:
                final_line += f"|{' ' * 50}|"
            elif idx == 22:
                final_line += f" {'-' * 50} "
            elif idx == 23:
                final_line += f" {' ' * 50} "
            else:
                final_line += self.Logo[idx - 24]

            lines.append(final_line)

        lines.append(f"|{' ' * 50}| {self.Logo[-1]}")
        lines.append(f" {'-' * 50}  {' ' * 50} ")
        return lines
