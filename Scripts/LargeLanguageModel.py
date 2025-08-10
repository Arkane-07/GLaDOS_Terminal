import re, ollama, os, threading, queue, time

def GetAvailableModels():
    """Fetch available models from Ollama with their details"""
    try:
        models = ollama.list()
        model_list = []
        for model in models.get('models', []):
            model_info = {
                'name': model['name'],
                'size': model.get('size', 0),
                'modified': model.get('modified_at', ''),
                'id': model.get('digest', '')[:12] if model.get('digest') else ''
            }
            model_list.append(model_info)
        return model_list
    except Exception as e:
        print(f"Error fetching models: {e}")
        # Fallback to known models if Ollama is not available
        return [
            {'name': 'llama3.2:3b', 'size': 0, 'modified': '', 'id': ''},
            {'name': 'mapler/gpt2:latest', 'size': 0, 'modified': '', 'id': ''},
            {'name': 'qwen3:0.6b', 'size': 0, 'modified': '', 'id': ''},
            {'name': 'deepseek-r1:1.5b', 'size': 0, 'modified': '', 'id': ''}
        ]

def FormatModelSize(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

class LargeLanguageModel:
    def __init__(self, ModelName, SystemPrompt):
        self.Model = ModelName
        self.History = [{"role":"system", "content":SystemPrompt}]

        self.ResponseQueue = queue.Queue()
        self.InferenceThread = None
        self.IsProcessing = False
        
        # Warm start the model with retry logic
        max_retries = 5
        for attempt in range(max_retries):
            try:
                print(f"Attempting to connect to Ollama... (attempt {attempt + 1}/{max_retries})")
                ollama.chat(model=self.Model, messages=[{"role":"user", "content":"Hi"}])
                print("Successfully connected to Ollama!")
                break
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    print("Failed to connect to Ollama. Please ensure the service is running.")
                    raise

    def ClearHistory(self, SystemPrompt):
        self.History = [{"role":"system", "content":SystemPrompt}]

    def StartInference(self, Text):
        if not self.IsProcessing:
            self.IsProcessing = True
            self.InferenceThread = threading.Thread(target=self.InferenceTask, args=(Text,))
            self.InferenceThread.daemon = True
            self.InferenceThread.start()

    def InferenceTask(self, Text):
        try:
            # Get response and append all to history
            self.History.append({"role":"user", "content":Text})
            
            # Retry logic for inference
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    Response = ollama.chat(model=self.Model, messages=self.History)
                    break
                except Exception as e:
                    print(f"Inference attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    else:
                        # Fallback response if all attempts fail
                        Response = {"message": {"content": "I'm experiencing technical difficulties. Please try again."}}
                        
            self.History.append(Response["message"])

            # Remove new lines
            CleanedText = Response["message"]["content"].replace("\n", " ")
            # Remove excessive white space
            CleanedSentence = re.sub(r'\s+', ' ', CleanedText)
            # Remove white space from start and end of it plus lower case
            CleanedSentence = CleanedText.lower().strip()
            # Add a full stop
            if CleanedText[-1] != ".": CleanedText += "."

            self.ResponseQueue.put(CleanedText)

        finally:
            self.IsProcessing = False

    def CheckResponse(self):
        try:
            Response = self.ResponseQueue.get_nowait()
            return True, Response
        except queue.Empty:
            return False, None
