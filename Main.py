# GLaDOS-Terminal, Author Arkane

print("Setting up, please wait.\n")

import pygame, sys, math, os, time, random, json
from pygame.locals import *

import moderngl as mgl
from array import array

import numpy as np

from Scripts.TextInput import TextInput
from Scripts.TextProcessing import TextProcessing
from Scripts.LargeLanguageModel import LargeLanguageModel, GetAvailableModels, FormatModelSize
from Scripts.TextToSpeech import TextToSpeech

# Helper to resolve bundled resources when packaged (PyInstaller)
def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# Load in settings
with open(resource_path("Settings.json"), "r") as File:
    Settings = json.loads(File.read())

# Get available models dynamically
print("Fetching available models...")
AVAILABLE_MODELS = GetAvailableModels()
MODEL_NAMES = [model['name'] for model in AVAILABLE_MODELS]

"""Runtime state for model selection and TTS"""
# Current model index (what's active) and selection index (what's highlighted in UI)
current_model_index = 0
try:
    current_model_index = MODEL_NAMES.index(Settings.get("ModelName", MODEL_NAMES[0]))
except ValueError:
    current_model_index = 0

selected_model_index = current_model_index

# TTS toggle (press F5 to toggle on/off)
tts_enabled = False

# Model selector GUI state (closed by default; open with ` or ~)
show_model_selector = False
model_selector_alpha = 0.0

print(f"Found {len(AVAILABLE_MODELS)} models:")
for i, model in enumerate(AVAILABLE_MODELS):
    print(f"  {i+1}. {model['name']} ({FormatModelSize(model['size'])})")

print(f"TTS is {'enabled' if tts_enabled else 'disabled'} (press F5 to toggle)")
print("Use ` or ~ to open the model selector in chat. Up/Down = navigate, Enter = select, Esc = cancel.")

# Do not preload LLM; user will choose model from selector
GeneratorLLM = None
GeneratorTTS = TextToSpeech(
    Settings["VoiceModels"]["ModelNameHifigan"], Settings["VoiceModels"]["ModelNameTacotron2"],
    Settings["VoiceModels"]["ModelIDHifigan"], Settings["VoiceModels"]["ModelIDTacotron2"], 0.75
)

## Pygame Setup Bits ###############################################################################

pygame.init()
pygame.display.set_caption("GLaDOS-Terminal")

Font = pygame.font.Font(resource_path("Fonts/1977-Apple2.ttf"), 12)
FontSize, Color = [9, 16], [230, 125, 15]

Resolution = (104 * FontSize[0], 47 * FontSize[1])
Screen = pygame.display.set_mode(Resolution, flags=pygame.OPENGL | pygame.DOUBLEBUF)
Display = pygame.Surface(Resolution).convert_alpha()

# Set window icon
IconImage = pygame.transform.scale(pygame.image.load(resource_path("Images/Icon.png")), (360, 360)).convert_alpha()
pygame.display.set_icon(IconImage)

Clock, LastTime = pygame.time.Clock(), time.time()
FPS, Time = 30, 0

HeldKeys = {}

# Init audio stuff
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.mixer.set_num_channels(64)

# Load in all sounds
ComputerBootSound = pygame.mixer.Sound(resource_path("Sounds/ComputerBoot.mp3"))
KeyboardPressedSound = pygame.mixer.Sound(resource_path("Sounds/KeyboardPressed.mp3"))

ComputerBootSound.set_volume(Settings["SoundEffectVolume"])
KeyboardPressedSound.set_volume(Settings["SoundEffectVolume"])

# init scrap for clipboard handling
pygame.scrap.init()
pygame.scrap.set_mode(pygame.SCRAP_CLIPBOARD)

# Allow keys to repeat and allow for text inputs
pygame.key.set_repeat(500, 33)
pygame.key.start_text_input()

## OpenGL Setup Bits ###############################################################################

Context = mgl.create_context()

QuadBuffer = Context.buffer(data=array("f", [
    # Position (x, y), uv coords (x, y)
    -1.0, 1.0, 0.0, 1.0,  # Topleft
    1.0, 1.0, 1.0, 1.0,   # Topright
    -1.0, -1.0, 0.0, 0.0, # Bottomleft
    1.0, -1.0, 1.0, 0.0   # Bottomright
]))

