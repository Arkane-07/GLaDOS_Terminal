import time, pygame

class TextInput:
    def __init__(self):
        self.Text = ""
        self.Offset = 0
        self.InsertionPoint = len(self.Text)
        self.CharLength = 42

    def GetInputText(self):
        InputText = self.Text[self.Offset:min(len(self.Text), self.Offset + self.CharLength)]
        
        if time.time() % 1 > 0.5:
            ScaledInsertionPoint = self.InsertionPoint - self.Offset
            # Insert the caret without removing the character under it
            return f"{InputText[:ScaledInsertionPoint]}█{InputText[ScaledInsertionPoint:]}"
        else:
            return InputText

    def Event(self, Event, CanProcess):

        if Event.type == pygame.TEXTINPUT:

            # Add key to text
            self.Text = self.Text[:self.InsertionPoint] + Event.text + self.Text[self.InsertionPoint:]
            self.InsertionPoint = min(len(self.Text), self.InsertionPoint + 1)
            self.SelectionPoint = self.InsertionPoint

            # If going outside of text box increase offset to keep it in
            if len(self.Text) - self.Offset > self.CharLength:
                self.Offset += 1
                    
        elif Event.type == pygame.KEYDOWN:

            # If backspace remove char at end of string
            if Event.key == pygame.K_BACKSPACE:

                if self.InsertionPoint == 0:
                    return False
                
                # Remove one letter
                self.Text = self.Text[:max(0, self.InsertionPoint - 1)] + self.Text[self.InsertionPoint:]
                self.InsertionPoint = max(0, self.InsertionPoint - 1)

                # If going outside of text box decrease offset to keep it in
                if self.Offset > self.InsertionPoint:
                    self.Offset = max(0, self.InsertionPoint)

            # If enter set value
            elif Event.key == pygame.K_RETURN and self.Text != "" and CanProcess:
                self.Offset, self.InsertionPoint = 0, 0
                return True

            # If left arrow move insertion point
            elif Event.key == pygame.K_LEFT:
                self.InsertionPoint = max(0, self.InsertionPoint - 1)

                if self.InsertionPoint < self.Offset:
                    self.Offset = self.InsertionPoint

            # If right arrow move insertion point
            elif Event.key == pygame.K_RIGHT:
                self.InsertionPoint = min(len(self.Text), self.InsertionPoint + 1)

                if self.InsertionPoint > self.Offset + self.CharLength:
                    self.Offset = self.InsertionPoint - self.CharLength

            if Event.mod & pygame.KMOD_CTRL:

                # Check for paste events
                if Event.key == pygame.K_v:

                    # Get raw bytes
                    PastedBytes = pygame.scrap.get(pygame.SCRAP_TEXT)

                    # If returned data and it isnt to long add to text
                    if PastedBytes and len(PastedBytes) < 50:

                        # Decode into string
                        PastedText = PastedBytes.decode("utf-8").strip().strip("\x00")
                        
                        # Add key to text
                        self.Text = self.Text[:self.InsertionPoint] + PastedText + self.Text[self.InsertionPoint:]
                        self.InsertionPoint = min(len(self.Text), self.InsertionPoint + len(PastedText))

                        # If going outside of text box increase offset to keep it in
                        if len(self.Text) - self.Offset > self.CharLength:
                            self.Offset += len(self.Text) - self.Offset - self.CharLength

        return False
