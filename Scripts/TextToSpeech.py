import os, json, torch, warnings, threading, re, gdown
import numpy as np
import sounddevice as sd

warnings.filterwarnings("ignore")

from .tacotron2.hparams import create_hparams
from .tacotron2.model import Tacotron2
from .tacotron2.layers import TacotronSTFT
from .tacotron2.audio_processing import griffin_lim
from .tacotron2.text.__init__ import text_to_sequence

from .hifigan.env import AttrDict
from .hifigan.meldataset import MAX_WAV_VALUE
from .hifigan.models import Generator

Directory = os.path.dirname(os.path.realpath(__file__))
GoogleDriveDirectory = "https://drive.google.com/uc?export=download&id="

Device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Small runtime perf tweaks
if Device.type == "cpu":
    try:
        torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))
    except Exception:
        pass
else:
    try:
        torch.backends.cudnn.benchmark = True
    except Exception:
        pass

def GetHifigan(ModelName, ModelID):
    
    if not os.path.exists(f"{Directory}/models/{ModelName}"):
        gdown.download(GoogleDriveDirectory + ModelID, f"{Directory}/models/{ModelName}", quiet=False)
                
    with open(Directory + "/hifigan/config.json") as File:
        JsonConfig = json.loads(File.read())
        
    HyperParams = AttrDict(JsonConfig)
    torch.manual_seed(HyperParams.seed)
    Model = Generator(HyperParams).to(Device)
    StateDictGenerator = torch.load(f"{Directory}/models/{ModelName}", weights_only=True, map_location=Device)
    
    Model.load_state_dict(StateDictGenerator["generator"])
    Model.eval()
    Model.remove_weight_norm()
    
    return Model, HyperParams

def GetTactron2(ModelName, ModelID):
    
    if not os.path.exists(f"{Directory}/models/{ModelName}"):
        gdown.download(GoogleDriveDirectory + ModelID, f"{Directory}/models/{ModelName}", quiet=False)
        
    HyperParams = create_hparams()
    HyperParams.sampling_rate = 22050
    HyperParams.max_decoder_steps = 3000
    # Keep default low threshold; we'll override the model decoder threshold after load
    HyperParams.gate_threshold = 0.2
    
    Model = Tacotron2(HyperParams)
    StateDict = torch.load(f"{Directory}/models/{ModelName}", weights_only=True, map_location=Device)["state_dict"]
    Model.load_state_dict(StateDict)
    Model.to(Device).eval()  # Remove .half() to avoid data type issues
    
    return Model, HyperParams

class TextToSpeech:
    def __init__(self, HifiganName, Tacotron2Name, HifiganID, Tacotron2ID, StopThreshold=0.2):
        self.HifiganModel, self.HifiganHyperParams = GetHifigan(HifiganName, HifiganID)
        self.Tacotron2Model, self.Tacotron2HyperParams = GetTactron2(Tacotron2Name, Tacotron2ID)

        # Faster inference settings
        # Keep a reasonable cap; too small can truncate longer sentences
        self.Tacotron2Model.decoder.max_decoder_steps = 1000
        self.Tacotron2Model.decoder.gate_threshold = StopThreshold
        
        # Keep models in full precision for compatibility
        # Note: Half precision can cause data type mismatches on CPU
        
        self.InferenceThread = None
        self.IsProcessing = False

    @staticmethod
    def _split_text_keep_punct(text: str):
        # Split into clauses, keeping ending punctuation as prosody cues
        # e.g., "Hello, world! How are you?" -> ["Hello, world!", "How are you?"]
        pattern = r"[^.!?;]+[.!?;]?"
        return [m.group(0).strip() for m in re.finditer(pattern, text) if m.group(0).strip()]

    @staticmethod
    def _trim_trailing_silence(audio: np.ndarray, threshold: int = 400, pad_samples: int = 400):
        # audio: int16 mono; remove trailing near-silence to reduce gaps
        if audio.size == 0:
            return audio
        abs_a = np.abs(audio.astype(np.int32))
        idx = np.where(abs_a > threshold)[0]
        if idx.size == 0:
            return audio
        end = min(audio.size, idx[-1] + pad_samples)
        return audio[:end]

    def StartInference(self, Text):
        if not self.IsProcessing:
            self.IsProcessing = True
            self.InferenceThread = threading.Thread(target=self.InferenceTask, args=(Text,))
            self.InferenceThread.daemon = True
            self.InferenceThread.start()

    def InferenceTask(self, Text):
        try:
            # Split into shorter chunks but keep punctuation for natural prosody
            sentences = self._split_text_keep_punct(Text)

            audio_segments = []
            sr = self.Tacotron2HyperParams.sampling_rate

            with torch.inference_mode():
                for Sentence in sentences:
                    sent = Sentence.strip()
                    if len(sent) < 3:
                        continue

                    try:
                        # Convert to phoneme/id sequence using default english cleaners
                        TextSequence = np.array(text_to_sequence(sent, ["english_cleaners"]))[None, :]
                        TextSequence = torch.from_numpy(TextSequence).to(Device).long()

                        # Generate mel and waveform
                        MelSpectrogram, MelSpectrogramPostnet, GateOutputs, AttentionAlignments = self.Tacotron2Model.inference(TextSequence)
                        MelSpectrogramPostnet = MelSpectrogramPostnet.float()

                        # Use autocast on GPU for speed
                        if Device.type == "cuda":
                            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=True):
                                GeneratedAudio = self.HifiganModel(MelSpectrogramPostnet)
                        else:
                            GeneratedAudio = self.HifiganModel(MelSpectrogramPostnet)

                        FinalAudio = GeneratedAudio.squeeze() * MAX_WAV_VALUE
                        audio_data = FinalAudio.cpu().numpy().astype("int16")

                        # Trim trailing silence to avoid long pauses between chunks
                        audio_data = self._trim_trailing_silence(audio_data)
                        if audio_data.size > 0:
                            audio_segments.append(audio_data)

                    except Exception as tts_error:
                        print(f"TTS generation failed for sentence '{sent}': {tts_error}")
                        continue

            # Concatenate and play once to avoid inter-chunk gaps
            if audio_segments:
                full_audio = np.concatenate(audio_segments)
                sd.play(full_audio, samplerate=sr, blocking=False)

        except Exception as e:
            print(f"TTS processing failed: {e}")
        finally:
            self.IsProcessing = False