with open(resource_path("Shaders/Vertex.glsl")) as file:
    VertexShader = file.read()

with open(resource_path("Shaders/Fragment.glsl")) as file:
    FragmentShader = file.read()

Program = Context.program(vertex_shader=VertexShader, fragment_shader=FragmentShader)
RenderObject = Context.vertex_array(Program, [(QuadBuffer, "2f 2f", "vert", "texcoord")])

## Functions and classes ###########################################################################

def SurfaceToTexture(Surface):
    Texure = Context.texture(Surface.get_size(), 4) # Innit texture
    Texure.filter = (mgl.NEAREST, mgl.NEAREST) # Set properties
    Texure.repeat_x, Texure.repeat_y = False, False # Make texture not repeat
    Texure.swizzle = "BGRA" # Set format
    Texure.write(Surface.get_view("1")) # Render surf to texture
    Texure.build_mipmaps() # Generate mipmaps
    return Texure # Return OpenGL texture

InputProcesser = TextInput()
TextProcesser = TextProcessing()

# Initial system messages
TextProcesser.AddConversationText("Welcome to GLaDOS Terminal v2.8.5", False)
TextProcesser.AddConversationText("Use ` or ~ to open the model selector in chat and F5 to toggle TTS.", False)

# ---------------------- Tunable UI/Logic Constants ---------------------- #
BOOT_DURATION = 5.0
FADE_FACTOR = 0.1
MODEL_SELECTOR_FADE_IN_SPEED = 800
MODEL_SELECTOR_FADE_OUT_SPEED = 1200
FONT_COLOR = (230, 125, 15)
MODEL_SELECTOR_BOX_WIDTH = 500


## Main game loop ##################################################################################

# Play background ambience sound and set it to repeat
pygame.mixer.music.load(resource_path("Sounds/ComputerAmbient.mp3"))
pygame.mixer.music.play(-1)
pygame.mixer.music.set_volume(Settings["SoundEffectVolume"])

# Play boot sound
ComputerBootSound.play()

while True:

    # Set fps
    Clock.tick(FPS)

    # Update delta time
    DeltaTime = time.time() - LastTime
    LastTime = time.time()

    Time += DeltaTime
    
    ## Pygame screen rendering #####################################################################

    # Fade out previous text
    Fade = pygame.Surface(Resolution).convert_alpha()
    Fade.fill([max(1, Value * FADE_FACTOR) for Value in Color])
    Display.blit(Fade, (0,0), special_flags=BLEND_RGB_SUB)

    # Draw loading text for first few seconds, then chat text
    Lines = TextProcesser.GetMainText(InputProcesser.GetInputText()) if Time > BOOT_DURATION else TextProcesser.GetLoadingText()
    for Line, Text in enumerate(Lines):
        for Count, Letter in enumerate(Text):
            Display.blit(Font.render(Letter, True, [230, 125, 15]), [Count * FontSize[0], Line * FontSize[1]])
    
    ## Model Selector GUI ##########################################################################
    if show_model_selector:
        # Animate the selector appearance
        model_selector_alpha = min(255, model_selector_alpha + DeltaTime * MODEL_SELECTOR_FADE_IN_SPEED)

        # Create semi-transparent overlay
        overlay = pygame.Surface(Resolution).convert_alpha()
        overlay.fill((0, 0, 0, int(model_selector_alpha * 0.7)))
        Display.blit(overlay, (0, 0))

        # Calculate selector box dimensions
        box_width = MODEL_SELECTOR_BOX_WIDTH
        box_height = 50 + len(AVAILABLE_MODELS) * 30 + 50
        box_x = (Resolution[0] - box_width) // 2
        box_y = (Resolution[1] - box_height) // 2

        # Draw selector box background
        selector_bg = pygame.Surface((box_width, box_height)).convert_alpha()
        selector_bg.fill((20, 40, 20, int(model_selector_alpha * 0.9)))
        pygame.draw.rect(selector_bg, (100, 200, 100, int(model_selector_alpha)), (0, 0, box_width, box_height), 2)
        Display.blit(selector_bg, (box_x, box_y))

        # Draw title
        title_text = Font.render("MODEL SELECTOR", True, (150, 255, 150))
        title_x = box_x + (box_width - title_text.get_width()) // 2
        Display.blit(title_text, (title_x, box_y + 10))

        # Draw instructions
        instruction_str = "Use UP/DOWN and ENTER to select, ESC to cancel"
        instruction_text = Font.render(instruction_str, True, (100, 180, 100))
        instr_x = box_x + (box_width - instruction_text.get_width()) // 2
        Display.blit(instruction_text, (instr_x, box_y + 30))

        # Draw model list
        for i, model in enumerate(AVAILABLE_MODELS):
            y_pos = box_y + 60 + i * 30

            # Highlight current model
            highlight_index = selected_model_index if show_model_selector else current_model_index
            if i == highlight_index:
                highlight = pygame.Surface((box_width - 20, 25)).convert_alpha()
                highlight.fill((50, 100, 50, int(model_selector_alpha * 0.5)))
                Display.blit(highlight, (box_x + 10, y_pos - 2))

            # Model number and name
            model_text = f"{i+1}. {model['name']}"
            size_text = f"({FormatModelSize(model['size'])})"

            # Draw model name
            name_surface = Font.render(model_text, True, (200, 255, 200) if i == highlight_index else (150, 200, 150))
            Display.blit(name_surface, (box_x + 20, y_pos))

            # Draw size info
            size_surface = Font.render(size_text, True, (120, 180, 120))
            size_x = box_x + box_width - size_surface.get_width() - 20
            Display.blit(size_surface, (size_x, y_pos))
    else:
        # Fade out the selector when closed
        model_selector_alpha = max(0, model_selector_alpha - DeltaTime * MODEL_SELECTOR_FADE_OUT_SPEED)
            
    ## OpenGL section ##############################################################################

    # Pass in pygame display texture
    DisplayTexure = SurfaceToTexture(pygame.transform.flip(Display, False, True))
    DisplayTexure.use(0)
    Program["PygameTexture"] = 0
    
    Program["Time"] = Time

    RenderObject.render(mode=mgl.TRIANGLE_STRIP) # Call render function

    # Update pygame window
    pygame.display.flip()

    # Release textures to avoid memory leaks
    DisplayTexure.release()

    ## General inputs handling #####################################################################

    # Check for completed inference (guard when no model yet)
    Processed, Response = (GeneratorLLM.CheckResponse() if GeneratorLLM is not None else (False, None))
    
    if Processed:
        # Add AI response to conversation visuals
        tts_status = " (TTS)" if tts_enabled else " (TTS off)"
        TextProcesser.AddConversationText(f"GLaDOS > {Response}{tts_status}", True)

        # Speak response only if TTS is enabled
        if tts_enabled:
            GeneratorTTS.StartInference(Response)
        else:
            print(f"GLaDOS says: {Response}")  # Print to console when TTS is off

    for Event in pygame.event.get():

        # 1) Window close
        if Event.type == QUIT:
            pygame.quit()
            sys.exit()

        # 2) Text input & submit handling (runs on all events) - after boot screen
        if Time > BOOT_DURATION:
            llm_busy = (GeneratorLLM is not None and GeneratorLLM.IsProcessing)
            tts_busy = (tts_enabled and GeneratorTTS.IsProcessing)
            system_busy = llm_busy or tts_busy
            allow_submit = (not system_busy) and (not show_model_selector) and (GeneratorLLM is not None)

            # Decide whether to forward to text input (block when selector is open or key is `/~)
            forward_to_input = not show_model_selector
            if forward_to_input and Event.type == pygame.TEXTINPUT:
                txt = getattr(Event, "text", "")
                if txt in ("`", "~"):
                    forward_to_input = False

            # Feed every event to the input processor so typing/backspace works
            # Prevent Enter from submitting while selector is open
            if show_model_selector and Event.type == pygame.KEYDOWN and Event.key == pygame.K_RETURN:
                pass
            elif forward_to_input and InputProcesser.Event(Event, allow_submit):
                # Only start inference if a model is selected
                if GeneratorLLM is not None:
                    GeneratorLLM.StartInference(InputProcesser.Text)
                    TextProcesser.AddConversationText(f"User > {InputProcesser.Text}", True)
                    InputProcesser.Text = ""
                else:
                    TextProcesser.AddConversationText("System > Select a model first (press ` or ~)", True)

        # 3) Keydown-only shortcuts and UI
        if Event.type == pygame.KEYDOWN:
            # Debounce key repeats
            first_press = Event.key not in HeldKeys
            if first_press:
                KeyboardPressedSound.play()
                HeldKeys[Event.key] = True

            # Model selector toggle (` or ~) only after boot screen
            if Time > BOOT_DURATION and first_press and (
                Event.key == K_BACKQUOTE or getattr(Event, "unicode", "") == "~"
            ):
                show_model_selector = not show_model_selector
                selected_model_index = current_model_index

            # Model selector navigation (UP/DOWN/ENTER/ESC)
            if show_model_selector and first_press:
                if Event.key == K_UP:
                    selected_model_index = (selected_model_index - 1) % len(MODEL_NAMES)
                elif Event.key == K_DOWN:
                    selected_model_index = (selected_model_index + 1) % len(MODEL_NAMES)
                elif Event.key == K_RETURN:
                    current_model_index = selected_model_index
                    new_model = MODEL_NAMES[current_model_index]
                    print(f"Switching to model: {new_model}")
                    GeneratorLLM = LargeLanguageModel(new_model, Settings["SystemPrompt"])
                    TextProcesser.AddConversationText(f"System > Now using {new_model}", True)
                    show_model_selector = False
                elif Event.key == K_ESCAPE:
                    # Close selector
                    show_model_selector = False

            # The rest (scrolling, legacy hotkeys) only after boot screen
            if Time > BOOT_DURATION:
                # Scroll conversation when selector is closed
                if Event.key == K_UP and not show_model_selector:
                    TextProcesser.Scroll(-1)
                elif Event.key == K_DOWN and not show_model_selector:
                    TextProcesser.Scroll(1)

                # Legacy hotkeys (when selector is closed)
                if not show_model_selector and first_press:
                    # Cycle with TAB
                    if Event.key == K_TAB and len(MODEL_NAMES) > 0:
                        current_model_index = (current_model_index + 1) % len(MODEL_NAMES)
                        new_model = MODEL_NAMES[current_model_index]
                        print(f"Cycling to model: {new_model}")
                        GeneratorLLM = LargeLanguageModel(new_model, Settings["SystemPrompt"])
                        TextProcesser.AddConversationText(f"System > Now using {new_model}", True)
                    # F1-F4 direct selection
                    elif Event.key == K_F1 and len(MODEL_NAMES) > 0:
                        current_model_index = 0
                        new_model = MODEL_NAMES[current_model_index]
                        print(f"Switching to model: {new_model}")
                        GeneratorLLM = LargeLanguageModel(new_model, Settings["SystemPrompt"])
                        TextProcesser.AddConversationText(f"System > Switched to {new_model}", True)
                    elif Event.key == K_F2 and len(MODEL_NAMES) > 1:
                        current_model_index = 1
                        new_model = MODEL_NAMES[current_model_index]
                        print(f"Switching to model: {new_model}")
                        GeneratorLLM = LargeLanguageModel(new_model, Settings["SystemPrompt"])
                        TextProcesser.AddConversationText(f"System > Switched to {new_model}", True)
                    elif Event.key == K_F3 and len(MODEL_NAMES) > 2:
                        current_model_index = 2
                        new_model = MODEL_NAMES[current_model_index]
                        print(f"Switching to model: {new_model}")
                        GeneratorLLM = LargeLanguageModel(new_model, Settings["SystemPrompt"])
                        TextProcesser.AddConversationText(f"System > Switched to {new_model}", True)
                    elif Event.key == K_F4 and len(MODEL_NAMES) > 3:
                        current_model_index = 3
                        new_model = MODEL_NAMES[current_model_index]
                        print(f"Switching to model: {new_model}")
                        GeneratorLLM = LargeLanguageModel(new_model, Settings["SystemPrompt"])
                        TextProcesser.AddConversationText(f"System > Switched to {new_model}", True)

                # TTS toggle
                if Event.key == K_F5 and first_press:
                    tts_enabled = not tts_enabled
                    status = "enabled" if tts_enabled else "disabled"
                    print(f"TTS {status}")
                    TextProcesser.AddConversationText(f"System > TTS {status}", True)

        elif Event.type == pygame.KEYUP:
            # Remove the key from HeldKeys
            HeldKeys.pop(Event.key, None)
